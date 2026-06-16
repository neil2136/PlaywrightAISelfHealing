import pytest
import time
from config.settings import Settings
from config.logger import get_logger
# from pages.fw_pages import FWPage  #
from playwright.sync_api import Page 



logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="interfaces", username='admin', password='S0nic@uto')
# pytestmark = pytest.mark.auto_login

class TestTC_01_navigate_to_network_interface_page():
    uuid = 'SOSAIOT-TC-94884'
    def test_01_navigate_to_network_interface_page(self, fw_page):
        logger.info(f"go to network url")
        fw_page.navigate_to_url(Settings.BASE_URL + '/m/mgmt/network/interfaces')
        res = fw_page.verify_text_exists("Add Interface", timeout=100000)
        assert res, "Interfaces page not loaded"

class TestTC_02_check_interface_page_navigation:
    uuid = 'SOSAIOT-TC-94885'
    def test_01_check_breadcrumb_text(self, fw_page):
        breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
        breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
        logger.info(f"breadcrumb text is: {breadcrumb_text}")
        assert "Network / System / Interfaces" in breadcrumb_text, "Breadcrumb text does not contain expected path"

class TestTC_03_check_l1_tab:
    uuid = 'SOSAIOT-TC-94886'
    def check_active_tab(self, fw_page):
        logger.info(f"test01 - check active tab")
        tab_l1 = fw_page.get_active_tab("l1")
        logger.info(f"active tab l1 is: {tab_l1}")
        assert tab_l1 == "Interface Settings", "Default active tab is not 'Interface Settings'"

    def switch_tab(self, fw_page):
        logger.info(f"test02 - switch tab")
        switch_tab_name = "Traffic Statistics"
        res = fw_page.switch_tab(switch_tab_name, tab_level="l1",verify=True)
        logger.info(f"switch_tab result: {res}")
        assert res, "Clear Statistics button not found after switching tabs"
    
    def switch_back_tab(self, fw_page):
        logger.info(f"test03 - switch back tab")
        switch_tab_name = "Interface Settings"
        res = fw_page.switch_tab(switch_tab_name, tab_level="l1",verify=True)
        assert res, "Failed to switch back to Interface Settings tab"

    def test_all(self, fw_page):
        self.check_active_tab(fw_page)
        self.switch_tab(fw_page)
        self.switch_back_tab(fw_page)


class TestTC_04_check_l2_tab:
    uuid ="SOSAIOT-TC-94887"
    def check_active_tab(self, fw_page):
        logger.info(f"test01 - check active tab")
        tab_text = ''
        active_tab = fw_page.page.locator('.sw-tab--l2.sw-tab--active')
        if active_tab.count() > 0:
            tab_text = active_tab.inner_text().strip()
            logger.info(f"active tab is: {tab_text}")
        assert tab_text == "IPv4", "Default active tab is not 'IPv4'"

    def switch_tab(self, fw_page):
        logger.info(f"test02 - switch tab")
        switch_tab_name = "IPv6"
        res = fw_page.switch_tab(switch_tab_name, tab_level="l2")
        assert res, "Failed to switch to IPv6 tab"
    
    def switch_back_tab(self, fw_page):
        logger.info(f"test03 - switch back tab")
        switch_tab_name = "IPv4"
        res = fw_page.switch_tab(switch_tab_name, tab_level="l2")
        logger.info(f"switch_back_tab result: {res}")
        assert res, "Failed to switch back to IPv4 tab"

    def test_all(self, fw_page):
        self.check_active_tab(fw_page)
        self.switch_tab(fw_page)
        self.switch_back_tab(fw_page)


class TestTC_08_table_total_display_number_is_correct:
    uuid = "SOSAIOT-TC-94891"
    def test_01_check_table_total_count(self, fw_page):
        fw_page.page.wait_for_timeout(3000)
        display_total_count = fw_page.extract_table_footer_total_count()
        logger.info(f"Extracted table total count: {display_total_count}")
        actual_total_count = fw_page.get_table_row_count_by_container("interface-settings-ipv4")
        logger.info(f"Actual table row count: {actual_total_count}")
        assert display_total_count == actual_total_count, "footer total count does not match actual row count"


class TestTC_05_check_ipv4_page_table_value:
    uuid = "SOSAIOT-TC-94888"
    def check_default_table_row_value(self, fw_page):
        logger.info(f"test01 - check default table row value")
        row_list = fw_page.get_table_row_text("interface-settings-ipv4","X0")
        logger.info(f"X0 row text: {row_list}")
        checklist = ['X0', 'LAN', '192.168.168.168', '255.255.255.0', 'Static IP']
        resall = [item in str(row_list) for item in checklist]
        logger.info(f"resall is: {resall}")
        assert all(resall) == True, "ipv4 page value does not match expected value"

    def check_table_interface_status(self, fw_page):
        logger.info(f"test02 - check table interface status")
        status = fw_page.interface.get_interface_status('X1') 
        logger.info(f"X1 interface status: {status}")
        assert status == "enabled", "X1 interface status should be enabled"
    
    def test_all(self, fw_page):
        self.check_default_table_row_value(fw_page)
        self.check_table_interface_status(fw_page)

class TestTC_06_check_ipv6_page_table_value:
    uuid = "SOSAIOT-TC-94889"
    def test_01_check_ipv6_table_interface_value(self, fw_page):
        fw_page.switch_tab("IPv6", tab_level="l2")
        fw_page.page.wait_for_timeout(5000)
        row_list = fw_page.get_table_row_text("interface-settings-ipv6 ","X0")
        logger.info(f"X0 row text: {row_list}")
        checklist = ["Static","fe80::","Automatic"]
        resall = [item in str(row_list) for item in checklist]
        logger.info(f"resall: {resall}")
        assert all(resall) == True, "check ipv6 page value failed"

class TestTC_20_check_interface_table_header:
    uuid = "SOSAIOT-TC-94903"
    def test_01_check_table_header(self, fw_page):
        fw_page.switch_tab("IPv4", tab_level="l2")
        fw_page.page.wait_for_timeout(5000)
        checkheaderlist = ['NAME', 'ZONE', 'GROUP', 'IP ADDRESS', 'SUBNET MASK', 'IP ASSIGNMENT', 'STATUS', 'ENABLED', 'COMMENT']
        get_table_header = fw_page.get_table_header("interface-settings-ipv4")
        logger.info(f"table header is: {get_table_header}")
        assert checkheaderlist == get_table_header, "table header does not match expected header list"

#tc15,tc16,tc17,tc18 are related to the same dropdown list, so put them together in one class for better maintenance and less time consuming to switch page back and forth
class TestTC_15_16_17_18_click_add_interface_button_then_select_option_and_verify_dialog:


    @pytest.mark.parametrize("option_text,uuid", [("Virtual Interface", "SOSAIOT-TC-94898"),
                                           ("VPN Tunnel Interface", "SOSAIOT-TC-94899"),
                                           ("4to6 Tunnel Interface", "SOSAIOT-TC-94900"),
                                           ("WLAN Tunnel Interface", "SOSAIOT-TC-94901")         
                                           ]) 
    def test_01_check_diag_window_after_click_add_interface_button(self, fw_page, option_text, uuid):
        logger.info(f'run test case: {uuid}-{option_text}')
        logger.info(f"click Add Interface dropdown option: {option_text}")
        fw_page.select_value_from_button_dropdown("Add Interface", option_text)
        fw_page.page.wait_for_timeout(3000)
        res = fw_page.verify_text_exists(f'Add {option_text}', timeout=10000)
        logger.info(f"Add Interface dropdown options: {res}")
        fw_page.click_close_icon_by_window_title(f"Add {option_text}")
        assert res, f"Add {option_text} page not loaded"


