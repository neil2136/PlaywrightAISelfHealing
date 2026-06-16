# pages/Network/System/web_proxy.py, Page Methods for Web Proxy Page
from pages.base_page import *

logger = get_logger('web_proxy_page')


class WebProxy(BasePage):
    """Page Object for Network > System > Web Proxy page.

    This page has two L1 tabs:
    - Proxy Forwarding: Settings form with proxy web server/port inputs and toggles
    - User Proxy Servers: Table of user proxy servers with Add/Delete/Refresh toolbar
    """

    # Table container CSS class — identifies the User Proxy Servers table wrapper
    USER_PROXY_SERVERS_TABLE = 'sw-table'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '/m/mgmt/network/web-proxy'

    def navigate_to_web_proxy(self):
        """Navigate to the Web Proxy page."""
        self.navigate_to_url(self.url)

    # ---------- User Proxy Servers tab ----------

    def open_add_proxy_server_dialog(self) -> bool:
        """Open the Add Proxy Server dialog from the User Proxy Servers tab.

        Returns True if the dialog title is visible after clicking Add.
        """
        try:
            logger.info("Opening Add Proxy Server dialog")
            self.switch_tab("User Proxy Servers", tab_level="l1")
            self.page.wait_for_timeout(2000)
            self.click_icon_button("Add")
            self.page.wait_for_timeout(2000)
            return self.verify_text_exists("Add Proxy Server", timeout=5000)
        except Exception as e:
            logger.error(f"Error opening Add Proxy Server dialog: {e}")
            return False

    def fill_proxy_server_name(self, name: str) -> bool:
        """Fill the Name field in the Add/Edit Proxy Server dialog.

        Args:
            name: The proxy server name to enter
        Returns True if the field was filled successfully.
        """
        try:
            logger.info(f"Filling proxy server name: {name}")
            self.page.fill('input[name="enter-name"]', name)
            return True
        except Exception as e:
            logger.error(f"Error filling proxy server name: {e}")
            return False

    def click_accept_in_dialog(self) -> bool:
        """Click the Accept button in the Add/Edit Proxy Server dialog."""
        try:
            logger.info("Clicking Accept button in dialog")
            self.click_button("Accept")
            self.page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error clicking Accept button: {e}")
            return False

    def click_cancel_in_dialog(self) -> bool:
        """Click the Cancel button in the Add/Edit Proxy Server dialog."""
        try:
            logger.info("Clicking Cancel button in dialog")
            self.click_button("Cancel")
            self.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            logger.error(f"Error clicking Cancel button: {e}")
            return False

    def get_user_proxy_servers_table_header(self) -> str:
        """Get the header text of the User Proxy Servers table.

        Returns:
            The header text as a string, or empty string on failure.
        """
        try:
            header_locator = self.page.locator('.sw-table .sw-table-header')
            if header_locator.count() > 0:
                text = header_locator.first.inner_text().strip()
                logger.info(f"Table header: {text}")
                return text
            logger.warning("User Proxy Servers table header not found")
            return ""
        except Exception as e:
            logger.error(f"Error getting table header: {e}")
            return ""

    def get_user_proxy_servers_row_count(self) -> int:
        """Get the number of rows in the User Proxy Servers table."""
        try:
            self.page.wait_for_selector('.sw-table-body__cont__table', state="visible", timeout=5000)
            rows = self.page.locator('.sw-table-body__cont__table .sw-table-row')
            count = rows.count()
            logger.info(f"User Proxy Servers table row count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting table row count: {e}")
            return 0

    def select_proxy_server_row(self, index: int = 0) -> bool:
        """Select a row in the User Proxy Servers table by its index.

        Args:
            index: The row index to select (0-based)
        """
        try:
            checkboxes = self.page.locator('.sw-table .sw-table-row input[type="checkbox"]')
            if checkboxes.count() > index:
                checkboxes.nth(index).check()
                logger.info(f"Selected row at index {index}")
                return True
            logger.warning(f"No row found at index {index}")
            return False
        except Exception as e:
            logger.error(f"Error selecting row: {e}")
            return False

    # ---------- Proxy Forwarding tab ----------

    def fill_proxy_web_server(self, server: str) -> bool:
        """Fill the Proxy Web Server input on the Proxy Forwarding tab.

        Args:
            server: The proxy server address to enter
        """
        try:
            logger.info(f"Filling Proxy Web Server: {server}")
            self.switch_tab("Proxy Forwarding", tab_level="l1")
            self.page.wait_for_timeout(2000)
            self.page.fill('input[name="proxyweb"]', server)
            return True
        except Exception as e:
            logger.error(f"Error filling Proxy Web Server: {e}")
            return False

    def fill_proxy_web_port(self, port: str) -> bool:
        """Fill the Proxy Web Server Port input on the Proxy Forwarding tab.

        Args:
            port: The port number to enter
        """
        try:
            logger.info(f"Filling Proxy Web Server Port: {port}")
            self.switch_tab("Proxy Forwarding", tab_level="l1")
            self.page.wait_for_timeout(2000)
            self.page.fill('input[name="proxywebport"]', port)
            return True
        except Exception as e:
            logger.error(f"Error filling Proxy Web Server Port: {e}")
            return False

    def accept_proxy_forwarding_settings(self) -> bool:
        """Click Accept on the Proxy Forwarding tab to save settings."""
        try:
            logger.info("Accepting Proxy Forwarding settings")
            self.click_button("Accept")
            self.page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error accepting settings: {e}")
            return False

    def cancel_proxy_forwarding_settings(self) -> bool:
        """Click Cancel on the Proxy Forwarding tab to discard changes."""
        try:
            logger.info("Cancelling Proxy Forwarding settings")
            self.click_button("Cancel")
            self.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            logger.error(f"Error cancelling settings: {e}")
            return False
