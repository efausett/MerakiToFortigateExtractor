"""Get the uplink and vlan settings for a particular network"""

import ipaddress

from mytools import fileops, merakiops


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
        fixed.append(f'                set description {client_name}\n')
        fixed.append(f'            next\n')
    fixed.append("        end\n")
    fixed_file = vlan_name + "_fixed"
    return fixed


def format_reserved_addresses(vlan_name, reserved_data):
    reserved = ["        config exclude-range\n"]
    for count, each in enumerate(reserved_data, start=1):
        start = each["start"]
        end = each["end"]
        comment = each["comment"]
        reserved.append(f'            edit {count}\n')
        reserved.append(f"                set start-ip {start}\n")
        reserved.append(f"                set end-ip {end}\n")
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
    ips = ["config options\n"]
    for option in options:
        if option["code"] == '150':
            ips.append(f"        edit {count}\n")
            ips.append(f"            set code {option['code']}\n")
            ips.append(f"            set type {option['type']}\n")
            ips.append(f"            set value {option['value']}\n")
            ips.append("        next\n")
            count += 1
    ips.append("end\n")
    if count > 1:
        return ips
    else:
        return []


def parse_dhcp_settings(vlan_data):
    dhcp_settings = []
    excluded = []
    fixed = []
    options = None
    dns_servers = ""
    opt_150 = []
    vlan_name = vlan_data["name"]
    vlan_id = vlan_data["id"]
    mandatory = vlan_data["mandatoryDhcp"]
    lease_time = vlan_data["dhcpLeaseTime"]
    dns_servers = vlan_data["dnsNameservers"]
    boot_options = vlan_data["dhcpBootOptionsEnabled"]
    dhcp_options = vlan_data["dhcpOptions"]
    reserved_ips = vlan_data["reservedIpRanges"]
    fixed_ips = vlan_data["fixedIpAssignments"]
    if reserved_ips:
        excluded = format_reserved_addresses(vlan_name, reserved_ips)
    if fixed_ips:
        fixed = format_fixed_addresses(vlan_name, fixed_ips)
    if dhcp_options:
        options = extract_domain_name(dhcp_options)
        opt_150 = extract_option_150(dhcp_options)
    domain_name = options or ""
    gateway = vlan_data["applianceIp"]
    subnet = vlan_data["subnet"]
    vlan_subnet = list(ipaddress.ip_network(subnet).hosts())
    netmask = ipaddress.ip_network(subnet).netmask
    dhcp_settings.append(f"        set domain {domain_name}\n")
    dhcp_settings.append(f"        set default-gateway {gateway}\n")
    dhcp_settings.append(f"        set netmask {netmask}\n")
    dhcp_settings.append(f"        set interface {vlan_name}\n")
    if dns_servers:
        dns_servers = dns_servers.split("\n")
        for count, server in enumerate(dns_servers):
            dhcp_settings.append(f"        set dns-server{count+1} {server}\n")
    else:
        dhcp_settings.append("        set dns-service default\n")
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
    primary_sn = ""
    spare_sn = ""
    mx_sn = ""
    dashboard = merakiops.get_dashboard()
    org_id, org_name = merakiops.select_organization(dashboard)
    network = merakiops.select_network(dashboard, org_id)

    ## Check for warm spare. If found set serial number for both MXs
    #warm_spare = dashboard.appliance.getNetworkApplianceWarmSpare(network[0])
    #if warm_spare["enabled"]:
    #    primary_sn = warm_spare["primarySerial"]
    #    spare_sn = warm_spare["spareSerial"]
    #    if warm_spare["uplinkMode"] == "virtual":
    #        print(f"This site, {network[1]}, has a warm spare")
    #        print(f"  VIP: {warm_spare['wan1']['ip']}")
    #        print(f"  VIP Subnet: {warm_spare['wan1']['subnet']}")
    ## Else warm spare not found, set single MX serial number
    #else:
    #    devices = dashboard.networks.getNetworkDevices(network[0])
    #    # print(devices)
    #    for device in devices:
    #        if "MX" in device["model"]:
    #            mx_sn = device["serial"]

    ## For each MX found, print out WAN uplink settings
    #MXs = [primary_sn, spare_sn, mx_sn]
    #for each_MX in MXs:
    #    if each_MX:
    #        print("\nMX Serial Number: " + each_MX)
    #        wan_info = dashboard.appliance.getDeviceApplianceUplinksSettings(each_MX)
    #        # print(wan_info)
    #        # Find enabled Uplink interfaces and extract config
    #        for each in wan_info["interfaces"]:
    #            if wan_info["interfaces"][each]["enabled"]:
    #                if (
    #                    wan_info["interfaces"][each]["svis"]["ipv4"]["assignmentMode"]
    #                    == "dynamic"
    #                ):
    #                    print(f"  {each} Uplink is set to dynamic")
    #                    break
    #                print(
    #                    f"  {each} {wan_info['interfaces'][each]['svis']['ipv4']['address']}"
    #                )
    #                print(
    #                    f"  {each} {wan_info['interfaces'][each]['svis']['ipv4']['gateway']}"
    #                )
    #                if wan_info["interfaces"][each]["vlanTagging"]["enabled"]:
    #                    print(f"  {each} {wan_info['interfaces'][each]['vlanTagging']}")
    #                    # print(wan_info['interfaces'][each]['vlanTagging']['vlanId'])
    #        print()

    # Find VLAN settings, handle case where vlans aren't enabled
    dhcp_settings = []
    output = []
    vlan_list = []
    dhcp = []
    count = 10
    if dashboard.appliance.getNetworkApplianceVlansSettings(network[0])["vlansEnabled"]:
        vlans = dashboard.appliance.getNetworkApplianceVlans(network[0])
        dhcp.append("config system dhcp server\n")
        
        for vlan in vlans:
            name = vlan["name"]
            vlan_id = vlan["id"]
            subnet = vlan["subnet"]
            assigned_ip = vlan["applianceIp"]
            dhcp_handling = vlan["dhcpHandling"]
            try:
                group_policy = vlan["groupPolicyId"]
            except KeyError:
                group_policy = ''
            values = name + "," + str(vlan_id) + "," + subnet + "," + assigned_ip + "," + dhcp_handling + "," + group_policy + "\n"
            vlan_list.append(values)
            #
            if "Run" in dhcp_handling:
                count += 1
                dhcp.append(f"    edit {count}\n")
                dhcp_parsed = parse_dhcp_settings(vlan)
                for item in dhcp_parsed:
                    dhcp.append(item)
                dhcp.append("    next\n")
        dhcp.append("end\n")
        fileops.append_to_file('dhcp1.txt', dhcp)
    else:
        single_network = dashboard.appliance.getNetworkApplianceSingleLan(network[0])
        print("Vlans are not enabled")
        print(f"The single subnet is {single_network['subnet']}")
    for each in dhcp_settings:
        output.append(each)

    fileops.writelines_to_file('vlans.txt', vlan_list)


if __name__ == '__main__':
    main()
