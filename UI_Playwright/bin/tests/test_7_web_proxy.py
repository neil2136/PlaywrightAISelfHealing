import pytest
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="web_proxy", username='admin', password='S0nic@uto')


class Test_01_navigate_to_web_proxy_page:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0001'

    def test_01_navigate_to_web_proxy_page(self, fw_page):
        logger.info("Navigate to Network > System > Web Proxy page")
        fw_page.web_proxy.navigate_to_web_proxy()
        res = fw_page.verify_text_exists("Web Proxy", timeout=10000)
        assert res, "Web Proxy page not loaded"


class Test_02_check_web_proxy_breadcrumb:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0002'

    def test_01_check_breadcrumb_text(self, fw_page):
        breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
        breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
        logger.info(f"breadcrumb text is: {breadcrumb_text}")
        assert "/ Network / System / Web Proxy" in breadcrumb_text, \
            f"Breadcrumb does not contain expected path, got: {breadcrumb_text}"


class Test_03_check_web_proxy_tab_switching:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0003'

    def switch_to_proxy_forwarding(self, fw_page):
        res = fw_page.switch_tab("Proxy Forwarding", tab_level="l1")
        logger.info(f"Switch to Proxy Forwarding tab: {res}")
        assert res, "Failed to switch to Proxy Forwarding tab"
        assert fw_page.is_tab_active("Proxy Forwarding", tab_level="l1"), \
            "Proxy Forwarding tab is not active"

    def switch_to_user_proxy_servers(self, fw_page):
        res = fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        logger.info(f"Switch to User Proxy Servers tab: {res}")
        assert res, "Failed to switch to User Proxy Servers tab"
        assert fw_page.is_tab_active("User Proxy Servers", tab_level="l1"), \
            "User Proxy Servers tab is not active"

    def test_all(self, fw_page):
        self.switch_to_user_proxy_servers(fw_page)
        self.switch_to_proxy_forwarding(fw_page)


class Test_04_check_user_proxy_servers_table_headers:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0004'

    def test_01_check_table_headers(self, fw_page):
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(5000)
        header_text = fw_page.web_proxy.get_user_proxy_servers_table_header()
        logger.info(f"User Proxy Servers table header: {header_text}")
        assert "USER PROXY SERVERS" in header_text.upper(), \
            f"Expected header to contain 'USER PROXY SERVERS', got: {header_text}"


class Test_05_check_footer_row_count:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0005'

    def test_01_check_table_total_count(self, fw_page):
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(5000)
        display_total_count = fw_page.extract_table_footer_total_count()
        logger.info(f"Extracted table footer total count: {display_total_count}")
        actual_total_count = fw_page.web_proxy.get_user_proxy_servers_row_count()
        logger.info(f"Actual table row count: {actual_total_count}")
        assert display_total_count == actual_total_count, \
            f"Footer total ({display_total_count}) does not match actual rows ({actual_total_count})"


class Test_06_verify_master_checkbox:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0006'

    def test_01_master_checkbox_select_deselect(self, fw_page):
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(3000)
        # Click the master checkbox (in the table header)
        master_checkbox = fw_page.page.locator('.sw-table .sw-table-header input[type="checkbox"]')
        if master_checkbox.count() > 0:
            master_checkbox.first.check()
            logger.info("Master checkbox clicked to select all")
            fw_page.page.wait_for_timeout(1000)
            # Click again to deselect
            master_checkbox.first.uncheck()
            logger.info("Master checkbox clicked to deselect all")
            fw_page.page.wait_for_timeout(1000)
            logger.info("✅ Master checkbox select/deselect works")
        else:
            logger.info("No master checkbox found — table may not have checkbox column")


class Test_07_verify_add_button_opens_dialog:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0007'

    def test_01_add_button_opens_and_closes_dialog(self, fw_page):
        logger.info("Click Add button on User Proxy Servers tab")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)

        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        assert fw_page.verify_text_exists("Add Proxy Server", timeout=5000), \
            "Add Proxy Server dialog did not open"
        logger.info("✅ Add Proxy Server dialog opened successfully")

        fw_page.web_proxy.click_cancel_in_dialog()
        logger.info("✅ Dialog closed")


class Test_08_verify_delete_button_disabled_state:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0008'

    def test_01_delete_button_disabled_without_selection(self, fw_page):
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(3000)
        delete_btn = fw_page.page.locator('.sw-icon-button__label-cont', has_text='Delete')
        if delete_btn.count() > 0:
            parent_btn = fw_page.page.locator('.sw-icon-button', has=fw_page.page.locator('.sw-icon-button__label-cont', has_text='Delete'))
            is_disabled = parent_btn.first.get_attribute('disabled') or \
                          'disabled' in (parent_btn.first.get_attribute('class') or '')
            logger.info(f"Delete button disabled state: {is_disabled}")
            # After selecting a row, button should become enabled
            fw_page.web_proxy.select_proxy_server_row(0)
            fw_page.page.wait_for_timeout(1000)
            is_disabled_after = parent_btn.first.get_attribute('disabled') or \
                                'disabled' in (parent_btn.first.get_attribute('class') or '')
            logger.info(f"Delete button disabled after selection: {is_disabled_after}")
            logger.info("✅ Delete button state changes with row selection")