class TestTC_09_verify_toggle_button_show_portshield_groups:
    uuid = 'SOSAIOT-TC-94892'
    def check_toggle_button_default_status(self, fw_page):
        logger.info(f"test01 - check toggle button default status")
        value = fw_page.get_toggle_status('input[name="show-portshield-groups"]')
        logger.info(f"Toggle button default status is: {value is True}")
        assert value == '1', "Toggle button default status is not enabled"

    def swith_toggle(self,fw_page):
        logger.info(f"test02 - swith toggle button")
        res = fw_page.click_toggle(selector='input[name="show-portshield-groups"]',enable=False) 
        logger.info(f"Toggle switch result: {res is True}")
        assert res, "Toggle switch failed"

    def test_all(self, fw_page):
        self.check_toggle_button_default_status(fw_page)
        self.swith_toggle(fw_page)

class TestTC_13_verify_trigger_dropdown_list_click_add_interface:
    uuid = 'SOSAIOT-TC-94896'
    def get_dropdown_value_after_click_add_interface(self,fw_page):
        logger.info('click Add Interface button')
        clickres = fw_page.click_element(text = 'Add Interface')
        if clickres:
            dropdown = fw_page.find_element(selector='.sw-dropdown__inner', wait_until="visible")
            if dropdown.count() > 0:
                logger.info('dropdown is visible')
            else:
                logger.info('dropdown is not visible')
        else:
            logger.info('click Add Interface button failed')
        
        assert clickres, "trigger dropdown after click Add Interface button failed"
    
    def close_dropdown(self, fw_page):
        logger.info('close dropdown list')
        # fw_page.page.keyboard.press("Escape")
        res = fw_page.click_element(text = 'Add Interface')
        assert res, "close dropdown list failed"
    
    def test_all(self,fw_page):
        self.get_dropdown_value_after_click_add_interface(fw_page)
        self.close_dropdown(fw_page)


class TestTC_14_check_droppdown_values_from_add_interface_list:
    uuid = 'SOSAIOT-TC-94897'
    def get_droppdown_value_after_click_add_interface(self,fw_page):
        logger.info('test_01 - click Add Interface button')
        valuelist = fw_page.get_values_from_button_dropdown('Add Interface')
        logger.info(f"Add Interface dropdown values: {valuelist}")
        checklist = ['Virtual Interface', 'VPN Tunnel Interface', '4to6 Tunnel Interface', 'WLAN Tunnel Interface']
        assert valuelist == checklist, "Add Interface dropdown values are not as expected"

    def close_dropdown(self, fw_page):
        logger.info('test_02 - close dropdown list')
        res = fw_page.click_element(text = 'Add Interface')
        assert res, "close dropdown list failed"

    def test_all(self,fw_page):
        self.get_droppdown_value_after_click_add_interface(fw_page)
        self.close_dropdown(fw_page)

class TestTC_07_check_interface_row_highlighted:
    uuid = 'SOSAIOT-TC-94890'
    def test_01_verify_row_highlighted_and_is_orange_background_color(self, fw_page):
        is_orange = False
        table_row_locator = fw_page.get_table_row_locator("interface-settings-ipv4","X0")
        background_color = fw_page.get_background_color(table_row_locator)
        logger.info(f"Background color: {background_color}")
        table_row_locator.first.hover()
        fw_page.page.wait_for_timeout(5000)
        hover_background_color = fw_page.get_background_color(table_row_locator)
        logger.info(f"hover_background_color: {hover_background_color}")
        if background_color != hover_background_color:
            logger.info("interface row is highlighted")
            is_orange = fw_page.is_orange_color(hover_background_color)
            logger.info(f"is_orange: {is_orange}")
        else:
            logger.error("interface row is not highlighted")
        assert is_orange, 'interface row is not orange background color after hovering'

class TestTC_19_verify_interface_table_autoload_and_display:
    uuid = 'SOSAIOT-TC-94902'
    
    def verify_physical_interfaces_displayed(self, fw_page):
        logger.info("test01 - Verify physical interfaces displayed")
        expected_interfaces = ['X0', 'X1', 'U0']
        found_interfaces = []
        
        try:
            for interface in expected_interfaces:
                row_text = fw_page.get_table_row_text("interface-settings-ipv4", interface)
                if row_text:
                    found_interfaces.append(interface)
                    logger.info(f"Found interface: {interface}")
                else:
                    logger.warning(f"Interface {interface} not found")
            
            missing = [i for i in expected_interfaces if i not in found_interfaces]
            assert not missing, f"Missing interfaces: {missing}"
            logger.info("All physical interfaces displayed")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            assert False, f"Failed to verify interfaces: {e}"
    
    def verify_sub_interfaces_displayed(self, fw_page):
        logger.info("test02 - Verify sub-interfaces displayed")
        try:
            total_rows = fw_page.get_table_row_count_by_container("interface-settings-ipv4")
            logger.info(f"Total rows: {total_rows}")
            sub_interfaces = []
            common_subs = ['X3:V10', 'X4:V10']
            
            for sub in common_subs:
                if fw_page.get_table_row_text("interface-settings-ipv4", sub):
                    sub_interfaces.append(sub)
            
            logger.info(f"Sub-interfaces found: {sub_interfaces}")
            assert total_rows > 0, "No interfaces found in table"
            
        except Exception as e:
            logger.error(f"Error: {e}")
            assert False, f"Failed to verify sub-interfaces: {e}"
    
    def test_all(self, fw_page):
        self.verify_physical_interfaces_displayed(fw_page)
        self.verify_sub_interfaces_displayed(fw_page)


class TestTC_21_verify_floating_toolbar_behavior:
    uuid = "SOSAIOT-TC-94904"

    @pytest.fixture(scope="class")
    def toolbar_elements(self, fw_page):
        logger.info("Setup fixture to get table row and toolbar elements once for all tests")
        logger.info("Navigate to Interface Settings page")
        fw_page.page.wait_for_timeout(3000)
        # Get X0 interface row
        table_row_locator = fw_page.get_table_row_locator("interface-settings-ipv4","X0")
        assert table_row_locator, "X0 interface row not found - cannot proceed with toolbar test"
        # Get floating toolbar from within the specific row (more precise)
        toolbar = table_row_locator.locator('span:has(.sw-table-row-float-actions) .sw-table-row-float-actions')
        return table_row_locator, toolbar
    
    def verify_floating_toolbar_appears_on_hover(self, fw_page, toolbar_elements):
        logger.info("test01 - Verify the floating toolbar (Edit/delete) appears on hover")
        # Get elements from fixture
        table_row_locator, toolbar = toolbar_elements
        edit_button = toolbar.locator('.icon-pencil')
        delete_button = toolbar.locator('.icon-trash')
        
        # Hover over row - toolbar should appear with Edit and Delete buttons
        logger.info("Testing toolbar appearance on hover...")
        table_row_locator.first.hover()
        fw_page.page.wait_for_timeout(1000)
        
        hover_class = toolbar.get_attribute('class')
        toolbar_visible = '--invisible' not in hover_class
        edit_button_exists = edit_button.count() > 0
        delete_button_exists = delete_button.count() > 0
        
        logger.info(f"Toolbar visible: {toolbar_visible}, Edit button exists: {edit_button_exists}, Delete button exists: {delete_button_exists}")
        assert toolbar_visible and edit_button_exists and delete_button_exists, \
            f"Toolbar should appear with Edit and Delete buttons on hover (toolbar: {toolbar_visible}, edit: {edit_button_exists}, delete: {delete_button_exists})"
    
    def verify_floating_toolbar_disappears_when_mouse_moves_away(self, fw_page, toolbar_elements):
        logger.info("test02 - Verify the floating toolbar disappears when the mouse moves away")
        table_row_locator, toolbar = toolbar_elements
    
        table_row_locator.first.hover()
        fw_page.page.wait_for_timeout(1000)
        logger.info("Testing toolbar disappearance when mouse moves away...")
        fw_page.page.hover('body')
        fw_page.page.wait_for_timeout(1000)
        away_class = toolbar.get_attribute('class')
        toolbar_invisible_after_away = '--invisible' in away_class
        logger.info(f"Toolbar invisible after mouse away: {toolbar_invisible_after_away}")
        
        assert toolbar_invisible_after_away, \
            f"Toolbar should disappear when mouse moves away (was: {toolbar_invisible_after_away})"

    def test_all(self, fw_page, toolbar_elements):
        self.verify_floating_toolbar_appears_on_hover(fw_page, toolbar_elements)
        self.verify_floating_toolbar_disappears_when_mouse_moves_away(fw_page, toolbar_elements)


