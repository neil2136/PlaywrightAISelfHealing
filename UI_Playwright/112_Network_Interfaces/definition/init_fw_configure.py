from definition.settings import *


class TestConfigFW(Test):
    uuid = 'NonTC'
    description = 'Initialize Firewall config'
    goto_teardown = True

    def test_01_config_x1(self):
        X1_static = {
            'if': 'X1',
            'zone': 'WAN',
            'mode': 'static',
            'ip': Parameter.X1_IP,
            'netmask': Parameter.MASK,
            'gateway': Parameter.X1_GW,
            'dns1': Parameter.X1_DNS1,
            'dns2': Parameter.X1_DNS2,
            'mgmt_ping': True,
            'mgmt_https': True,
            'mgmt_ssh': True,
        }
        rc = interfacev4api.config_interface(**X1_static)
        Assertion.assert_equal(rc, True, "ERR: Config X1 failed!")

    @repeat_method(10)
    def test_02_register_fw(self):
        time.sleep(30)
        rc = license_cli.register("online")
        Assertion.assert_equal(rc, True, "ERR: register fw failed")

    def test_03_skip_automatic_update_window(self):
        autoupdatedict = {
            "update": True,
            "download": True,
            "install_firmware": True,
            "hide_advice": True,
            "critical_only": False
        }
        res = setting_api.edit_firmware_auto_update(**autoupdatedict)
        Assertion.assert_equal(res, True, "ERR: Skip Automatic Update window failed!!")

    def test_04_config_x1_sub_vlan_if(self):
        logger.info("config x1 interface... ")
        x1_vlan10_static = {
            'if': 'X1',
            'type': 'vlan',
            'vlan_tag': 10,
            'mode': 'static',
            'ip': Parameter.X1_VLAN10_V4_IP,
            'netmask': Parameter.MASK,
            # 'gateway': Parameter.X1_GW,
            # 'dns1': Parameter.DNS1,
            # 'dns2': Parameter.DNS2,
            'mgmt_https': True,
            'mgmt_ssh': True,
            'mgmt_ping': True,
            'user_https': True,
        }
        x1_vlan10_v6_dict = {
            'name': 'X1',
            'vlan': 10,
            'mode': 'static',
            'zone': 'LAN',
            'ip': Parameter.X1_VLAN10_V6_IP,
            'prefix_length': Parameter.PREFIX_LENGTH,
            'mgmt_ping': True,
            'mgmt_https': True
        }
        rc1 = interfacev4api.add_interface(**x1_vlan10_static)
        rc2 = interfacev6api.config_interface_ipv6(**x1_vlan10_v6_dict)
        Assertion.assert_equal(rc1 & rc2, True, "ERR: Config X1 sub vlan interface failed")

    def test_05_config_x2_as_dhcp_mode(self):
        x2_dhcp_dict = {
            'if': 'x2',
            'zone': 'wan',
            'mode': 'dhcp',
            'dhcp_hostname': '',
            'mgmt_https': True,
            'mgmt_ssh': True,
            'mgmt_snmp': True,
            'mgmt_ping': True,
            'user_https': True,
        }
        res = interfacev4api.config_interface(**x2_dhcp_dict)
        res &= interfacev4api.disable_interface(name='X2')
        # res &= interfacev4api.enable_interface(name='X2')
        Assertion.assert_equal(res, True, "ERR: Configure X2 status to DHCP failed")

    def test_06_config_x3(self):
        X1_static = {
            'if': 'X3',
            'zone': 'LAN',
            'mode': 'static',
            'ip': Parameter.X3_IP,
            'netmask': Parameter.MASK,
            'mgmt_ping': True,
            'mgmt_https': True,
            'mgmt_ssh': True,
        }
        rc = interfacev4api.config_interface(**X1_static)
        Assertion.assert_equal(rc, True, "ERR: Config X3 failed!")

    def test_07_config_interface_x4_x5_wiremode(self):
        logger.info('config interface x2 to wiremode bypass...')
        flag = False
        x4_x5_wiremode = {
            'if': 'X4',
            'zone': 'LAN', 
            'mode': 'wire-mode',
            'type': 'bypass', 
            'wire_paired_interface': 'X5',
            'wire_paired_zone': 'LAN',
            'wire_link_propagation': False,        
            'stateful_inspection': False,
            'restrict_analysis': False,
        }
        rc = interfacev4api.config_interface(**x4_x5_wiremode)

    def test_08_add_tunnle_vpn_policy_on_local_dut(self):
        vpn_policy_dict = {
            'type': 'tunnel_interface',
            'name': Parameter.LOCAL_VPN_NAME,
            'enable': True,
            'auth_mode': 'shared_secret',
            'secret': 'password',
            'pri_gate': Parameter.X1_REMOTE_IP,
            'local_ike_type': 'ipv4',
            'peer_ike_type': 'ipv4',
            'ike_exchange': 'ikev2',
            # 'ike_encryption': 'aes-128',
            'ipversion': 'ipv4',
            # 'ike_auth': 'sha-1',
            # 'ike_dh_group': '2',
            'ike_lifetime': '28800',
            'ipsec_lifetime': '28800',
            'ipsec_protocol': 'esp',
            'ipsec_encryption': 'aes_gcm16_256',
            # 'ipsec_pfs': True,
            'keep_alive': True,
        }

        res = vpnbasesettingapi.add_vpn_policy(**vpn_policy_dict)
        logger.info(res)
        vpnentry = vpnbasesettingapi.show_tunnelvpnpolicy()
        logger.info(f'vpnentry is :{vpnentry}')
        Assertion.assert_regular(str(vpnentry), Parameter.LOCAL_VPN_NAME, "ERR: Add local tunnel vpn policy failed.")