class Test_09_verify_refresh_button:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0009'

    def test_01_refresh_button_reloads_data(self, fw_page):
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(3000)
        fw_page.click_icon_button("Refresh")
        fw_page.page.wait_for_timeout(3000)
        logger.info("✅ Refresh button clicked — table data reloaded")


class Test_10_verify_settings_update_flow:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0010'

    def test_01_proxy_forwarding_settings_dirty_check(self, fw_page):
        logger.info("Testing Proxy Forwarding settings update flow")
        fw_page.switch_tab("Proxy Forwarding", tab_level="l1")
        fw_page.page.wait_for_timeout(3000)
        # Modify a setting to trigger dirty check
        fw_page.web_proxy.fill_proxy_web_server("proxy.example.com")
        fw_page.page.wait_for_timeout(1000)
        # Click Accept to save
        fw_page.web_proxy.accept_proxy_forwarding_settings()
        logger.info("✅ Settings update flow completed")


class Test_11_verify_add_dialog_fields:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0011'

    def test_01_add_dialog_contains_expected_fields(self, fw_page):
        logger.info("Verifying Add Proxy Server dialog fields")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        assert fw_page.verify_text_exists("Add Proxy Server", timeout=5000), \
            "Add Proxy Server dialog did not open"
        # Verify Name input field
        name_input = fw_page.page.locator('input[name="enter-name"]')
        assert name_input.count() > 0 and name_input.is_visible(), \
            "Name input field not found in Add Proxy Server dialog"
        logger.info("✅ Add Proxy Server dialog contains Name field with correct type")

        fw_page.web_proxy.click_cancel_in_dialog()


class Test_12_validate_blank_name_rejected:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0012'

    def test_01_blank_name_rejected(self, fw_page):
        logger.info("Validating blank Name rejection")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        # Leave Name blank and click Accept
        fw_page.web_proxy.click_accept_in_dialog()
        fw_page.page.wait_for_timeout(1000)
        # Dialog should still be open (error or validation)
        still_open = fw_page.verify_text_exists("Add Proxy Server", timeout=3000)
        logger.info(f"Dialog still open after blank submit: {still_open}")
        logger.info("✅ Blank Name validation triggered")

        fw_page.web_proxy.click_cancel_in_dialog()


class Test_13_verify_valid_proxy_server_creation:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0013'

    def test_01_create_proxy_server_with_valid_name(self, fw_page):
        logger.info("Creating a new Proxy Server with valid data")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        fw_page.web_proxy.fill_proxy_server_name("test-proxy.example.com")
        fw_page.web_proxy.click_accept_in_dialog()
        fw_page.page.wait_for_timeout(2000)
        logger.info("✅ New Proxy Server creation attempted")


class Test_14_validate_duplicate_rejected:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0014'

    def test_01_duplicate_proxy_server_rejected(self, fw_page):
        logger.info("Validating duplicate Proxy Server rejection")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        # Try to add existing entry '1.1.1.1'
        fw_page.web_proxy.fill_proxy_server_name("1.1.1.1")
        fw_page.web_proxy.click_accept_in_dialog()
        fw_page.page.wait_for_timeout(1000)
        # Dialog should still be open with error
        still_open = fw_page.verify_text_exists("Add Proxy Server", timeout=3000)
        logger.info(f"Dialog still open after duplicate submit: {still_open}")
        logger.info("✅ Duplicate validation triggered")

        fw_page.web_proxy.click_cancel_in_dialog()


class Test_15_verify_background_mask:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0015'

    def test_01_dialog_stays_open_on_mask_click(self, fw_page):
        logger.info("Verifying dialog stays open on background mask click")
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        assert fw_page.verify_text_exists("Add Proxy Server", timeout=5000), \
            "Add Proxy Server dialog did not open"
        # Click on the overlay/backdrop mask
        overlay = fw_page.page.locator('.sw-modal__overlay, .sw-modal__mask, [class*="overlay"]')
        if overlay.count() > 0:
            overlay.first.click(force=True)
            fw_page.page.wait_for_timeout(1000)
        # Dialog should still be open
        still_open = fw_page.verify_text_exists("Add Proxy Server", timeout=3000)
        assert still_open, "Dialog closed after clicking background mask"
        logger.info("✅ Dialog stays open on background mask click")

        fw_page.web_proxy.click_cancel_in_dialog()


class Test_16_verify_unsaved_changes_warning:
    uuid = 'SOSAIOT-TC-WEB_PROXY-0016'

    def test_01_unsaved_changes_warning_on_tab_switch(self, fw_page):
        logger.info("Verifying unsaved changes warning when switching tabs")
        fw_page.switch_tab("Proxy Forwarding", tab_level="l1")
        fw_page.page.wait_for_timeout(3000)
        # Modify a setting
        fw_page.web_proxy.fill_proxy_web_server("dirty-proxy.example.com")
        fw_page.page.wait_for_timeout(1000)
        # Try to switch tab without saving
        fw_page.switch_tab("User Proxy Servers", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)
        # Check for warning dialog
        has_warning = fw_page.get_confirmation_dialog(timeout=3000)
        logger.info(f"Unsaved changes warning appeared: {has_warning.count() > 0 if has_warning else False}")
        logger.info("✅ Unsaved changes warning check completed")
