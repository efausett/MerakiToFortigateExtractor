"""Pull settings from Meraki dashboard and use them to build fortigate config"""

import ipaddress
import logging

import jinja2

from meraki_converter.common import fileops, merakiops

log = logging.getLogger(__name__)
fileops.setup_logging("main")


def setup_fixed_address_clients(clients):
    """Create and return a list of all client attributes"""
    client_list = []
    for count, client in enumerate(clients, start=1):
        client_data = {
            "count": count,
            "ip": clients[client]["ip"],
            "mac": client,
            "description": clients[client].get("name", "")
        }
        client_list.append(client_data)
    return client_list


def parse_dhcp_options(options):
    """For each Meraki DHCP option, format to Fortigate options"""
    all_options = {
        "code_15_text": "",
        "code_43_hex": "",
        "code_78_ip": "",
        "code_79_text": "",
        "code_85_ip": "",
        "code_150_ip": ""}
    for option in options:
        if option["code"] == "15" and option["type"] == "text":
            try:
                fileops.validate_domain(option["value"])
            except ValueError:
                all_options["code_15_text"] = "Error"
            else:
                all_options["code_15_text"] = option["value"]
        elif option["code"] == "43" and option["type"] == "hex":
            new_format = []
            hex_string = option["value"].split(":")
            new_format.append(hex_string[0] + hex_string[1])
            new_format.append(hex_string[2] + hex_string[3])
            new_format.append(hex_string[4] + hex_string[5])
            all_options["code_43_hex"] = ":".join(new_format) 
        elif option["code"] == "78" and option["type"] == "ip":
            code_78_ips = option["value"].split(",")
            code_78_mystr = ""
            for code_78_ip in code_78_ips:
                code_78_mystr += code_78_ip.strip()
                code_78_mystr += " "
            all_options["code_78_ip"] = code_78_mystr.rstrip()
        elif option["code"] == "79" and option["type"] == "text":
            all_options["code_79_text"] = option["value"]
        elif option["code"] == "85" and option["type"] == "ip":
            code_85_ips = option["value"].split(",")
            code_85_mystr = ""
            for code_85_ip in code_85_ips:
                code_85_mystr += code_85_ip.strip()
                code_85_mystr += " "
            all_options["code_85_ip"] = code_85_mystr.rstrip()
        elif option["code"] == "150" and option["type"] == "ip":
            ips = option["value"].split(",")
            mystr = ""
            for ip in ips:
                mystr += ip.strip()
                mystr += " "
            all_options["code_150_ip"] = mystr.rstrip()
        elif option["code"] == "115":
            next
        else:
            raise TypeError("Undefined DHCP option code provided")
    return all_options


def convert_lease_time_to_seconds(lease):
    match lease:
        case "30 minutes":
            return "1800"
        case "1 hour":
            return "3600"
        case "4 hours":
            return "14400"
        case "12 hours":
            return "43200"
        case "1 day":
            return "86400"
        case "1 week":
            return "604800"
        case _:
            # Default case to catch an undefined input
            raise ValueError("The specified lease time has not been defined")


def process_settings(org_name):
    """Get the settings from org_name and return a dict object with them"""
    req_keys = [
        "global",
        "interface",
        "system_dns",
        "fortimanager",
        "fortianalyzer",
        "ipsec",
        "bgp",
        "user",
        "tacacs",
        "netflow",
        "banner",
    ]
    settings = fileops.load_settings(f"input/{org_name}.toml", req_keys)
    config = {
        # global
        "model": settings["global"]["model"],
        "hostname": settings["global"]["hostname"],
        "gui_theme": settings["global"]["gui_theme"],
        # interface
        "loopback_name": settings["interface"]["loopback_name"],
        "loopback_description": settings["interface"]["loopback_description"],
        "loopback_ip": settings["interface"]["loopback_ip"],
        "wan_name": settings["interface"]["wan_name"],
        "wan_description": settings["interface"]["wan_description"],
        "wan_ip": settings["interface"]["wan_ip"],
        "wan_mask": settings["interface"]["wan_mask"],
        "wan_gw": settings["interface"]["wan_gw"],
        "lan_interface": settings["interface"]["lan_interface"],
        # dns
        "system_dns_primary": settings["system_dns"]["system_dns_primary"],
        "system_dns_secondary": settings["system_dns"]["system_dns_secondary"],
        "system_domain": settings["system_dns"]["system_domain"],
        # fortimanager
        "fortimanager_server": settings["fortimanager"]["fortimanager_server"],
        # fortianalyzer
        "fortianalyzer_server": settings["fortianalyzer"]["fortianalyzer_server"],
        "fortianalyzer_serial": settings["fortianalyzer"]["fortianalyzer_serial"],
        # ipsec
        "ipsec_remote_gw": settings["ipsec"]["ipsec_remote_gw"],
        "ipsec_vpn_secret": settings["ipsec"]["ipsec_vpn_secret"],
        # bgp
        "local_asn": settings["bgp"]["local_asn"],
        "remote_asn": settings["bgp"]["remote_asn"],
        "neighbor_ip": settings["bgp"]["neighbor_ip"],
        # user
        "user1": settings["user"]["user1"],
        "user1_password": settings["user"]["user1_password"],
        "user1_profile": settings["user"]["user1_profile"],
        "user2": settings["user"]["user2"],
        "user2_password": settings["user"]["user2_password"],
        "user2_profile": settings["user"]["user2_profile"],
        "user3": settings["user"]["user3"],
        "user3_password": settings["user"]["user3_password"],
        "user3_profile": settings["user"]["user3_profile"],
        # tacacs
        "ise_server": settings["tacacs"]["ise_server"],
        "ise_key": settings["tacacs"]["ise_key"],
        # netflow
        "netflow_collector_ip": settings["netflow"]["netflow_collector_ip"],
        # banner
        "banner": settings["banner"]["banner"].strip("\n"),
    }

    return config


