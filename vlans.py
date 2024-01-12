"""Converts Meraki Vlan and DHCP settings to a FortiGate config"""

import ipaddress
import logging
import sys
from datetime import datetime
from pathlib import Path

from mytools import fileops, merakiops


# Setup logging
logs_path = "output/logs/"
# Check that specified path exists or create
if not Path(logs_path).exists():
    Path(logs_path).mkdir(parents=True, exist_ok=True)
this_file = Path(__file__).stem
time_stamp = datetime.now().strftime("__%Y-%m-%d_%H-%M-%S")
logname = this_file + time_stamp + ".log"
try:
    logging.basicConfig(
        filename=f"output/logs/{logname}",
        encoding="utf-8",
        level=logging.DEBUG,
        format=(
            "%(asctime)2s %(filename)14s:%(lineno)s " "%(levelname)11s > %(message)s"
        ),
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )
except (FileNotFoundError, PermissionError) as e:
    sys.exit(f'Unable to write logs to file due to "{e.args[1]}"')


def cleanse_the_data(exclude_list, fixed_list):
    logging.info("The cleanse_the_data function has been called")
    for fixed_ip in fixed_list.values():
        search_ip = ipaddress.ip_address(fixed_ip["ip"])
        for count, each in enumerate(exclude_list):
            start_ip = ipaddress.ip_address(each["start"])
            end_ip = ipaddress.ip_address(each["end"])
            # Test for fixed ip found in exclude list
            if search_ip >= start_ip and search_ip <= end_ip:
                # Remove from excluded list
                if start_ip == end_ip:
                    exclude_list.pop(count)
                    continue
                if search_ip == start_ip:
                    new_start_ip = start_ip + 1
                    exclude_list[count]["start"] = str(new_start_ip)
                if search_ip == end_ip:
                    new_end_ip = end_ip - 1
                    exclude_list[count]["end"] = str(new_end_ip)
                # Need to make two new ranges that don't include given IP
                new_end_ip = search_ip - 1
                exclude_list[count]["end"] = str(new_end_ip)
                # Now add another item to list for the new start to end
                new_start_ip = search_ip + 1
                exclude_list.insert(
                    count, {"start": new_start_ip, "end": end_ip, "comment": ""}
                )
    return exclude_list


def format_fixed_addresses(vlan_name, fixed_data):
    logging.info("The format_fixed_addresses function has been called")
    fixed = ["        config reserved-address\n"]
    for count, fixed_ip in enumerate(fixed_data, start=1):
        client_name = fixed_data[fixed_ip]["name"]
        client_mac = fixed_ip
        client_ip = fixed_data[fixed_ip]["ip"]
        if not client_name:
            client_name = ""
        fixed.append(f"            edit {count}\n")
        fixed.append(f"                set ip {client_ip}\n")
        fixed.append(f"                set mac {client_mac}\n")
        fixed.append(f'                set description "{client_name}"\n')
        fixed.append(f"            next\n")
    fixed.append("        end\n")
    fixed_file = vlan_name + "_fixed"
    return fixed


def format_reserved_addresses(vlan_name, reserved_data):
    logging.info("The format_reserved_addresses function has been called")
    reserved = ["        config exclude-range\n"]
    for count, each in enumerate(reserved_data, start=1):
        start_ip = each["start"]
        end_ip = each["end"]
        comment = each["comment"]
        reserved.append(f"            edit {count}\n")
        reserved.append(f"                set start-ip {start_ip}\n")
        reserved.append(f"                set end-ip {end_ip}\n")
        reserved.append(f"            next\n")
    reserved.append("        end\n")
    reserved_file = vlan_name + "_reserved"
    return reserved


def extract_domain_name(options):
    logging.info("The extract_domain_name function has been called")
    domain_name = ""
    for option in options:
        if option["code"] == "15":
            domain_name = option["value"]
    return domain_name