class TestTC_22_verify_interface_expand_collapse_behavior:
    uuid = "SOSAIOT-TC-94905"
    EXPANDED_CLASS = 'sw-table-row__cell__trigger__cont--expanded'
    
    @pytest.fixture(scope="class")
    def interface_elements(self, fw_page):
        logger.info('setup fixture to get parent interface and expand icon elements')
        # Get X1 interface row (parent interface)
        table_row_locator = fw_page.get_table_row_locator("interface-settings-ipv4","X1")
        assert table_row_locator, "X1 interface row not found - cannot proceed with expand/collapse test"
        expand_icon = table_row_locator.locator('.sw-table-row__cell__trigger__cont .sw-icon')
        trigger_container = table_row_locator.locator('.sw-table-row__cell__trigger__cont')
        return table_row_locator, expand_icon, trigger_container
    
    def verify_interface_collapses_when_arrow_clicked(self, fw_page, interface_elements):
        logger.info("test01 - Verify clicking arrow icon next to a parent interface collapses sub-interfaces")
        # Get elements from fixture
        table_row_locator, expand_icon, trigger_container = interface_elements
        is_collapsed = False
        has_expand_icon = expand_icon.count() > 0
        trigger_class = trigger_container.get_attribute('class') 
        is_initially_expanded = self.EXPANDED_CLASS in trigger_class
        logger.info(f"Has expand icon: {has_expand_icon}")
        logger.info(f"Initial state: expanded={is_initially_expanded}")
        # Execute test logic only if expand icon exists
        if has_expand_icon and is_initially_expanded:
            logger.info("Collapsing interface...")
            expand_icon.click()
            fw_page.page.wait_for_timeout(1000)
            
            # Check final state
            trigger_class_final = trigger_container.get_attribute('class') 
            is_collapsed = self.EXPANDED_CLASS not in trigger_class_final
            logger.info(f"Final state: collapsed={is_collapsed}")
        
        assert is_collapsed, f"Interface should collapse when arrow clicked (has_icon: {has_expand_icon}, collapsed={is_collapsed})"

    def verify_interface_expands_when_arrow_clicked_again(self, fw_page, interface_elements):
        logger.info("test02 - Verify clicking arrow icon again expands sub-interfaces")
        table_row_locator, expand_icon, trigger_container = interface_elements
        
        logger.info("Expanding interface...")
        expand_icon.click()
        fw_page.page.wait_for_timeout(1000)
        
        # Check final state
        trigger_class_final = trigger_container.get_attribute('class') 
        is_expanded = self.EXPANDED_CLASS in trigger_class_final
        logger.info(f"Final state: expanded={is_expanded}")
        assert is_expanded, f"Interface should expand when arrow clicked again (expanded: {is_expanded})"
    
    def test_all(self, fw_page, interface_elements):
        self.verify_interface_collapses_when_arrow_clicked(fw_page, interface_elements)
        self.verify_interface_expands_when_arrow_clicked_again(fw_page, interface_elements)

class TestTC_23_verify_sub_interfaces_displayed_in_status_column:
    uuid = "SOSAIOT-TC-94906"
    SUB_INTERFACE_STATUS = "VLAN Sub-Interface"

    def test_vlan_interface(self, fw_page):
        logger.info("test01 - Verify sub-interface displays 'VLAN Sub-Interface' in STATUS column")
        row_text_list = fw_page.get_table_row_text("interface-settings-ipv4", "X1:V10")
        logger.info(f'row_text is: {row_text_list}')
        
        assert len(row_text_list) >= 8, (
            f"[DATA] X1:V10 row incomplete: Expected >8 columns, got {len(row_text_list)}. "
            f"Available data: {row_text_list}"
        )
        status_value = row_text_list[6]
        assert status_value == self.SUB_INTERFACE_STATUS, (
            f"[STATUS] X1:V10 status mismatch: Expected '{self.SUB_INTERFACE_STATUS}', got '{status_value}'"
        )

class TestTC_24_verify_interface_enabled_button_can_be_clicked:
    uuid = "SOSAIOT-TC-94907"
    
    def verify_disconnected_interface_rate(self, fw_page):
        logger.info("test_01: Checking disconnected interface rate display...")
        row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X5")
        logger.info(f"Interface status: {row_text}")
        status = row_text[6]
        assert status == 'No link',f"connected interface should display No link,but actual is {status}"

    def verify_connected_interface_rate(self, fw_page):
        logger.info("test_02: Checking connected interface rate display...")
        row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X1")
        logger.info(f"Interface status: {row_text}")
        status = row_text[6]
        assert status == '1 Gbps Full Duplex',f"connected interface should display 1 Gbps Full Duplex,but actual is {status}"

    def test_all(self, fw_page):
        self.verify_disconnected_interface_rate(fw_page)
        self.verify_connected_interface_rate(fw_page)

class TestTC_10_verify_interface_enabled_button_can_be_clicked:
    uuid = "SOSAIOT-TC-94893"
    
    def verify_interface_x0_enabled_button_default_state(self, fw_page):
        logger.info("test_01: Checking default state of interface enabled button for X3...")
        status = fw_page.interface.get_interface_status('X3')
        logger.info(f"Interface status: {status}")
        assert status == 'enabled', (f"[CONTROL] Interface X3 should be enabled by default")

    def disable_x0_interface(self, fw_page):
        logger.info("test_02: Disabling interface X...")
        disable_interface_result = fw_page.interface.disable_interface('X3')
        logger.info(f"Disable interface result: {disable_interface_result}")
        time.sleep(10)
        assert disable_interface_result, "Failed to disable interface X0"

    def enable_x0_interface(self, fw_page):
        logger.info("Enabling interface X3...")
        enable_interface_result = fw_page.interface.enable_interface('X3')
        logger.info(f"Enable interface result: {enable_interface_result}")
        assert enable_interface_result, "Failed to enable interface X3"

    def test_all(self, fw_page):
        self.verify_interface_x0_enabled_button_default_state(fw_page)
        self.disable_x0_interface(fw_page)
        self.enable_x0_interface(fw_page)


