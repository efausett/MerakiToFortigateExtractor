"""Frequently used functions for accessing the Meraki dashboard"""

import os
import sys

import meraki

from meraki_converter.common import fileops


def get_dashboard(key=None, print_console=False, output_log=False):
    """Instantiate the Meraki dashboard

    Args:
        key (str): The API KEY
        print_console (bool): Flag used to determine writing to CLI
        output_log (bool): Flag used to determine writing to logs

    Returns:
        DashboardAPI
    """
    # TODO: look into log_file_prefix=os.path.basename(__file__)
    if key:
        try:
            return meraki.DashboardAPI(
                key,
                output_log=output_log,
                print_console=print_console,
                suppress_logging=True,
            )
        except AttributeError as e:
            sys.exit("Make sure meraki library is installed. Try `pip install meraki`")

    if "MERAKI_DASHBOARD_API_KEY" in os.environ:
        try:
            return meraki.DashboardAPI(
                output_log=False, print_console=False, suppress_logging=True
            )
        except AttributeError as e:
            sys.exit("Make sure meraki library is installed. Try `pip install meraki`")

    sys.exit("MERAKI_DASHBOARD_API_KEY not found.")


def validate_integer_in_range(end_range):
    while True:
        try:
            selected = int(input("\nOption >> "))
            assert selected in range(1, end_range + 1)
        except ValueError:
            print("\tThat is not an integer!\n")
        except AssertionError:
            print(f"\n\tYou must enter a number between 1 and {end_range}")
        else:
            break
    print()
    return selected - 1


def select_organization(dashboard):
    """Lists all the organizations and prompts the user to select one

    Args:
        dashboard (object): An instance of the Meraki dashboard
    Returns:
        A tuple containing organization ID and name
    """
    organizations = dashboard.organizations.getOrganizations()
    organizations.sort(key=lambda x: x["name"])
    print("\nSelect an organization:\n")
    for line_num, organization in enumerate(organizations, start=1):
        row = fileops.colorme((f'  {line_num} - {organization["name"]}'), "green")
        print(row)
    selected = validate_integer_in_range(len(organizations))
    return (
        organizations[int(selected)]["id"],
        organizations[int(selected)]["name"],
    )


def select_network(dashboard, org, lines_to_display=25):
    """Lists the organization networks and prompts user to select one

    Args:
        dashboard (obj): The Meraki dashboard instance
        org (str): The selected organization ID
        lines_to_display (int): The number of lines before pausing

    Returns:
        list: the selected network ID and network name
    """

    network_list = []
    networks = dashboard.organizations.getOrganizationNetworks(org)

    while not network_list:
        search_name = input(
            "Enter a name to search for or leave blank for all networks: "
        )
        if search_name:
            for network in networks:
                if search_name.lower() in network["name"].lower():
                    network_list.append(network)
        else:
            network_list = networks
        if network_list:
            network_list.sort(key=lambda x: x["name"])
            print("\nNetworks:")
            for line_num, net in enumerate(network_list, start=1):
                net_name = net["name"]
                print(f"{line_num} - {net_name}")
                if line_num % lines_to_display == 0:
                    user_response = input(
                        "\nPress Enter to continue, or q + Enter to quit search: "
                    )
                    if "q" in user_response:
                        break
        else:
            print(f"No networks found matching {search_name}")

    selected = validate_integer_in_range(len(network_list))
    return [network_list[int(selected)]["id"], network_list[int(selected)]["name"]]


def get_networks(dashboard, org):
    try:
        networks = dashboard.organizations.getOrganizationNetworks(org)
        return networks
    except meraki.APIError as e:
        print(f"reason = {e.reason}")


def get_mx_serial_number(dashboard, net_id):
    has_spare = False
    primary_mx_sn = None
    spare_mx_sn = None
    try:
        warm_spare = dashboard.appliance.getNetworkApplianceWarmSpare(net_id)
        if warm_spare["enabled"]:
            has_spare = True
            spare_mx_sn = warm_spare["spareSerial"]
        primary_mx_sn = warm_spare["primarySerial"]
        return (has_spare, primary_mx_sn, spare_mx_sn)
    except meraki.APIError as e:
        print(f"reason = {e.reason}")
        print(f"error = {e.message}")