def extract_option_150(options):
    logging.info("The extract_option_150 function has been called")
    count = 1
    ips = ["        config options\n"]
    new_value = ""
    for option in options:
        if option["code"] == "150":
            ips.append(f"            edit {count}\n")
            ips.append(f"                set code {option['code']}\n")
            ips.append(f"                set type {option['type']}\n")
            opt = option["value"].split(",")
            for each_ip in opt:
                quoted_ip = f'"{each_ip.strip()}"'
                new_value += quoted_ip + " "
            ips.append(f"                set ip {new_value.rstrip()}\n")
            ips.append("            next\n")
            count += 1
    ips.append("        end\n")
    if count > 1:
        return ips
    else:
        return []


def match_lease_time(lease):
    logging.info("The match_lease_time function has been called")
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


def parse_dhcp_settings(vlan_data):
    logging.info("The parse_dhcp_settings function has been called")
    dhcp_settings = []
    excluded = []
    excluded_list = []
    fixed = []
    options = None
    dns_servers = ""
    opt_150 = []
    new_excluded_list = []
    vlan_name = vlan_data["name"]
    vlan_id = vlan_data["id"]
    vlan_int = "Vlan_" + str(vlan_id)
    mandatory = vlan_data["mandatoryDhcp"]
    lease_time = vlan_data["dhcpLeaseTime"]
    lease_time_int = match_lease_time(lease_time)
    dns_servers = vlan_data["dnsNameservers"]
    boot_options = vlan_data["dhcpBootOptionsEnabled"]
    dhcp_options = vlan_data["dhcpOptions"]
    reserved_ips = vlan_data["reservedIpRanges"]
    fixed_ips = vlan_data["fixedIpAssignments"]
    if reserved_ips and fixed_ips:
        new_excluded_list = cleanse_the_data(reserved_ips, fixed_ips)
    if fixed_ips:
        fixed = format_fixed_addresses(vlan_name, fixed_ips)
    if new_excluded_list:
        excluded = format_reserved_addresses(vlan_name, new_excluded_list)
    else:
        excluded = format_reserved_addresses(vlan_name, reserved_ips)
    if dhcp_options:
        options = extract_domain_name(dhcp_options)
        opt_150 = extract_option_150(dhcp_options)
    domain_name = options or ""
    gateway = vlan_data["applianceIp"]
    subnet = vlan_data["subnet"]
    vlan_subnet = list(ipaddress.ip_network(subnet).hosts())
    netmask = ipaddress.ip_network(subnet).netmask
    if domain_name:
        dhcp_settings.append(f"        set domain {domain_name}\n")
    dhcp_settings.append(f"        set default-gateway {gateway}\n")
    dhcp_settings.append(f"        set netmask {netmask}\n")
    dhcp_settings.append(f'        set interface "{vlan_int}"\n')
    dhcp_settings.append(f"        set lease-time {lease_time_int}\n")
    if dns_servers == "upstream_dns":
        dhcp_settings.append("        set dns-service default\n")
    else:
        dns_servers = dns_servers.split("\n")
        for count, server in enumerate(dns_servers):
            dhcp_settings.append(f"        set dns-server{count+1} {server}\n")
    dhcp_settings.append("        config ip-range\n")
    dhcp_settings.append("            edit 1\n")
    dhcp_settings.append(f"               set start-ip {vlan_subnet[0]}\n")
    dhcp_settings.append(f"               set end-ip {vlan_subnet[-1]}\n")
    dhcp_settings.append("            next\n")
    dhcp_settings.append("        end\n")
    for exclude in excluded:
        dhcp_settings.append(exclude)
    for fix in fixed:
        dhcp_settings.append(fix)
    if opt_150:
        for opt in opt_150:
            dhcp_settings.append(opt)
    return dhcp_settings