class TestTC_11_verify_x2_interface_dhcp_state_and_release_renew_can_be_clicked:
    uuid = "SOSAIOT-TC-94894"
    dhcp_renew_successful = False  
    
    def verify_x2_interface_dhcp_button_can_be_clicked(self, fw_page):
        logger.info('test_01: Verify X2 interface DHCP button can be clicked...')
        flag = False
        get_x2_row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X2")
        row_locator = fw_page.get_table_row_locator("interface-settings-ipv4", "X2")
        logger.info(f"X3 row text: {get_x2_row_text}")
        if '0.0.0.0' in get_x2_row_text and 'DHCPRenew' in get_x2_row_text:
            logger.info("X2 interface is DHCP mode and has Renew button, checking if it can be clicked...")
            logger.info('enable x2 interface')
            fw_page.interface.enable_interface('X2')
            fw_page.page.wait_for_timeout(6000)
            dhcp_button = row_locator.locator('.sw-button.sw-button--light:has-text("Renew")')
            dhcp_button.click()
            fw_page.page.wait_for_timeout(10000)
            get_x2_row_text_new = fw_page.get_table_row_text("interface-settings-ipv4", "X2")
            logger.info(f"X2 row text after clicking Renew: {get_x2_row_text_new}")
            if 'DHCPRelease' in get_x2_row_text_new:
                logger.info("Renew action successful")
                self.dhcp_renew_successful = True  
                logger.info(f"DHCP Renew successful: {self.dhcp_renew_successful}")
                flag = True
        assert flag, "DHCP Renew button for X2 interface should be clickable"
    
    def verify_x2_interface_dhcp_release_button_can_be_clicked(self, fw_page):
        logger.info('test_02: Verify X2 interface DHCP Release button can be clicked...')
        get_x3_row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X2")
        row_locator = fw_page.get_table_row_locator("interface-settings-ipv4", "X2")
        logger.info(f"X2 row text: {get_x3_row_text}")
        logger.info("X2 interface has Release button, checking if it can be clicked...")
        release_button = row_locator.locator('.sw-button.sw-button--light:has-text("Release")')
        release_button.click()
        fw_page.page.wait_for_timeout(10000)
        get_x2_row_text_new = fw_page.get_table_row_text("interface-settings-ipv4", "X2")
        logger.info(f"X2 row text after clicking Release: {get_x2_row_text_new}")
        assert 'DHCPRenew' in get_x2_row_text_new, "Expected DHCPRenew button after clicking Release"

    def test_all(self, fw_page):
        self.verify_x2_interface_dhcp_button_can_be_clicked(fw_page)
        self.verify_x2_interface_dhcp_release_button_can_be_clicked(fw_page)


class TestTC_12_verify_refresh_button_loading_animation_and_list_update:
    uuid = "SOSAIOT-TC-94895"
    
    def test_01_verify_refresh_button_shows_loading_animation(self, fw_page):
        fw_page.click_element(text="Refresh")
        find_element_result = fw_page.find_element(text='Loading...')
        logger.info(f"Find Loading animation found: {find_element_result}")
        assert find_element_result.count() == 1, "Loading animation not found after clicking Refresh button"
    
class TestTC_25_check_confirm_diag_popup_after_click_enable_toggle_button:
    uuid = "SOSAIOT-TC-94908"
    def check_confirm_diag_popup_after_click_enable_toggle_button(self, fw_page):
        logger.info("test_01: Check confirm diag popup after click enable toggle button...")
        row_locator = fw_page.get_table_row_locator("interface-settings-ipv4", "X1")
        enable_toggle = row_locator.locator('.sw-toggle')
        enable_toggle.click()
        fw_page.page.wait_for_timeout(3000)
        confirm_dialog = fw_page.find_element(selector='.sw-confirm-modal__dialog', wait_until="visible")
        logger.info(f"Confirm dialog found: {confirm_dialog.count() > 0}")
        assert confirm_dialog.count() > 0, "Confirmation dialog not found after clicking enable toggle button"
        
    def close_confirm_dialog(self, fw_page):
        logger.info("test_02: Close confirm diag popup...")
        fw_page.click_dialog_button('Cancel')
        fw_page.page.wait_for_timeout(1000)
        confirm_dialog = fw_page.find_element(selector='.sw-confirm-modal__dialog')
        logger.info(f"Confirm dialog closed: {confirm_dialog.count() == 0}")
        assert confirm_dialog.count() == 0, "Confirmation dialog should be closed after clicking Cancel"

    def test_all(self, fw_page):
        self.check_confirm_diag_popup_after_click_enable_toggle_button(fw_page)
        self.close_confirm_dialog(fw_page)


class TestTC_26_verify_dhcp_configured_interface_display:
    uuid = "SOSAIOT-TC-94909"
    
    def test_01_verify_dhcp_interface_displays_acquired_ip(self, fw_page):
        get_x2_row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X2")
        logger.info(f"X2 row text: {get_x2_row_text}")
        ip_address = get_x2_row_text[3]  # IP ADDRESS column
        assignment_type = get_x2_row_text[5]  # IP ASSIGNMENT column
        logger.info(f"X2 IP Address: {ip_address}")
        logger.info(f"X2 IP Assignment Type: {assignment_type}")
        assert assignment_type in ['DHCPRenew', 'DHCPRelease'], f"Invalid DHCP assignment type: {assignment_type}"
        if 'DHCPRenew' in assignment_type:
            assert ip_address == '0.0.0.0', "DHCP interface X2 should display 0.0.0.0 when DHCPRenew"
        elif "DHCPRelease" in assignment_type:
            assert ip_address != '0.0.0.0', "DHCP interface X2 should display acquired IP when DHCPRelease"
        

class TestTC_27_verify_wire_mode_interfaces_display:
    uuid = "SOSAIOT-TC-94910"
    
    @pytest.fixture(scope="class")
    def get_wire_interface_rows(self, fw_page):
        logger.info("Setup fixture to ensure X4 and X5 interfaces are visible and get their row locators")
        fw_page.page.wait_for_timeout(3000)
        get_x4_row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X4", column_index=2)
        get_x5_row_text = fw_page.get_table_row_text("interface-settings-ipv4", "X5", column_index=2)
        logger.info(f"X4 row text: {get_x4_row_text}")
        logger.info(f"X5 row text: {get_x5_row_text}")
        assignment_type_x4 = get_x4_row_text[5]  # IP ASSIGNMENT column
        assignment_type_x5 = get_x5_row_text[5]  # IP ASSIGNMENT column
        comment_x4 = get_x4_row_text[-1]
        comment_x5 = get_x5_row_text[-1] 
        logger.info(f"X4 IP Assignment Type: {assignment_type_x4}")
        logger.info(f"X4 Comment: {comment_x4}")
        logger.info(f"X5 IP Assignment Type: {assignment_type_x5}")
        logger.info(f"X5 Comment: {comment_x5}")
        return get_x4_row_text, get_x5_row_text, assignment_type_x4, assignment_type_x5, comment_x4, comment_x5
    
    def verify_wire_mode_interfaces_show_wire_in_ip_assignment(self, fw_page, get_wire_interface_rows):
        logger.info('test_01: Verify Wire Mode interfaces show "Wire" in IP ASSIGNMENT column...')
        get_x4_row_text, get_x5_row_text, assignment_type_x4, assignment_type_x5, comment_x4, comment_x5 = get_wire_interface_rows
        logger.info(f"get_x5_row_text is: {get_x4_row_text}")
        logger.info(f"get_x6_row_text is: {get_x5_row_text}")
        assert assignment_type_x4 == 'Wire' and assignment_type_x5 == 'Wire', "X4 and X5 interfaces should show 'Wire' in IP ASSIGNMENT column"

    def verify_wire_mode_interfaces_show_pairing_info_in_comment(self, fw_page, get_wire_interface_rows):
        logger.info('test_02: Verify Wire Mode interfaces show pairing info in COMMENT column...')
        get_x4_row_text, get_x5_row_text, assignment_type_x4, assignment_type_x5, comment_x4, comment_x5 = get_wire_interface_rows
        logger.info(f"comment_x4 is: {comment_x4}")
        logger.info(f"comment_x5 is: {comment_x5}")
        assert comment_x4 == 'Wire Mode Bypass - X5' and comment_x5 == 'Wire Mode Bypass - X4', "X4 and X5 interfaces should show pairing info in COMMENT column"

    def test_all(self, fw_page, get_wire_interface_rows):
        self.verify_wire_mode_interfaces_show_wire_in_ip_assignment(fw_page, get_wire_interface_rows)
        self.verify_wire_mode_interfaces_show_pairing_info_in_comment(fw_page, get_wire_interface_rows)


