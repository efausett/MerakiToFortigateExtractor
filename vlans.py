"""Convers Meraki DHCP settings to a FortiGate config"""

import ipaddress

from mytools import fileops, merakiops


def cleanse_the_data(exclude_list, fixed_list):
    for fixed_ip in fixed_list.values():
        search_ip = ipaddress.ip_address(fixed_ip["ip"])
        for count, each in enumerate(exclude_list):
            start_ip = ipaddress.ip_address(each['start'])
            end_ip = ipaddress.ip_address(each['end'])
            # Test for fixed ip found in exclude list
            if search_ip >= start_ip and search_ip <= end_ip:
                # Remove from excluded list
                if start_ip == end_ip:
                    exclude_list.pop(count)
                    continue
                if search_ip == start_ip:
                    new_start_ip = start_ip + 1
                    exclude_list[count]['start'] = str(new_start_ip)
                if search_ip == end_ip:
                    new_end_ip = end_ip - 1
                    exclude_list[count]['end'] = str(new_end_ip)
                # Need to make two new ranges that don't include given IP
                new_end_ip = search_ip - 1
                exclude_list[count]['end'] = str(new_end_ip)
                # Now add another item to list for the new start to end
                new_start_ip = search_ip + 1
                exclude_list.insert(count, {'start': new_start_ip, 'end': end_ip, 'comment': ''})
    return exclude_list


def format_fixed_addresses(vlan_name, fixed_data):
    fixed = ["        config reserved-address\n"]
    for count, fixed_ip in enumerate(fixed_data, start=1):
        client_name = fixed_data[fixed_ip]["name"]
        client_mac = fixed_ip
        client_ip = fixed_data[fixed_ip]["ip"]
        if not client_name:
            client_name = ''
        fixed.append(f'            edit {count}\n')
        fixed.append(f'                set ip {client_ip}\n')
        fixed.append(f'                set mac {client_mac}\n')
        fixed.append(f'                set description \"{client_name}\"\n')
        fixed.append(f'            next\n')
    fixed.append("        end\n")
    fixed_file = vlan_name + "_fixed"
    return fixed


def format_reserved_addresses(vlan_name, reserved_data):
    reserved = ["        config exclude-range\n"]
    for count, each in enumerate(reserved_data, start=1):
        start_ip = each["start"]
        end_ip = each["end"]
        comment = each["comment"]
        reserved.append(f'            edit {count}\n')
        reserved.append(f"                set start-ip {start_ip}\n")
        reserved.append(f"                set end-ip {end_ip}\n")
        reserved.append(f'            next\n')
    reserved.append("        end\n")
    reserved_file = vlan_name + "_reserved"
    return reserved


def extract_domain_name(options):
    domain_name = ""
    for option in options:
        if option["code"] == '15':
            domain_name = option["value"]
    return domain_name


def extract_option_150(options):
    count = 1
    ips = ["        config options\n"]
    new_value = ""
    for option in options:
        if option["code"] == '150':
            ips.append(f"            edit {count}\n")
            ips.append(f"                set code {option['code']}\n")
            ips.append(f"                set type {option['type']}\n")
            opt = option['value'].split(",")
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


def parse_dhcp_settings(vlan_data):
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
    dhcp_settings.append(f"        set interface \"{vlan_int}\"\n")
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


def main():
    dashboard = merakiops.get_dashboard()
    org_id, org_name = merakiops.select_organization(dashboard)
    network = merakiops.select_network(dashboard, org_id)
    # Find VLAN settings, handle case where vlans aren't enabled
    filename = network[1] + ".cfg"
    dhcp = []
    interface_config = []
    count = 10
    if dashboard.appliance.getNetworkApplianceVlansSettings(network[0])["vlansEnabled"]:
        vlans = dashboard.appliance.getNetworkApplianceVlans(network[0])
        dhcp.append("config system dhcp server\n")
        interface_config.append("config system interface\n")
        for vlan in vlans:
            name = vlan["name"]
            vlan_id = vlan["id"]
            subnet = vlan["subnet"]
            netmask = ipaddress.ip_network(subnet).netmask
            assigned_ip = vlan["applianceIp"]
            dhcp_handling = vlan["dhcpHandling"]
            interface_config.append(f"    edit Vlan_{vlan_id}\n")
            interface_config.append("        set vdom root\n")
            interface_config.append(f"        set alias {name}\n")
            interface_config.append(f"        set ip {assigned_ip} {netmask}\n")
            interface_config.append("        set allowaccess ping\n")
            interface_config.append("        set role lan\n")
            interface_config.append("        set interface \"internal1\"\n")
            interface_config.append(f"        set vlanid {vlan_id}\n")
            interface_config.append(f"    next\n")
            if "Run" in dhcp_handling:
                count += 1
                dhcp.append(f"    edit {count}\n")
                dhcp_parsed = parse_dhcp_settings(vlan)
                for item in dhcp_parsed:
                    dhcp.append(item)
                dhcp.append("    next\n")
        dhcp.append("end\n")
        #fileops.append_to_file('tax-dhcp.txt', dhcp)
        interface_config.append("end\n")
        interface_config.extend(dhcp)
        fileops.writelines_to_file(filename, interface_config)
    else:
        single_network = dashboard.appliance.getNetworkApplianceSingleLan(network[0])
        print("Vlans are not enabled")
        print(f"The single subnet is {single_network['subnet']}")


if __name__ == '__main__':
    main()