def from_meraki_get_vlans(dashboard, netid):
    # Get list of vlans TODO: put in try block incase there are none
    vlans = dashboard.appliance.getNetworkApplianceVlans(netid)

    # Extract vlan info into dict
    all_vlans = []
    for vlan in vlans:
        vlan_info = {
            "vlan_name": vlan["name"],
            "vlan_id": vlan["id"],
            "vlan_ip": vlan["applianceIp"],
            "vlan_subnet": vlan["subnet"],
            "vlan_start": format(ipaddress.IPv4Network(vlan["subnet"])[1]),
            "vlan_end": format(ipaddress.IPv4Network(vlan["subnet"])[-2]),
            "dhcp_handling": vlan["dhcpHandling"],
            "dhcp_fixed": vlan["fixedIpAssignments"],
            "dhcp_reserved": vlan["reservedIpRanges"],
            "dhcp_name_servers": vlan["dnsNameservers"],
        }
        netmask = ipaddress.ip_network(vlan_info["vlan_subnet"]).netmask
        vlan_info["vlan_netmask"] = netmask
        if "dhcpRelayServerIps" in vlan:
            vlan_info["dhcp_relay"] = " ".join(vlan["dhcpRelayServerIps"])
        if "dhcpLeaseTime" in vlan:
            lease = convert_lease_time_to_seconds(vlan["dhcpLeaseTime"])
            vlan_info["dhcp_lease_time"] = lease
        if "dhcpOptions" in vlan:
            vlan_info["dhcp_options"] = parse_dhcp_options(vlan["dhcpOptions"])
        dhcp_servers = []
        if vlan_info["dhcp_name_servers"] not in [
            "upstream_dns",
            "google_dns",
            "opendns",
        ]:
            dns_servers = vlan_info["dhcp_name_servers"].split("\n")
            for count, server in enumerate(dns_servers):
                dhcp_servers.append(f"set dns-server{count+1} {server}")
            vlan_info["dhcp_name_servers"] = dhcp_servers
        if vlan["fixedIpAssignments"]:
            clients = setup_fixed_address_clients(vlan["fixedIpAssignments"])
            vlan_info["clients"] = clients
        all_vlans.append(vlan_info)
        if len(vlan_info["dhcp_reserved"]) > 16:
            print(len(vlan_info["dhcp_reserved"]))
            raise Exception("Exceeds maximum allowed reservations")
    return all_vlans


def main():
    # Get the title and print it out to the screen
    req_keys = ["title", "logging"]
    settings = fileops.load_settings("input/general_settings.toml", req_keys)
    fileops.clear_screen()
    title = settings["title"]
    print(fileops.colorme(title, "red"))

    # Select an organization to work with
    log.info("Creating instance of the Meraki dashboard")
    dashboard = merakiops.get_dashboard()
    org_id, org_name = merakiops.select_organization(dashboard)
    log.info(f"User has selected organization {org_name} with ID {org_id}")

    # Specify which network in that organization to pull data from
    network_id, network_name = merakiops.select_network(dashboard, org_id)
    log.info(f"User has selected network {network_name} with ID {network_id}")

    # Get and format the configuration information
    vlan_info = from_meraki_get_vlans(dashboard, network_id)
    config = process_settings(org_name)

    # Load and render jinja templates
    log.info("Loading jinja templates")
    file_loader = jinja2.FileSystemLoader("templates")
    env = jinja2.Environment(loader=file_loader)
    template = env.get_template("base.conf")
    rendered_vlans = template.render(config=config, vlan_info=vlan_info)

    # Write rendered data to file named after the network name
    filename = "output/configs/" + network_name + ".conf"
    log.info(f"Writing rendered output to file {filename}")
    fileops.writelines_to_file(filename, rendered_vlans)
    log.info("Script completed successfully")
    print(fileops.colorme("Script completed successfully", "green"))
