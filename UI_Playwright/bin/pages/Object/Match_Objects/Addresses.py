# pages/Object/Match_Objects/addresses.py, Page Methods for Addresses Page
from pages.base_page import *

logger = get_logger('addresses_page')


class Addresses(BasePage):
    ADD_BUTTON = '.icon-add'
    NAME_INPUT = 'input[name="name"]'
    ZONE_DROPDOWN = 'input[name="zoneAssignment"]'
    TYPE_DROPDOWN = 'input[name="type"]'
    IP_INPUT = 'input[name="ip-address"]'
    SAVE_BUTTON = 'text=Save'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + "/m/mgmt/objects/address-objects"
    
    def navigate_to_address_objects_tab(self):
        # self.navigate_to(self.url + "/address-object")
        self.navigate_to_Top_tab('Object')
        self.navigate_to_left_level_1_tab('Match Objects', 'Addresses')
        self.page.get_by_text('Address Objects').click()

    # def navigate_to_address_groups_tab(self):
    #     self.navigate_to_url(self.url+"/address-group")
    
    def open_add_address_object_window(self, timeout: int = 30000):
        logger.info('Click Add Address Object button')
        self.click(self.ADD_BUTTON, timeout=timeout)
        logger.info('Wait for Add Address Object window')
        self.wait_for_selector(self.NAME_INPUT, timeout=timeout)

    def add_address_object(self, name, zone, ao_type, ip, timeout: int = 30000):
        try:
            logger.info('Fill Name textbox')
            self.fill(self.NAME_INPUT, name)
            self.select_value_in_dropdown_box("Zone Assignment", zone, timeout)
            self.select_value_in_dropdown_box("Type", ao_type, timeout)
            logger.info('Fill IP textbox')
            self.fill(self.IP_INPUT, ip)
            logger.info('Click Save button')
            self.click(self.SAVE_BUTTON, timeout=timeout)
            logger.info('Wait for Address Object to be added')
            self.wait_for_selector(self.STATUS_MESSAGE, timeout=timeout)
        except Exception as e:
            logger.error(f"Add Address Object failed: {e}")

    def is_address_object_exist(self, name: str) -> bool:
        """check if address object exists"""
        try:
            self.get_element_by_text(name).is_visible(timeout=5000)
            return True
        except Exception as e:
            logger.error(f"Address Object '{name}' does not exist: {e}")
            return False