def process_vlans(dashboard, network):
    logging.debug("The process_vlans function has been called")
    # Confirm that the specified network has an appliance or exit
    devices = dashboard.networks.getNetworkDevices(network[0])
    mx_found = False
    for device in devices:
        if "MX" in device["model"]:
            logging.info(f"Found a Meraki {device['model']}")
            mx_found = True
    if not mx_found:
        logging.info("No MX appliance was found for specified network")
        sys.exit(f"The selected network {network[1]} does not have an MX appliance")
    # Check if Vlans are enabled and if not exit
    if not dashboard.appliance.getNetworkApplianceVlansSettings(network[0])[
        "vlansEnabled"
    ]:
        logging.info("Vlans are not enabled for the specified network")
        single_network = dashboard.appliance.getNetworkApplianceSingleLan(network[0])
        print(f"Vlans are not enabled for {network[1]}")
        sys.exit(f"The single subnet is {single_network['subnet']}")
    # When Vlans are enabled extract dhcp and interface settings
    filename = "output/configs/" + network[1] + ".cfg"
    dhcp = ["config system dhcp server\n"]
    interface_config = ["config system interface\n"]
    bgp_config = ["config router bgp\n", "    config network\n"]
    route_map = [
        "config router prefix-list\n",
        "    edit LAN1\n",
        "        config rule\n",
    ]
    found_dhcp = False
    # TODO: Pull existing fortigate settings to know where to start
    # Start at 10 to avoid conflicts with existing fortigate settings
    count = 10
    vlans = dashboard.appliance.getNetworkApplianceVlans(network[0])
    for vlan in vlans:
        name = vlan["name"]
        logging.info(f"Processing vlan {name}")
        vlan_id = vlan["id"]
        subnet = vlan["subnet"]
        netmask = ipaddress.ip_network(subnet).netmask
        assigned_ip = vlan["applianceIp"]
        interface_config.append(f"    edit Vlan_{vlan_id}\n")
        interface_config.append("        set vdom root\n")
        interface_config.append(f'        set alias "{name}"\n')
        interface_config.append(f"        set ip {assigned_ip} {netmask}\n")
        interface_config.append("        set allowaccess ping\n")
        interface_config.append("        set role lan\n")
        interface_config.append('        set interface "internal1"\n')
        interface_config.append(f"        set vlanid {vlan_id}\n")
        bgp_config.append(f"        edit {count}\n")
        bgp_config.append(f"            set prefix {subnet}\n")
        bgp_config.append("        next\n")
        route_map.append(f"            edit {count}\n")
        route_map.append(f"                set prefix {subnet}\n")
        route_map.append(f"                unset ge\n")
        route_map.append(f"                unset le\n")
        route_map.append("            next\n")
        dhcp_handling = vlan["dhcpHandling"]
        # Handle case where "Run a DHCP server" is selected
        if "Run" in dhcp_handling:
            found_dhcp = True
            logging.info(f"Vlan {name} has DHCP settings enabled")
            count += 1
            dhcp.append(f"    edit {count}\n")
            dhcp_parsed = parse_dhcp_settings(vlan)
            for item in dhcp_parsed:
                dhcp.append(item)
            dhcp.append("    next\n")
        # Handle case where "Relay DHCP to another server" is selected
        if "Relay" in dhcp_handling:
            logging.info(f"Vlan {name} has a DHCP relay configured")
            relay_servers = vlan["dhcpRelayServerIps"]
            interface_config.append("        set dhcp-relay-service enable\n")
            interface_config.append(
                f"        set dhcp-relay-ip {' '.join(relay_servers)}\n"
            )
        interface_config.append(f"    next\n")
    # Only append DHCP if it was enabled
    if found_dhcp:
        logging.info("Processing dhcp settings")
        dhcp.append("end\n")
        interface_config.append("end\n")
        bgp_config.append("    end\n")
        bgp_config.append("end\n")
        route_map.append("        end\n")
        route_map.append("    next\n")
        route_map.append("end\n")
        interface_config.extend(dhcp)
        interface_config.extend(bgp_config)
        interface_config.extend(route_map)
    else:
        interface_config.append("end\n")
        bgp_config.append("    end\n")
        bgp_config.append("end\n")
        route_map.append("        end\n")
        route_map.append("    next\n")
        route_map.append("end\n")
        interface_config.extend(bgp_config)
        interface_config.extend(route_map)
    fileops.writelines_to_file(filename, interface_config)


def main():
    dashboard = merakiops.get_dashboard()
    org = merakiops.select_organization(dashboard)
    network = merakiops.select_network(dashboard, org[0])
    logging.info(f"Network {network[1]} from organization {org[1] } has been selected")
    process_vlans(dashboard, network)


if __name__ == "__main__":
    main()
