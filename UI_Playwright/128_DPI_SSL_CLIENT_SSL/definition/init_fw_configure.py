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
        rc = interface_api.config_interface(**X1_static)
        Assertion.assert_equal(rc, True, "ERR: Config X1 failed!")

    @repeat_method(10)
    def test_02_register_fw(self):
        time.sleep(30)
        rc = license_cli.register("online")
        Assertion.assert_equal(rc, True, "ERR: register fw failed")

    def test_03_admin_logout_timeout(self):
        admin = {
            "multiple_admin": True,
            "idle_logout_time": 5000
        }
        rc = admin_api.conf_admin(**admin)
        Assertion.assert_equal(rc, True, "ERR: config admin logout timeout failed")

    def test_04_users_configure(self):
        user = {
            "web_login_session_limit": 3000,
            "inactivity_time_in_minutes": 5000
        }
        rc = user_api.user_session(**user)
        Assertion.assert_equal(rc, True, "ERR: config User session failed")

    def test_05_skip_automatic_update_window(self):
        autoupdatedict = {
            "update": True,
            "download": True,
            "install_firmware": True,
            "hide_advice": True,
            "critical_only": False
        }
        res = setting_api.edit_firmware_auto_update(**autoupdatedict)
        Assertion.assert_equal(res, True, "ERR: Skip Automatic Update window failed!!")