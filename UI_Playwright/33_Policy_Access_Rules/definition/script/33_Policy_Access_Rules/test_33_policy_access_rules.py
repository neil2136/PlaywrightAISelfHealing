import pytest
from config.settings import Settings
from config.logger import get_logger

logger = get_logger(__name__)
# "UI / Non-UPE / 33_Policy-Access_Rules"
pytestmark = pytest.mark.auto_login


class Test_01_navigate_to_access_rule_page:
    uuid = 'SOSAIOT-TC-95079'
    def test_01_navigate_to_access_rule_page(self, fw_page):
        logger.info(f"go to network url")
        fw_page.navigate_to_url(Settings.BASE_URL + '/m/mgmt/policies/ngpe-access-rules')
        res = fw_page.page.wait_for_selector('.fw-ftr-ngpe-access-rules', timeout=10000)
        logger.info(f"res: {res}")
        flag = True if res else False
        assert flag, "access rule page not loaded"

class Test_02_check_access_page_navigation:
    uuid = 'SOSAIOT-TC-95080'
    def test_01_check_breadcrumb_text(self, fw_page):
        breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
        breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
        logger.info(f"breadcrumb text is: {breadcrumb_text}")
        assert "Policy / Rules and Policies / Access Rules" in breadcrumb_text, "Breadcrumb text does not contain expected path"


class Test_03_check_access_rule_toolbar:
    @pytest.mark.parametrize("type, locator, expected_options, uuid", [
        ("Rule Type", ".fw-ftr-ngpe-access-rules__rule-type-select", ["Default & Custom", "Default Rules", "Custom Rules"], "SOSAIOT-TC-95081"),
        ("IPversion", ".fw-ftr-ngpe-access-rules__ipversion-select", ["IPv4 & IPv6", "IPv4", "IPv6"], "SOSAIOT-TC-95082"),
        ("Active", ".fw-ftr-ngpe-access-rules__active-select", ["Active & Inactive", "Active Rules", "Inactive Rules"], "SOSAIOT-TC-95083"),
        ("Used", ".fw-ftr-ngpe-access-rules__used-select", ["Used & Unused", "Used Rules", "Unused Rules"], "SOSAIOT-TC-95084"),
        ])
    def test_02_check_dropdown_options_value(self, fw_page, type, locator, expected_options, uuid):
        try:
            flag = False
            # fwpage.page.locator("div[class*='sw-select--top-padding'][class*='access-rules__ipversion-select']").click()
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


class Test_04_check_interface_table_header:
    uuid = "SOSAIOT-TC-95092"
    def test_01_check_table_header(self, fw_page):
        checkheaderlist = ['GENERAL', 'PRIORITY', 'HITS', 'NAME', 'ACTION', 'ZONE', 'SOURCE', 'DESTINATION', 'ADDRESS', 'SOURCE', 'DESTINATION', 'SERVICE', 'DESTINATION PORT', 'USER', 'USER INCL.', 'USER EXCL.', 'SCHEDULE', 'SCHEDULE']
        get_table_header = fw_page.get_table_header("fw-ftr-ngpe-access-rules")
        logger.info(f"table header is: {get_table_header}")
        # assert checkheaderlist == get_table_header, "table header does not match expected header list"



# class Test_02_check_access_rule_edit_button:
#     uuid = "11008"
#     def test_01_check_add_button(self, fw_page):
#         flag = False
#         # fwpage.page.locator('.sw-icon-button__label-cont:has-text("add")').click()
#         class_value = fw_page.page.locator('.sw-icon-button:has-text("Edit")').get_attribute('class')
#         # class_value = fw_page.page.locator('.sw-icon-button:has(.sw-icon-button__label-cont:has-text("Edit"))').get_attribute('class')
#         logger.info(f'Add button class value is :{class_value}')
#         assert 'is--disabled' in class_value, "ERR: Edit button is not disabled by default"





