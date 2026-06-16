# pages/Network/System/interface.py, Page Methods for Interface Page
from pages.base_page import *

logger = get_logger('interface')

class Interface(BasePage):
    TABLE_CONTAINER_CLASS = 'interface-settings-ipv4'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + "/mgmt/objects/address-objects"

    def get_interface_row_locator(self, interface_name: str) -> Locator:
        """Get row locator for specified interface"""
        try:
            logger.info(f'Getting interface row locator for: {interface_name}')
            row_locator = self.get_table_row_locator(self.TABLE_CONTAINER_CLASS, interface_name)
            if row_locator.count() == 0:
                logger.error(f'Interface {interface_name} not found in table')
                return self.page.locator('')  # Return empty locator if not found
            return row_locator
        except Exception as e:
            logger.error(f'Error getting interface row locator for {interface_name}: {e}')
            return self.page.locator('')  # Return empty locator on error

    def get_interface_status(self, interface_name: str) -> str:
        """Get interface status(enabled/disabled/unknown) from the interface table"""
        status = 'unknown'
        try:
            logger.info(f'container_class: {self.TABLE_CONTAINER_CLASS}, row_name: {interface_name}')
            row_locator = self.get_table_row_locator(self.TABLE_CONTAINER_CLASS, interface_name)
            logger.info(f"row_locator: {row_locator}")
            if interface_name in row_locator.inner_text().strip():
                logger.info(f"found row {interface_name}")
                toggle_div = row_locator.locator(f"xpath=.//input[contains(@name,'enable-button')]")
                logger.info(f"toggle_div: {toggle_div}")
                if toggle_div:
                    toggle_class = toggle_div.get_attribute('value')
                    logger.info(f"toggle_class: {toggle_class}")
                    if toggle_class == '1':
                        status = 'enabled'
                    else:
                        status = 'disabled'
            return status
        except Exception as e:
            logger.error(f"Error getting table count for '{self.TABLE_CONTAINER_CLASS}': {e}")
            return status  

    def enable_interface(self, interface_name: str) -> bool:
        interface_row = self.get_interface_row_locator(interface_name)
        if interface_row.count() == 0:
            logger.error(f'Interface {interface_name} not found in table')
            return False
        return self.set_toggle_by_locator(interface_row, enable=True,handle_confirmation=True)

    def disable_interface(self, interface_name: str) -> bool:
        interface_row = self.get_interface_row_locator(interface_name)
        if interface_row.count() == 0:
            logger.error(f'Interface {interface_name} not found in table')
            return False
        return self.set_toggle_by_locator(interface_row, enable=False,handle_confirmation=True)

    def hover_interface_row(self, interface_name: str, wait_time: int = 300) -> Optional[Locator]:
        row_locator = self.get_interface_row_locator(interface_name)
        if row_locator.count() == 0:
            logger.error(f"Interface row not found: {interface_name}")
            return None
        row_locator.first.hover()
        self.page.wait_for_timeout(wait_time)
        return row_locator

    def open_edit_interface_page(self, interface_name: str) -> bool:
        """Edit interface, open edit interface"""
        row_locator = self.hover_interface_row(interface_name)
        if not row_locator:
            logger.error(f"Failed to hover over interface row: {interface_name}")
            return False
        toolbar = row_locator.locator('span:has(.sw-table-row-float-actions) .sw-table-row-float-actions')
        edit_button = toolbar.locator('.icon-pencil')
        if edit_button.count() == 0:
            logger.error(f"Edit button not found for interface: {interface_name}")
            return False
        edit_button.first.click()
        self.page.wait_for_timeout(2000)
        return True

    


    
