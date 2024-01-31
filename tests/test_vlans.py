import pytest

from src.vlans import match_lease_time, parse_dhcp_options

from src.mytools.fileops import validate_domain


# ------------------------TEST match_lease_time-------------------------
"""
dhcpLeaseTime:string

The term of DHCP leases if the appliance is running a DHCP server on this 
VLAN. One of: '30 minutes', '1 hour', '4 hours', '12 hours', '1 day' or '1 week'

https://developer.cisco.com/meraki/api-v1/get-network-appliance-vlans/
"""


def test_match_lease_time_30_min():
    """
    Test that given a lease time of 30 minutes, 1800 seconds is returned
    """
    assert match_lease_time("30 minutes") == "1800"


def test_match_lease_time_1_week():
    """
    Test that given a lease time of 1 week, 604800 seconds is returned
    """
    assert match_lease_time("1 week") == "604800"


def test_match_lease_time_invalid_lease():
    """
    Test that given a lease time not yet defined, we raise a ValueError
    """
    with pytest.raises(ValueError) as excinfo:
        match_lease_time("2 hours")
    assert str(excinfo.value) == "The specified lease time has not been defined"


# ------------------------TEST validate_domain--------------------------
"""
Each element of a domain name separated by [.] is called a “label.”
The maximum length of each label is 63 characters, and a full domain
name can have a maximum of 253 characters. Alphanumeric characters
and hyphens can be used in labels, but a domain name must not
commence or end with a hyphen.

"""


def test_validate_domain_name_has_space():
    """
    Test that a ValueError is raised when the domain name has a space
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain("my example.org")
    assert str(excinfo.value) == "Invalid domain name provided"


def test_validate_domain_name_has_special_char():
    """
    Test that a ValueError is raised when the domain name has a special char
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain("my^example.org")
    assert str(excinfo.value) == "Invalid domain name provided"


def test_validate_domain_name_begins_with_dash():
    """
    Test that a ValueError is raised when the domain name begins with -
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain("-example.org")
    assert str(excinfo.value) == "Invalid domain name provided"


def test_domain_name_end_with_dash():
    """
    Test that a ValueError is raised when the domain name ends with -
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain("example.org-")
    assert str(excinfo.value) == "Invalid domain name provided"


def test_domain_name_exceeds_max_length():
    """
    Test that a ValueError is raised when a label name is greater than 63 chars
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain(
            "ThisDomainExceedsThe63MaximumLengthCharactersAllowedAndShouldFail.example.org"
        )
    assert str(excinfo.value) == "Invalid domain name provided"


def test_domain_name_has_two_consecutive_dots():
    """
    Test that a ValueError is raised when the domain name has two or more consecutive dots
    """
    with pytest.raises(ValueError) as excinfo:
        validate_domain("my..example.org")
    assert str(excinfo.value) == "Invalid domain name provided"


def test_domain_name_is_returned():
    """
    Test that a valid domain name is returned
    """
    assert validate_domain("my.example.org") == True


def test_domain_name_with_num_no_exception_raised():
    """
    Test that given a number in a label, a valid domain name is returned
    """
    try:
        validate_domain("my.example1.org")
    except Exception as excinfo:
        pytest.fail(f"Unexpected exception raised: {excinfo}")


def test_domain_name_with_hyphen_no_exception_raised():
    """
    Test that given a hyphen in a label, a valid domain name is returned
    """
    try:
        validate_domain("my-example.org")
    except Exception as excinfo:
        pytest.fail(f"Unexpected exception raised: {excinfo}")


# ---------------------TEST parse_dhcp_options--------------------------
"""
dhcpOptions*:array[]

The list of DHCP options that will be included in DHCP responses. 
Each object in the list should have "code", "type", and "value" properties.

    code*:string
    The code for the DHCP option. This should be an integer between 2 and 254.

    type*:string
    The type for the DHCP option. One of: 'text', 'ip', 'hex' or 'integer'

    value*:string
    The value for the DHCP option
"""

# Arrange
code_15 = [{"code": "15", "type": "text", "value": "example.org"}]
code_150 = [{"code": "150", "type": "ip", "value": "1.1.1.1"}]
code_150_dual_ips = [{"code": "150", "type": "ip", "value": "1.1.1.1, 2.2.2.2"}]
dual_options = [
    {"type": "text", "code": "15", "value": "my.example.org"},
    {"type": "ip", "code": "150", "value": "1.1.1.1, 2.2.2.2"},
]
code_unknown = [{"code": "2", "type": "text", "value": "unknown"}]
type_unknown = [{"code": "15", "type": "float", "value": "unknown"}]


def test_parse_dhcp_options_code_15():
    """
    Test that given code 15 and type is text, a valid domain is returned
    """
    assert parse_dhcp_options(code_15) == {"dn": "example.org", "ip_list": []}


def test_parse_dhcp_options_code_150():
    """
    Test that give code 150 and type ip, a valid IP is returned
    """
    assert parse_dhcp_options(code_150) == {"dn": "", "ip_list": ["1.1.1.1"]}


def test_parse_dhcp_options_code_150_dual_ips():
    """
    Test that give code 150 and type ip where there are two IPs, two are returned
    """
    assert parse_dhcp_options(code_150_dual_ips) == {
        "dn": "",
        "ip_list": ["1.1.1.1", "2.2.2.2"],
    }


def test_parse_dhcp_options_dual_options():
    """
    Test that when given multiple options, those options are all returned
    """
    assert parse_dhcp_options(dual_options) == {
        "dn": "my.example.org",
        "ip_list": ["1.1.1.1", "2.2.2.2"],
    }


def test_parse_dhcp_options_code_unknown():
    """
    Test that when given an undefined code, a TypeError is raised
    """
    with pytest.raises(TypeError) as excinfo:
        parse_dhcp_options(code_unknown)
    assert str(excinfo.value) == "Unknown code provided"


def test_parse_dhcp_options_type_unknown():
    """
    Test that when given an undefined code, a TypeError is raised
    """
    with pytest.raises(TypeError) as excinfo:
        parse_dhcp_options(type_unknown)
    assert str(excinfo.value) == "Unknown code provided"