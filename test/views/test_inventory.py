import json

import pytest
from pypuppetdb.types import Fact

from puppetboard import app


@pytest.fixture
def mock_puppetdb_inventory_facts(mocker):
    node_facts = [
        {
            "node": "node-debian.test.domain",
            "environment": "production",
            "facts": {
                "hardwaremodel": "x86_64",
                "kernelrelease": "5.10.0-17-amd64",
                "puppetversion": "6.27.0",
                "trusted": {
                    "domain": "local",
                    "certname": "node-debian.test.domain",
                    "hostname": "node-debian",
                    "extensions": {},
                    "authenticated": "remote",
                },
                "os": {
                    "name": "Debian",
                    "distro": {
                        "id": "Debian",
                        "release": {"full": "11.4", "major": "11", "minor": "4"},
                        "codename": "bullseye",
                        "description": "Debian GNU/Linux 11 (bullseye)",
                    },
                    "family": "Debian",
                    "release": {"full": "11.4", "major": "11", "minor": "4"},
                    "selinux": {"enabled": False},
                    "hardware": "x86_64",
                    "architecture": "amd64",
                },
                "networking": {
                    "interfaces": {
                        "lo": {
                            "ip": "127.0.0.1",
                            "mtu": 65536,
                            "netmask": "255.0.0.0",
                            "network": "127.0.0.0",
                            "bindings": [
                                {
                                    "address": "127.0.0.1",
                                    "netmask": "255.0.0.0",
                                    "network": "127.0.0.0",
                                }
                            ],
                        },
                        "eth0": {
                            "ip": "192.168.0.2",
                            "mac": "",
                            "mtu": 1500,
                            "dhcp": "192.168.0.1",
                            "netmask": "255.255.255.0",
                            "network": "192.168.0.0",
                            "bindings": [
                                {
                                    "address": "192.168.0.2",
                                    "netmask": "255.255.255.0",
                                    "network": "192.168.0.0",
                                }
                            ],
                        },
                    },
                    "ip": "192.168.0.2",
                    "primary": "eth0",
                    "mtu": 1500,
                    "hostname": "node-debian",
                    "dhcp": "192.168.0.1",
                    "fqdn": "node-debian.test.domain",
                    "netmask": "255.255.255.0",
                    "network": "192.168.0.0",
                    "domain": "test.domain",
                    "mac": "",
                },
            },
        },
        {
            "node": "node-windows.test.domain",
            "environment": "production",
            "facts": {
                "hardwaremodel": "x86_64",
                "kernelrelease": "10.0.19041",
                "puppetversion": "6.27.0",
                "trusted": {
                    "domain": "local",
                    "certname": "node-windows.test.domain",
                    "hostname": "node-windows",
                    "extensions": {},
                    "authenticated": "remote",
                },
                "os": {
                    "name": "windows",
                    "family": "windows",
                    "release": {"full": "10", "major": "10"},
                    "windows": {
                        "system32": "C:\\WINDOWS\\system32",
                        "edition_id": "Professional",
                        "release_id": "2009",
                        "product_name": "Windows 10 Pro",
                        "installation_type": "Client",
                    },
                    "hardware": "x86_64",
                    "architecture": "x64",
                },
                "networking": {
                    "interfaces": {
                        "Ethernet 1": {
                            "ip": "192.168.0.3",
                            "mtu": 1500,
                            "bindings": [
                                {
                                    "address": "192.168.0.3",
                                    "netmask": "255.255.255.0",
                                    "network": "192.168.0.0",
                                }
                            ],
                            "netmask": "255.255.255.0",
                            "network": "192.168.0.0",
                            "mac": "",
                        }
                    },
                    "ip": "192.168.0.3",
                    "primary": "Ethernet 1",
                    "mtu": 1500,
                    "hostname": "node-windows",
                    "fqdn": "node-windows.test.domain",
                    "netmask": "255.255.255.0",
                    "network": "192.168.0.0",
                    "domain": "test.domain",
                    "mac": "",
                },
            },
        },
        {
            "node": "node-mac.test.domain",
            "environment": "production",
            "facts": {
                "hardwaremodel": "x86_64",
                "kernelrelease": "21.6.0",
                "puppetversion": "6.27.0",
                "trusted": {
                    "domain": "local",
                    "certname": "node-mac.test.domain",
                    "hostname": "node-mac",
                    "extensions": {},
                    "authenticated": "remote",
                },
                "os": {
                    "name": "Darwin",
                    "family": "Darwin",
                    "macosx": {
                        "build": "21G72",
                        "product": "macOS",
                        "version": {
                            "full": "12.5",
                            "major": "12",
                            "minor": "5",
                            "patch": "0",
                        },
                    },
                    "release": {"full": "21.6.0", "major": "21", "minor": "6"},
                    "hardware": "x86_64",
                    "architecture": "x86_64",
                },
                "networking": {
                    "interfaces": {
                        "lo0": {
                            "ip": "127.0.0.1",
                            "bindings6": [
                                {
                                    "scope6": "host",
                                    "address": "::1",
                                    "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                                    "network": "::1",
                                },
                                {
                                    "scope6": "link",
                                    "address": "fe80::1",
                                    "netmask": "ffff:ffff:ffff:ffff::",
                                    "network": "fe80::",
                                },
                            ],
                            "mtu": 16384,
                            "bindings": [
                                {
                                    "address": "127.0.0.1",
                                    "netmask": "255.0.0.0",
                                    "network": "127.0.0.0",
                                }
                            ],
                            "network6": "::1",
                            "netmask6": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                            "ip6": "::1",
                            "netmask": "255.0.0.0",
                            "network": "127.0.0.0",
                            "scope6": "host",
                        },
                        "en0": {
                            "ip": "192.168.0.4",
                            "mac": "",
                            "mtu": 1500,
                            "dhcp": "192.168.0.1",
                            "netmask": "255.255.255.0",
                            "network": "192.168.0.0",
                            "bindings": [
                                {
                                    "address": "192.168.0.4",
                                    "netmask": "255.255.255.0",
                                    "network": "192.168.0.0",
                                }
                            ],
                        },
                    },
                    "ip": "192.168.0.4",
                    "primary": "en0",
                    "mtu": 1500,
                    "hostname": "node-mac",
                    "dhcp": "192.168.0.1",
                    "fqdn": "node-mac.test.domain",
                    "netmask": "255.255.255.0",
                    "network": "192.168.0.0",
                    "domain": "test.domain",
                    "mac": "",
                },
            },
        },
    ]

    facts_list = [
        Fact(
            node=node['node'],
            environment=node['environment'],
            name=fact_name,
            value=fact_value,
        )
        for node in node_facts
        for fact_name, fact_value in node['facts'].items()
    ]
    return mocker.patch.object(app.puppetdb, "facts", return_value=iter(facts_list))


def test_inventory_json(
    client,
    mocker,
    mock_puppetdb_environments,
    mock_puppetdb_inventory_facts,
):

    rv = client.get("/inventory/json")
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode("utf-8"))
    assert len(result_json["data"]) == 3