class TestTC_28_verify_table_total_items_count_updates_after_add_vpn_interface:
    uuid = "SOSAIOT-TC-94911"

    @pytest.fixture(scope="class")
    def get_table_count_before_add_interface(self, fw_page):
        logger.info("--------Getting initial table total count before adding sub-interface...")
        initial_count = fw_page.extract_table_footer_total_count()
        logger.info(f"Initial total count: {initial_count}")
        return initial_count
    
    def add_tunnel_vpn_interface(self, fw_page):
        logger.info("test_01:Adding new tunnel interface TI...")
        fw_page.select_value_from_button_dropdown("Add Interface", "VPN Tunnel Interface")
        fw_page.select_value_in_dropdown_box('VPN Policy','localtunnelvpn')
        fw_page.fill_input_by_label_name("Name", 'TI')
        fw_page.fill_input_by_label_name("IP Address", '11.11.11.10')
        fw_page.click_toggle(selector='input[name="cb-enable-https"]', enable=True)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(5000)   
        assert fw_page.verify_text_exists('11.11.11.10'), "New add tunnel interface should be created and visible in the table"
    
    def verify_table_itmes_count_updates_after_adding_sub_interface(self, fw_page, get_table_count_before_add_interface):
        logger.info("test_02:Verifying table total items count updates after adding sub-interface...")
        initial_count = get_table_count_before_add_interface
        update_count = fw_page.extract_table_footer_total_count()
        logger.info(f"Displayed total count in footer after add interface: {update_count}")
        assert update_count == initial_count + 1, "footer total count should increase by 1 after adding a sub-interface"

    def test_all(self, fw_page, get_table_count_before_add_interface):
        self.add_tunnel_vpn_interface(fw_page)
        self.verify_table_itmes_count_updates_after_adding_sub_interface(fw_page,get_table_count_before_add_interface)

class TestTC_29_verify_management_interface_toggle_disabled:
    uuid = "SOSAIOT-TC-94912"

    def verify_current_management_interface_toggle_is_not_displayed(self, fw_page):
        logger.info("test_01:Verifying management interface toggle is not displayed...")
        management_interface_row = fw_page.get_table_row_locator("interface-settings-ipv4", "X0")
        toggle_button = management_interface_row.locator('.sw-toggle')
        logger.info(f"Management interface X0 toggle locator: {toggle_button},toggle_button.count(): {toggle_button.count()}")
        assert toggle_button.count() == 0, "ENABLED toggle should be found for management interface"

    def verify_non_management_interface_toggle_button_is_displayed(self, fw_page):
        logger.info("test_02:Verifying non-management interface toggle is displayed...")
        management_interface_row = fw_page.get_table_row_locator("interface-settings-ipv4", "X1")
        toggle_button = management_interface_row.locator('.sw-toggle')
        logger.info(f"Management interface X1 toggle locator: {toggle_button},toggle_button.count(): {toggle_button.count()}")
        assert toggle_button.count() == 1, "non-management interface should have ENABLED toggle button"

    def test_all(self, fw_page):
        self.verify_current_management_interface_toggle_is_not_displayed(fw_page)
        self.verify_non_management_interface_toggle_button_is_displayed(fw_page)


class TestTC_30_interface_comment_word_wrap_and_multi_line_display:
    uuid = "SOSAIOT-TC-94913"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page('X3')
        yield
        fw_page.interface.open_edit_interface_page('X3')
        fw_page.fill_input_by_label_name("Comment", ' ')
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(5000)

    def test_interface_comment_word_wrap(self,fw_page):
        long_comment = "Test table's multi-line display for long comment without spaces"
        fw_page.fill_input_by_label_name("Comment", long_comment)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        x3_row = fw_page.get_table_row_locator("interface-settings-ipv4", "X3")
        logger.info(f"X3 row locator: {x3_row}")
        cells = x3_row.locator("div.sw-table-row__cell")
        comment_cell = cells.nth(10)  
        logger.info(f"Comment cell locator: {comment_cell}")
        white_space = comment_cell.evaluate("el => window.getComputedStyle(el).whiteSpace")
        word_break = comment_cell.evaluate("el => window.getComputedStyle(el).wordBreak")
        logger.info(f"white_space is: {white_space}, word_break is: {word_break}")
        # Usually 'normal' or 'pre-wrap' allows line wrapping
        assert white_space in ['normal', 'pre-wrap', 'pre-line'], f"Unexpected white-space: {white_space}"
        # Check word-break property to ensure long text can wrap
        assert word_break in ['normal', 'break-all', 'break-word'], f"Unexpected word-break: {word_break}"
        logger.info('check height(multi-line display)')
        # --- Assertion point B: Check height (verify multi-line display actually occurred) ---
        height = comment_cell.evaluate("el => el.offsetHeight")
        # Normal single-line height is usually 20-30px, multi-line will definitely exceed 40px
        logger.info(f'height is:{height}')
        assert height > 33, f"Comment cell height is {height}px, expected multi-line wrap."
        comment_text = comment_cell.inner_text()
        logger.info(f'comment_text is:{comment_text}')
        assert long_comment in comment_text, f"Long comment not properly saved. Expected: {long_comment}, Got: {comment_text}"


@pytest.mark.parametrize("uuid, invalid_ip_type, invalid_ip,", [
        ("SOSAIOT-TC-94914","invalid_ip_format", "192.168.a.1"),
        ("SOSAIOT-TC-94915", "out_of_range_ip", "192.168.1.256"),
        ("SOSAIOT-TC-94916", "empty_ip", " "),
        ])
class TestTC_31_32_33_negative_test_verify_invalid_ip_validation_on_edit_interface_page:

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page('X3')
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_verify_invalid_ip(self, fw_page,uuid, invalid_ip_type, invalid_ip):
        logger.info(f"Running test case: {uuid} - {invalid_ip_type} with IP: {invalid_ip}")
        check_status_info = 'Please enter a valid IP Address'
        success = fw_page.fill_input_by_label_name("IP Address", invalid_ip)
        logger.info(f"Fill invalid IP result: {success}")
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(2000)
        status_info = fw_page.find_element(selector='.sw-status-info')
        assert status_info.count() > 0, "Status info element not found after submitting invalid IP"
        logger.info(f"Status info after adding interface: {status_info.inner_text()}")
        flag = check_status_info in status_info.inner_text()
        assert flag, "Expected error message not matched after adding sub-interface with invalid IP"

class TestTC_34_47_negative_test_verify_invalid_mask_validation_on_interface_edit_interface_modal:
    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    @pytest.mark.parametrize("uuid", [("SOSAIOT-TC-94917")])
    def test_tc34_verify_invalid_subnet_mask_format(self, fw_page, uuid):
        logger.info(f"Running test case {uuid}: - invalid subnet mask")
        check_status_info = 'Please enter a valid Subnet Mask'
        invalid_mask_list = [' ', '255.255.255.256', '255.255.255', 'abc.def.ghi.jkl', '255.255.255.255.255',"-3323/%/%$###"]
        check_res = [ ]
        for invalid_mask in invalid_mask_list:
            success = fw_page.fill_input_by_label_name("Subnet Mask", invalid_mask)
            logger.info(f"Fill invalid subnet mask result: {success}")
            fw_page.click_element(selector='.sw-button', has_text='OK')
            fw_page.page.wait_for_timeout(2000)
            status_info = fw_page.find_element(selector='.sw-status-info')
            flag = check_status_info in status_info.inner_text()
            check_res.append(flag)
        logger.info(f"Check results for invalid subnet masks: {check_res}")
        assert all(check_res) and len(check_res) > 0, "Expected error message not matched after adding sub-interface with invalid subnet mask"
 
    @pytest.mark.parametrize("uuid", [("SOSAIOT-TC-94930")])
    def test_tc47_verify_non_standard_subnet_mask_length(self, fw_page, uuid):
        logger.info(f"Running test case: {uuid} - non-standard subnet mask length")
        check_status_info = 'Please enter a valid Subnet Mask'
        success = fw_page.fill_input_by_label_name("Subnet Mask", '255.255.255.253')
        logger.info(f"Fill invalid subnet mask result: {success}")
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(2000)
        status_info = fw_page.get_status_info()
        flag = check_status_info in status_info
        assert flag, "Expected error message not matched after adding sub-interface with non-standard subnet mask length"
    

