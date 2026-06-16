import pytest
import inspect
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login

class Test_01_navigate_to_routing_page:
    uuid = 'SOSAIOT-TC-95189'
    def test_01_navigate_to_routing_rule_page(self, fw_page):
        logger.info(f"go to routing page")
        fw_page.navigate_to_url(Settings.BASE_URL + '/m/mgmt/policies/ngpe-route-policy')
        res = fw_page.page.wait_for_selector('.fw-ftr-ngpe-route-policy', timeout=10000)
        logger.info(f"res: {res}")
        flag = True if res else False
        assert flag, "routing page not loaded"

class Test_02_check_interface_page_navigation:
    uuid = 'SOSAIOT-TC-95190'
    def test_01_check_breadcrumb_text(self, fw_page):
        breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
        breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
        logger.info(f"breadcrumb text is: {breadcrumb_text}")
        assert "Policy / Rules and Policies / Routing Rules" in breadcrumb_text, "Breadcrumb text does not contain expected path"


class Test_03_check_routing_toolbar:

    @pytest.mark.parametrize("type, locator, expected_options, uuid", [
        ("Rule Type", ".fw-ftr-ngpe-route-policy__class-select", ["Default & Custom", "Default Rules", "Custom Rules"], "SOSAIOT-TC-95191"),
        ("IPversion", ".fw-ftr-ngpe-route-policy__ipversion-select", ["IPv4 & IPv6", "IPv4 Rules", "IPv6 Rules"], "SOSAIOT-TC-95192"),
        ("Active", ".fw-ftr-ngpe-route-policy__active-select", ["Active & Inactive", "Active Rules", "Inactive Rules"], "SOSAIOT-TC-95194"),
        ("Used", ".fw-ftr-ngpe-route-policy__used-select", ["Used & Unused", "Used Rules", "Unused Rules"], "SOSAIOT-TC-95195"),
        ])
    def test_02_check_dropdown_options_value(self, fw_page, type, locator, expected_options, uuid):
        try:
            flag = False
            fw_page.page.locator(locator).click()
            fw_page.page.wait_for_selector('.sw-dropdown__inner', state='visible', timeout=5000)
            dropdown_inner = fw_page.page.locator('.sw-dropdown__inner')
            options = dropdown_inner.locator('.sw-dropdown-unit')
            item_options = []
            if options.count() != 0:
                for i in range(options.count()):
                    option = options.nth(i)
                    # get the option id and text
                    option_id = option.get_attribute('id')
                    all_text = option.inner_text().strip()
                    item_options.append(all_text)
            logger.info(f'All dropdown options: {item_options}')
            flag = True if item_options == expected_options else False  
        finally:
            logger.info(f'close dropdown')
            fw_page.page.keyboard.press("Escape")
            fw_page.page.wait_for_timeout(500)
        assert flag == True, f"{type} default  dropdown options value is not {expected_options}"

class Test_07_check_routing_table_header:
    uuid = "SOSAIOT-TC-95202"
    def test_01_check_table_header(self, fw_page):
        checkheaderlist = ['GENERAL', 'PRIORITY', 'HITS', 'NAME', 'LOOKUP', 'SOURCE', 'DESTINATION', 'SERVICE', 'APP', 'NEXT HOP', 'INTERFACE', 'GATEWAY', 'METRIC', 'TYPE', 'PATH SELECTION PROFILE', 'PROBE', 'PROBE', 'OPERATION', 'CLASS']
        get_table_header = fw_page.get_table_header("fw-ftr-ngpe-route-policy")
        logger.info(f"Actual table header: {get_table_header}")
        assert checkheaderlist == get_table_header, "table header does not match expected header list"


