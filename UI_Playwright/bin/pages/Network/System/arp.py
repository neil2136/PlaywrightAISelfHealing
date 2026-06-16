from pages.base_page import *
from tools.self_healing_locator import self_heal

logger = get_logger('arp_page')

class ARP(BasePage):
    CONTAINER_1 = 'network-arp-cache'
    CONTAINER_2 = 'network-static-arp-cache'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '/m/mgmt/network/arp'

    def navigate_to_arp(self):
        self.navigate_to_url(self.url)

    def open_add_static_entry_dialog(self) -> bool:
        '''Open the Add Static Entry dialog from the Static ARP Entries tab.

        Returns True if the dialog title is visible after clicking Add.
        '''
        try:
            logger.info("Opening Add Static Entry dialog")
            self.switch_tab("Static ARP Entries", tab_level="l1")
            self.page.wait_for_timeout(2000)
            self.click_icon_button("Add")
            self.page.wait_for_timeout(2000)
            return self.verify_text_exists("Add Static Entry", timeout=5000)
        except Exception as e:
            logger.error(f"Error opening Add Static Entry dialog: {e}")
            return False

    @self_heal(
        # 'Click the Cancel button on the Add/Edit Static Entry dialog to close it',
        ' ',
        auto_retry=True,
        auto_fix= True,
        ai_backend="glm",     # glm, mcp
        enable_rules=True,
    )
    def close_add_dialog(self) -> bool:
        '''Close the Add/Edit dialog by clicking its Cancel button.

        Uses @self_heal: if SonicWall renames the button class after a firmware
        update, the decorator auto-heals the selector and retries.
        '''
        # -> `.sw-modal:visible button:has-text("Cancel")` (scoped to visible modal to avoid
        # matching hidden Cancel buttons elsewhere on the page)
        # [self-healed 2026-06-16 06:01] `.static-entry-modal__modal-footer-cancel-old` -> `.static-entry-modal__modal-footer-cancel`
        self.page.locator('.static-entry-modal__modal-footer-cancel').click()
        self.page.wait_for_timeout(500)
        return True