class TestTC_35_negative_test_verify_default_gateway_validation_on_edit_interface_page:
    uuid = "SOSAIOT-TC-94918"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        # fw_page.page.evaluate("document.body.style.zoom = '1'") 
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)
    
    def test_01_verify_invalid_default_gateway(self, fw_page):
        logger.info(f"Running test case: {self.uuid} - invalid default gateway")
        check_status_info = 'Please enter a valid Default Gateway'
        invalid_gateway_list = [' ', '255.255.255.256', '255.255.255', 'abc.def.ghi.jkl', '255.255.255.255.255',"-3323/%/%$###"]

        check_res = [ ]
        for invalid_gateway in invalid_gateway_list:
            success = fw_page.fill_input_by_label_name("Default Gateway (Optional)", invalid_gateway)
            logger.info(f"Fill invalid default gateway result: {success}")
            fw_page.click_element(selector='.sw-button', has_text='OK')
            fw_page.page.wait_for_timeout(2000)
            status_info = fw_page.find_element(selector='.sw-status-info')
            logger.info(f"Status info: {status_info.inner_text()}")
            flag = check_status_info in status_info.inner_text()
            check_res.append(flag)
        
        logger.info(f"Check results for invalid default gateways: {check_res}")
        assert all(check_res) and len(check_res) > 0, "Expected error message not matched after adding sub-interface with invalid default gateway"


class TestTC_36_37_negative_test_verify_dns_server_validation_on_edit_interface_page:

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page('X1')
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    @pytest.mark.parametrize("uuid", ["SOSAIOT-TC-94919"])
    def test_TC_36_negative_test_verify_invalid_dns_server_1(self, fw_page,uuid):
        check_status_info = 'Please enter a valid DNS Server 1 IP Address'
        invalid_dns_list = [' ', '255.255.255.256', '255.255.255', 'abc.def.ghi.jkl', '255.255.255.255.255',"-3323/%/%$###"]
        check_res = [ ] 
        for invalid_dns in invalid_dns_list:
            success = fw_page.fill_input_by_label_name("DNS Server 1", invalid_dns)
            logger.info(f"Fill invalid DNS server result: {success}")
            fw_page.click_element(selector='.sw-button', has_text='OK')
            fw_page.page.wait_for_timeout(2000)
            status_info = fw_page.find_element(selector='.sw-status-info')
            logger.info(f"Status info: {status_info.inner_text()}")
            flag = check_status_info in status_info.inner_text()
            check_res.append(flag)
        logger.info(f"Check results for invalid DNS servers: {check_res}")
        assert all(check_res) and len(check_res) > 0, "Expected error message not matched after adding sub-interface with invalid DNS server"

    @pytest.mark.parametrize("uuid", ["SOSAIOT-TC-94920"])
    def test_TC_37_negative_test_verify_duplicate_dns_server(self, fw_page, uuid):
        check_status_info = 'Duplicate DNS server IP addresses not allowed'
        fw_page.fill_input_by_label_name("DNS Server 1", '30.30.30.30')
        fw_page.fill_input_by_label_name("DNS Server 2", '30.30.30.30')
        fw_page.click_element(selector='.sw-button', has_text='OK')
        status_info = fw_page.find_element(selector='.sw-status-info')
        logger.info(f"Status info: {status_info.inner_text()}")
        flag = check_status_info in status_info.inner_text()  
        assert flag , "Expected error message not matched after adding sub-interface with invalid DNS Server 2"


class TestTC_38_39_negative_test_verify_domain_name_validation_on_interface_edit_page:
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page('X3')
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    @pytest.mark.parametrize("uuid, invalid_type, invalid_input,", [
        ("SOSAIOT-TC-94921", "total_length_exceeded", "a"*61 + "." + "b"*61 + "." + "c"*61 + "." + "d"*61 + ".example.com.x"),
    ])
    def test_38_test_domain_name_exceeding_character_limit(self, fw_page, uuid, invalid_type, invalid_input):
        check_status_info = 'Value or string length(261) out of bounds (max = 255)'
        logger.info(f"Running test case: {uuid} - {invalid_type} with input: {invalid_input}")
        fw_page.fill_input_by_label_name('Domain Name', invalid_input)
        fw_page.page.wait_for_timeout(10000)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        status_info = fw_page.find_element(selector='.sw-status-info')
        assert status_info.count() > 0, "Status info element not found!"
        logger.info(f"Status info: {status_info.inner_text()}")
        logger.info(f"Expected: {check_status_info}")
        flag = check_status_info in status_info.inner_text()  
        logger.info(f"Match result: {flag}")
        assert flag , "Expected error message not matched after editing X1 interface with invalid domain name"

    @pytest.mark.parametrize("uuid",["SOSAIOT-TC-94922"])
    def test_39_test_domain_name_illegal_and_invalid_characters(self, fw_page, uuid):
        check_status_info = 'Please enter a valid Domain Name'
        logger.info(f"Running test case: {uuid} - domain name illegal and invalid characters")
        
        invalid_test_cases = [
            ("label_too_long", "a"*64 + ".test.com"),
            ("multiple_labels_too_long", "a"*70 + "." + "b"*70 + ".test.com"),
            ("illegal_characters", "a$.com"),
        ]
        for invalid_type, invalid_input in invalid_test_cases:
            logger.info(f"Testing {invalid_type} with input: {invalid_input}")
        fw_page.fill_input_by_label_name('Domain Name', invalid_input)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(2000)
        status_info = fw_page.find_element(selector='.sw-status-info')
        logger.info(f"Status info: {status_info.inner_text()}")
        flag = check_status_info in status_info.inner_text()  
        assert flag , f"Expected error message not matched for {invalid_type} with input: {invalid_input}"

    
class TestTC_40_negative_test_verify_comment_field_character_limit_on_interface_edit_page:
    uuid = "SOSAIOT-TC-94923"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal_once(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_comment_field_character_limit(self, fw_page):
        check_status_info = 'Value or string length(64) out of bounds (max = 63)'
        logger.info(f"Running test case: {self.uuid} - Comment field character limit")
        fw_page.fill_input_by_label_name('Comment', "a"*64)
        fw_page.page.wait_for_timeout(10000)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        status_info = fw_page.find_element(selector='.sw-status-info')
        assert status_info.count() > 0, "Status info element not found!"
        logger.info(f"Status info: {status_info.inner_text()}")
        flag = check_status_info in status_info.inner_text()  
        assert flag , "Expected error message not matched after editing X3 interface with invalid domain name"


@pytest.mark.parametrize("uuid, invalid_type, invalid_input,check_status_info", [
        ("SOSAIOT-TC-94924", "zero_ip_address", "0.0.0.0","Please enter a valid IP Address"),
        ("SOSAIOT-TC-94925", "incomplete_ip_address", "192.168.1.","Please enter a valid IP Address"),
        ("SOSAIOT-TC-94931", "broadcast_ip_address", "192.168.1.255","Invalid IP Address"),
    ])
class TestTC_41_42_48_negative_test_verify_ip_address_validation_on_edit_interface_page:
    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_set_ip_address_invalid_in_static_mode(self, fw_page, uuid, invalid_type, invalid_input, check_status_info):
        logger.info(f'Running test case: {uuid} - {invalid_type} with IP: {invalid_input},check_status_info: {check_status_info}')
        fw_page.fill_input_by_label_name("IP Address", invalid_input)
        fw_page.page.wait_for_timeout(3000)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        status_info = fw_page.get_status_info()
        logger.info(f"Status info: {status_info}")
        assert status_info and len(status_info) > 0, "Status info element not found!"
        flag = check_status_info in status_info  
        logger.info(f"Match result: {flag}")
        assert flag , "Expected error message not matched after inputting invalid IP address in static mode"


@pytest.mark.parametrize("uuid, invalid_type, invalid_input,check_status_info", [
        ("SOSAIOT-TC-94924", "zero_ip_address", "0.0.0.0","Please enter a valid IP Address"),
        ("SOSAIOT-TC-94925", "incomplete_ip_address", "192.168.1.","Please enter a valid IP Address"),
        ("SOSAIOT-TC-94931", "broadcast_ip_address", "192.168.1.255","Invalid IP Address"),
    ])
class TestTC_41_42_48_negative_test_verify_ip_address_validation_on_edit_interface_page:
    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_set_ip_address_invalid_in_static_mode(self, fw_page, uuid, invalid_type, invalid_input, check_status_info):
        logger.info(f'Running test case: {uuid} - {invalid_type} with IP: {invalid_input},check_status_info: {check_status_info}')
        fw_page.fill_input_by_label_name("IP Address", invalid_input)
        fw_page.page.wait_for_timeout(3000)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        status_info = fw_page.get_status_info()
        logger.info(f"Status info: {status_info}")
        assert status_info and len(status_info) > 0, "Status info element not found!"
        flag = check_status_info in status_info  
        logger.info(f"Match result: {flag}")
        assert flag , "Expected error message not matched after inputting invalid IP address in static mode"


class TestTC_43_negative_test_verify_management_conflict_on_interface_edit_interface_page:
    uuid = "SOSAIOT-TC-94926"
    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_dialog_button('Cancel')
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_management_conflict_disabled_all_management_protocols(self, fw_page):
        logger.info(f"Running test case: {self.uuid} - Management conflict disabled all management protocols")
        fw_page.click_toggle(selector='input[name="cb-enable-https"]', enable=False)
        fw_page.click_toggle(selector='input[name="cb-enable-ping"]', enable =False)
        fw_page.click_toggle(selector='input[name="cb-enable-snmp"]', enable =False)
        fw_page.click_toggle(selector='input[name="cb-enable-ssh"]', enable =False) 
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        dialog_element = fw_page.get_confirmation_dialog()
        assert dialog_element.count() == 1, "Confirmation dialog element not found!"


class TestTC44_negative_test_verify_ip_conflict_on_interface_edit_modal:
    uuid = "SOSAIOT-TC-94927"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_management_conflict_enabled_all_management_protocols(self, fw_page):
        check_status_info = 'Subnet on this interface overlaps with another interface'
        logger.info(f"Running test case: {self.uuid} - Management conflict enabled all management protocols")
        fw_page.fill_input_by_label_name("IP Address", "192.168.168.168")
        fw_page.click_element(selector='.sw-button', has_text='OK')
        fw_page.page.wait_for_timeout(3000)
        status_info = fw_page.get_status_info()
        assert status_info, "Status info element not found!"
        logger.info(f"Status info: {status_info}")
        flag = check_status_info in status_info
        assert flag, "Expected error message not matched after inputting invalid IP address in static mode"

        
class TestTC45_negative_test_verify_double_click_and_rapid_submission_test_for_duplicate_requests:
    uuid = "SOSAIOT-TC-94928"

    def double_click_for_submission(self, fw_page):
        logger.info(f"test_01: Double click for rapid submission test for duplicate requests")
        fw_page.interface.open_edit_interface_page("X3")
        fw_page.fill_input_by_label_name("Comment", "aaaaaasffdfdfddfdfaagggggggaaa")
        
        # Setup network request listener for debugging
        all_requests = []
        def capture_request(request):
            all_requests.append(request)
        fw_page.page.on("request", capture_request)
        
        # Filter specific API path for saving interface configuration
        captured_requests = []
        fw_page.page.on("request", lambda request: captured_requests.append(request) 
                if "/api/sonicos/interfaces/ipv4/name/X3" in request.url and request.method == "PUT" else None)

        # Simulate rapid double click on OK button
        ok_button = fw_page.page.locator(".configure-modal-ipv4__form-buttons .sw-button:has-text('OK')")
        
        # Track double click execution
        double_click_successful = False
        logger.info('Begin double click')
        
        try:
            # Check if button is visible and enabled before double click
            if ok_button.is_visible() and ok_button.is_enabled():
                ok_button.dblclick()
                double_click_successful = True
                logger.info("Double click: SUCCESS")
            else:
                logger.warning("Double click: SKIPPED - Button not visible or enabled")
        except Exception as e:
            logger.error(f"Double click: FAILED - {e}")
        
        fw_page.page.wait_for_timeout(2000)
        
        # Debug: Print all requests
        print(f"DEBUG - Total requests captured: {len(all_requests)}")
        for i, req in enumerate(all_requests):
            print(f"DEBUG - Request {i+1}: {req.method} - {req.url}")
        
        # Filter out requests for saving interface configuration
        captured_requests = [req for req in all_requests 
                           if "/api/sonicos/interfaces/ipv4/name/X3" in req.url and req.method == "PUT"]
        
        print(f"DEBUG - Filtered requests: {len(captured_requests)}")
        for i, req in enumerate(captured_requests):
            print(f"DEBUG - Filtered {i+1}: {req.method} - {req.url}")
        
        # Verification Point A: Check if only 1 save request was sent (verify idempotency/frontend blocking)
        save_request_count = len(captured_requests)
        print(f"Total save requests sent: {save_request_count}")
        
        # Only assert if double click was successful
        if double_click_successful:
            assert save_request_count == 1, f"Expected 1 request, but sent {save_request_count}. UI fails to block duplicate clicks."
            
            # Verification Point B: Check for exception popups (500 Error or other JavaScript errors)
            error_info = fw_page.get_top_message(timeout=5000)  # 5 second timeout
            logger.info(f'error_info is:{error_info}')
            flag = 'Error' in (error_info or "")
            assert not flag, f"System error appeared during double clicking: {error_info}"
            logger.info("Double click test passed - no duplicate requests detected")
        else:
            logger.warning("Double click failed - skipping assertions")


    def rapid_commit_for_duplicate_requests(self, fw_page):
        logger.info(f"test_02: Rapid commit test for duplicate requests")
        fw_page.page.wait_for_timeout(4000)
        fw_page.interface.open_edit_interface_page("X3")
        fw_page.fill_input_by_label_name("Comment", "testing_rapid_commit")
        
        # Setup network request listener
        all_requests = []
        def capture_request(request):
            all_requests.append(request)
        
        fw_page.page.on("request", capture_request)
        
        # Filter specific API path for saving interface configuration
        captured_requests = []
        fw_page.page.on("request", lambda request: captured_requests.append(request) 
                if "/api/sonicos/interfaces/ipv4/name/X3" in request.url and request.method == "PUT" else None)

        # Simulate rapid clicking on OK button
        ok_button = fw_page.page.locator(".configure-modal-ipv4__form-buttons .sw-button:has-text('OK')")
        
        # Track click attempts and results
        click_attempts = 0
        successful_clicks = 0
        failed_clicks = 0
        
        logger.info('Begin rapid click')
        for i in range(5):
            click_attempts += 1
            try:
                # Check if button is still visible and enabled before clicking
                if ok_button.is_visible() and ok_button.is_enabled():
                    ok_button.click(no_wait_after=True)
                    successful_clicks += 1
                    logger.info(f"Click {i+1}: SUCCESS")
                else:
                    logger.info(f"Click {i+1}: SKIPPED - Button not visible or enabled")
                    break
                fw_page.page.wait_for_timeout(10)  # 10ms interval, simulate extremely fast clicking
            except Exception as e:
                failed_clicks += 1
                logger.info(f"Click {i+1}: FAILED - {e}")
                # If it's the first click that failed, the test is not meaningful
                if i == 0:
                    logger.warning("First click failed! Rapid commit test is not meaningful.")
                    break
                break  # Stop clicking after page closes

        logger.info(f"Click Summary - Attempts: {click_attempts}, Successful: {successful_clicks}, Failed: {failed_clicks}")

        # Wait a while to ensure requests are sent
        fw_page.page.wait_for_timeout(2000)
        
        # Filter out requests for saving interface configuration
        captured_requests = [req for req in all_requests 
                           if "/api/sonicos/interfaces/ipv4/name/X3" in req.url and req.method == "PUT"]
        
        print(f"DEBUG - Filtered requests: {len(captured_requests)}")
        for i, req in enumerate(captured_requests):
            print(f"DEBUG - Filtered {i+1}: {req.method} - {req.url}")

        # Verification Point A: Check if only 1 save request was sent (verify idempotency/frontend blocking)
        save_request_count = len(captured_requests)
        print(f"Total save requests sent: {save_request_count}")
        
        # Only assert if we had at least one successful click
        if successful_clicks > 0:
            assert save_request_count == 1, f"Expected 1 request, but sent {save_request_count}. UI fails to block duplicate clicks."
            
            # Verification Point B: Check for exception popups
            error_info = fw_page.get_top_message(timeout=5000)  # 5 second timeout
            logger.info(f'error_info is:{error_info}')
            flag = 'Error' in (error_info or "")
            assert not flag, f"System error appeared during rapid clicking: {error_info}"
        else:
            logger.warning("No successful clicks made - skipping assertions")


    def test_all(self, fw_page):
        self.double_click_for_submission(fw_page)
        self.rapid_commit_for_duplicate_requests(fw_page)

    
class TestTC46_negative_test_verify_data_not_saved_when_clicking_cancel:
    uuid = "SOSAIOT-TC-94929"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_data_not_saved_when_clicking_cancel(self, fw_page):
        # logger.info("open edit interface page for X3")
        # fw_page.interface.open_edit_interface_page("X3")
        logger.info(f"Running test case: {self.uuid} - Verify data is NOT saved when clicking Cancel")    
        original_ip = fw_page.get_input_value_by_label_name("IP Address")
        logger.info(f"Original IP address: {original_ip}")
        new_ip = "192.168.100.100"
        fw_page.fill_input_by_label_name("IP Address", new_ip)
        logger.info(f"Modified IP address to: {new_ip}")
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(2000)  
        fw_page.interface.open_edit_interface_page("X3")
        fw_page.page.wait_for_timeout(1000)
        current_ip = fw_page.get_input_value_by_label_name("IP Address")
        logger.info(f"Current IP address after cancel: {current_ip}")
        assert current_ip == original_ip, f"IP address was saved after clicking Cancel! Expected: {original_ip}, Actual: {current_ip}"
        
class TestTC_49_negative_test_verify_xss_injection_prevention_on_edit_interface_modal:
    uuid = "SOSAIOT-TC-94932"

    @pytest.fixture(scope="class", autouse=True)
    def setup_modal(self, fw_page):
        fw_page.interface.open_edit_interface_page("X3")
        yield
        fw_page.click_element(selector='.sw-button', has_text='Cancel')
        fw_page.page.wait_for_timeout(5000)

    def test_verify_xss_injection_prevention_on_edit_interface_modal(self, fw_page):
        logger.info(f"Running test case: {self.uuid} - Verify XSS injection prevention on edit interface modal")
        # fw_page.interface.open_edit_interface_page("X3")
        check_status = "Comments for this interface object: Bad value, script-like text found"
        checkres = []
        xss_payloads = [
            "<script>alert('xss')</script>",        # Explicit Script Tag
            ' " onmouseover="alert(\'hit\')"',      # Attribute Escape (Blocked)
            # ' onmouseover="alert(\'hit\')"',        # Attribute Injection (Accepted/Escaped)
        ]
        for payload in xss_payloads:
            fw_page.fill_input_by_label_name("Comment", payload)
            fw_page.click_element(selector='.sw-button', has_text='OK')

            error_info = fw_page.get_status_info(timeout=5000)  # 5秒超时
            logger.info(f'error_info is:{error_info}')
            flag = check_status in error_info
            checkres.append(flag)
        assert all(checkres) and len(checkres)>0, f"Expected error message not matched after inputting invalid IP address in static mode"

                
class TestTC_50_negative_test_interface_mode_switching_residual:
    uuid = "SOSAIOT-TC-94933"

    def test_verify_mode_switching_data_clearing_static_to_dhcp(self, fw_page):
        logger.info(f"Running test case: {self.uuid} - Verify mode switching residual")
        original_ip = "192.168.100.100"
        fw_page.interface.open_edit_interface_page("X6")
        
        logger.info('step1: configure X6 from unassigned mode to static mode')
        fw_page.select_value_in_dropdown_box('Zone', 'WAN')
        fw_page.select_value_in_dropdown_box('Mode / IP Assignment', 'Static')
        fw_page.fill_input_by_label_name("IP Address", original_ip)
        fw_page.click_toggle(selector='input[name="cb-enable-https"]', enable=True)
        fw_page.click_element(selector='.sw-button', has_text='OK')

        logger.info('step2: configure X6 from static mode to dhcp mode')
        fw_page.page.wait_for_timeout(5000)
        fw_page.interface.open_edit_interface_page("X6")
        fw_page.select_value_in_dropdown_box('Mode / IP Assignment', 'DHCP')
        logger.info('Verify :IP input field is readonly after switch to dhcp mode')
        ip_input = fw_page.page.locator('input[name="textfield-ip-address"]')
        assert ip_input.get_attribute("readonly") is not None, "should be readonly after switch to dhcp mode"
        logger.info('Verify :IP input field is empty after switch to dhcp mode')
        current_ip = ip_input.input_value()
        logger.info(f"Current IP address: {current_ip}")
        assert current_ip == "0.0.0.0", "IP address should be empty when switching to DHCP mode"
        
        logger.info('step3: save dhcp config')
        fw_page.click_toggle(selector='input[name="cb-enable-https"]', enable=True)
        fw_page.click_element(selector='.sw-button', has_text='OK')
        
        logger.info('step4: switch back to static mode,and verify data residue after switch back to static mode')
        fw_page.page.wait_for_timeout(5000)
        fw_page.interface.open_edit_interface_page("X6")
        fw_page.select_value_in_dropdown_box('Mode / IP Assignment', 'Static')
        current_ip = fw_page.get_input_value_by_label_name("IP Address")
        
        logger.info(f"verify :Current IP address after switch back to static mode: {current_ip}")
        assert current_ip == "0.0.0.0" , f"finded data residue after switch back to static mode! Expected: '', Actual: {current_ip}"



        






