import pytest
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="mac_ip_anti_spoof", username='admin', password='S0nic@uto')


# ═══════════════════════════════════════════════════════════════
# Pattern 1: Page Navigation (0001)
# ═══════════════════════════════════════════════════════════════
class Test_01_navigate_to_mac_ip_anti_spoof_page:
    uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0001'
    def test_01_navigate_to_mac_ip_anti_spoof_page(self, fw_page):
        logger.info("Navigate to Network > System > MAC IP Anti-Spoof page")
        fw_page.mac_ip_anti_spoof.navigate_to_mac_ip_anti_spoof()
        res = fw_page.verify_text_exists("MAC IP Anti-Spoof", timeout=30000)
        assert res, "MAC IP Anti-Spoof page not loaded"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 2: Breadcrumb (0002)
# # ═══════════════════════════════════════════════════════════════
# class Test_02_check_mac_ip_anti_spoof_breadcrumb:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0002'
#     def test_01_check_breadcrumb_text(self, fw_page):
#         breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
#         breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
#         logger.info(f"breadcrumb text is: {breadcrumb_text}")
#         assert "Network / System / MAC IP Anti-Spoof" in breadcrumb_text, \
#             f"Breadcrumb does not contain expected path, got: {breadcrumb_text}"


# ═══════════════════════════════════════════════════════════════
# Pattern 3: L1 Tab Switching (0003)
# ═══════════════════════════════════════════════════════════════
class Test_03_check_mac_ip_anti_spoof_tab_switching:
    uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0003'

    def check_active_tab(self, fw_page):
        time.sleep(10)  # Wait for tabs to load
        tab_text = fw_page.get_active_tab("l1") 
        logger.info(f"Default active L1 tab: {tab_text}")
        assert tab_text == "MAC IPv4 Anti Spoof Settings", \
            "Default active tab is not 'MAC IPv4 Anti Spoof Settings'"

    def switch_to_mac_ipv4_anti_spoof_settings(self, fw_page):
        res = fw_page.switch_tab("MAC IPv4 Anti Spoof Settings", tab_level="l1")
        logger.info(f"Switch to MAC IPv4 Anti Spoof Settings tab: {res}")
        assert res, "Failed to switch to MAC IPv4 Anti Spoof Settings tab"
        assert fw_page.is_tab_active("MAC IPv4 Anti Spoof Settings", tab_level="l1"), \
            "MAC IPv4 Anti Spoof Settings tab is not active"

    def switch_to_anti_spoof_cache(self, fw_page):
        res = fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
        logger.info(f"Switch to Anti Spoof Cache tab: {res}")
        assert res, "Failed to switch to Anti Spoof Cache tab"
        assert fw_page.is_tab_active("Anti Spoof Cache", tab_level="l1"), \
            "Anti Spoof Cache tab is not active"

    def switch_to_spoof_detected_list(self, fw_page):
        res = fw_page.switch_tab("Spoof Detected List", tab_level="l1")
        logger.info(f"Switch to Spoof Detected List tab: {res}")
        assert res, "Failed to switch to Spoof Detected List tab"
        assert fw_page.is_tab_active("Spoof Detected List", tab_level="l1"), \
            "Spoof Detected List tab is not active"

    def test_all(self, fw_page):
        self.check_active_tab(fw_page)
        # self.switch_to_mac_ipv4_anti_spoof_settings(fw_page)
        # self.switch_to_anti_spoof_cache(fw_page)
        # self.switch_to_spoof_detected_list(fw_page)


# # ═══════════════════════════════════════════════════════════════
# # Pattern 4: L2 Tab Switching (0004)
# # ═══════════════════════════════════════════════════════════════
# class Test_04_check_mac_ip_anti_spoof_l2_tab_switching:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0004'

#     def check_active_tab(self, fw_page):
#         tab_text = fw_page.get_active_tab("l2") or ''
#         logger.info(f"Default active L2 tab: {tab_text}")
#         assert tab_text == "IPv4", \
#             "Default active L2 tab is not 'IPv4'"

#     def switch_to_ipv4(self, fw_page):
#         res = fw_page.switch_tab("IPv4", tab_level="l2")
#         logger.info(f"Switch to IPv4: {res}")
#         assert res or fw_page.is_tab_active("IPv4", tab_level="l2"), \
#             "IPv4 tab is not active"
#         fw_page.page.wait_for_timeout(3000)

#     def switch_to_ipv6(self, fw_page):
#         res = fw_page.switch_tab("IPv6", tab_level="l2")
#         logger.info(f"Switch to IPv6: {res}")
#         assert res or fw_page.is_tab_active("IPv6", tab_level="l2"), \
#             "IPv6 tab is not active"
#         fw_page.page.wait_for_timeout(3000)

#     def test_all(self, fw_page):
#         self.check_active_tab(fw_page)
#         self.switch_to_ipv4(fw_page)
#         self.switch_to_ipv6(fw_page)


# # ═══════════════════════════════════════════════════════════════
# # Pattern 5: Table Headers — Settings IPv4 (0005)
# # ═══════════════════════════════════════════════════════════════
# class Test_05_check_mac_ipv4_settings_ipv4_table_headers:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0005'
#     def test_01_check_settings_ipv4_headers(self, fw_page):
#         fw_page.switch_tab("MAC IPv4 Anti Spoof Settings", tab_level="l1")
#         fw_page.switch_tab("IPv4", tab_level="l2")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ["INTERFACE", "ENFORCED", "ENABLE", "ARP LOCK", "ARP WATCH",
#                             "STATIC ARP", "DHCP SERVER", "DHCP RELAY", "SPOOF DETECTION", "ALLOW MGMT."]
#         actual_headers = fw_page.get_table_header(
#             fw_page.mac_ip_anti_spoof.CONTAINER_SETTINGS
#         )
#         logger.info(f"Settings IPv4 table headers: {actual_headers}")
#         assert actual_headers == expected_headers, \
#             f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 5: Table Headers — Settings IPv6 (0006)
# # ═══════════════════════════════════════════════════════════════
# class Test_06_check_mac_ipv4_settings_ipv6_table_headers:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0006'
#     def test_01_check_settings_ipv6_headers(self, fw_page):
#         fw_page.switch_tab("MAC IPv4 Anti Spoof Settings", tab_level="l1")
#         fw_page.switch_tab("IPv6", tab_level="l2")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ["INTERFACE", "ENFORCED", "ENABLE", "NDP LOCK",
#                             "STATIC NDP", "SPOOF DETECTION", "ALLOW MGMT."]
#         actual_headers = fw_page.get_table_header(
#             fw_page.mac_ip_anti_spoof.CONTAINER_SETTINGS
#         )
#         logger.info(f"Settings IPv6 table headers: {actual_headers}")
#         assert actual_headers == expected_headers, \
#             f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 5: Table Headers — Anti Spoof Cache (0007)
# # ═══════════════════════════════════════════════════════════════
# class Test_07_check_anti_spoof_cache_table_headers:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0007'
#     def test_01_check_cache_headers(self, fw_page):
#         fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ["IP ADDRESS", "TYPE", "INTERFACE", "MAC ADDRESS",
#                             "VENDOR", "HOST NAME", "ROUTER", "BLACKLISTED"]
#         actual_headers = fw_page.get_table_header(
#             fw_page.mac_ip_anti_spoof.CONTAINER_CACHE
#         )
#         logger.info(f"Anti Spoof Cache table headers: {actual_headers}")
#         if actual_headers:
#             assert actual_headers == expected_headers, \
#                 f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"
#         else:
#             has_no_data = fw_page.verify_text_exists("No Data", timeout=3000)
#             logger.info(f"Table appears empty, 'No Data' visible: {has_no_data}")


# # ═══════════════════════════════════════════════════════════════
# # Pattern 5: Table Headers — Spoof Detected List (0008)
# # ═══════════════════════════════════════════════════════════════
# class Test_08_check_spoof_detected_list_table_headers:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0008'
#     def test_01_check_spoof_headers(self, fw_page):
#         fw_page.switch_tab("Spoof Detected List", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ["IP ADDRESS", "INTERFACE", "MAC ADDRESS",
#                             "VENDOR", "HOST NAME", "PKTS."]
#         actual_headers = fw_page.get_table_header(
#             fw_page.mac_ip_anti_spoof.CONTAINER_SPOOF
#         )
#         logger.info(f"Spoof Detected List table headers: {actual_headers}")
#         if actual_headers:
#             assert actual_headers == expected_headers, \
#                 f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"
#         else:
#             has_no_data = fw_page.verify_text_exists("No Data", timeout=3000)
#             logger.info(f"Table appears empty, 'No Data' visible: {has_no_data}")


# # ═══════════════════════════════════════════════════════════════
# # Pattern 11: Empty State — Anti Spoof Cache (0009)
# # ═══════════════════════════════════════════════════════════════
# class Test_09_check_anti_spoof_cache_empty_state:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0009'
#     def test_01_check_cache_empty(self, fw_page):
#         fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         has_no_data = fw_page.verify_text_exists("No Data", timeout=3000)
#         logger.info(f"Anti Spoof Cache empty, 'No Data' visible: {has_no_data}")
#         assert has_no_data, "Expected 'No Data' message not found in Anti Spoof Cache table"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 11: Empty State — Spoof Detected List (0010)
# # ═══════════════════════════════════════════════════════════════
# class Test_10_check_spoof_detected_list_empty_state:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0010'
#     def test_01_check_spoof_empty(self, fw_page):
#         fw_page.switch_tab("Spoof Detected List", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         has_no_data = fw_page.verify_text_exists("No Data", timeout=3000)
#         logger.info(f"Spoof Detected List empty, 'No Data' visible: {has_no_data}")
#         assert has_no_data, "Expected 'No Data' message not found in Spoof Detected List table"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 6: Table Total Count (0011)
# # ═══════════════════════════════════════════════════════════════
# class Test_11_check_mac_ipv4_settings_table_count:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0011'
#     def test_01_check_table_total_count(self, fw_page):
#         fw_page.switch_tab("MAC IPv4 Anti Spoof Settings", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         display_total_count = fw_page.extract_table_footer_total_count()
#         logger.info(f"Extracted table total count: {display_total_count}")
#         actual_total_count = fw_page.get_table_row_count_by_container(
#             fw_page.mac_ip_anti_spoof.CONTAINER_SETTINGS
#         )
#         logger.info(f"Actual table row count: {actual_total_count}")
#         assert display_total_count == actual_total_count, \
#             f"Footer total ({display_total_count}) does not match actual rows ({actual_total_count})"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 9: Button Click — Refresh (0012)
# # ═══════════════════════════════════════════════════════════════
# class Test_12_check_mac_ipv4_settings_refresh_button:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0012'
#     def test_01_check_refresh_button(self, fw_page):
#         fw_page.switch_tab("MAC IPv4 Anti Spoof Settings", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         logger.info("Clicking Refresh button")
#         fw_page.click_icon_button("Refresh")
#         fw_page.page.wait_for_timeout(5000)
#         logger.info("Refresh action completed — verifying page still shows expected content")
#         assert fw_page.verify_text_exists("MAC IPv4 Anti Spoof Settings", timeout=5000), \
#             "Page content missing after refresh"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 9: Button Click — Statistics (0013)
# # ═══════════════════════════════════════════════════════════════
# class Test_13_check_statistics_button:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0013'
#     def test_01_check_statistics_button(self, fw_page):
#         fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
#         fw_page.switch_tab("IPv6", tab_level="l2")
#         fw_page.page.wait_for_timeout(5000)
#         fw_page.click_icon_button("Statistics")
#         fw_page.page.wait_for_timeout(3000)
#         res = fw_page.verify_text_exists("Statistics", timeout=5000)
#         assert res, "Statistics popover did not open"
#         for field in ["Entries", "Lookups", "Passed", "Dropped", "Success", "Passed(To Us)"]:
#             assert fw_page.verify_text_exists(field, timeout=2000), \
#                 f"Statistics field '{field}' not found in popover"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 9: Button Click — Add (0014)
# # ═══════════════════════════════════════════════════════════════
# class Test_14_check_add_button:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0014'
#     def test_01_check_add_button(self, fw_page):
#         fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
#         fw_page.switch_tab("IPv6", tab_level="l2")
#         fw_page.page.wait_for_timeout(5000)
#         fw_page.click_icon_button("Add")
#         fw_page.page.wait_for_timeout(3000)
#         res = fw_page.verify_text_exists("Add Anti Spoof Cache", timeout=5000)
#         assert res, "Add Anti Spoof Cache dialog did not open"


# # ═══════════════════════════════════════════════════════════════
# # Pattern 10: Delete Disabled State (0015)
# # ═══════════════════════════════════════════════════════════════
# class Test_15_check_delete_button_disabled_state:
#     uuid = 'SOSAIOT-TC-MAC_IP_ANTI_SPOOF-0015'
#     def test_01_check_delete_disabled(self, fw_page):
#         fw_page.switch_tab("Anti Spoof Cache", tab_level="l1")
#         fw_page.switch_tab("IPv6", tab_level="l2")
#         fw_page.page.wait_for_timeout(5000)
#         delete_btn = fw_page.page.locator(".sw-icon-button__label-cont:text-is('Delete')")
#         if delete_btn.count() > 0:
#             parent_btn = delete_btn.first.locator("..")
#             is_enabled = parent_btn.first.is_enabled()
#             logger.info(f"Delete button enabled state (no selection): {is_enabled}")
#             assert not is_enabled, "Delete button should be disabled when no row is selected"
#         else:
#             logger.info("Delete button not found — skipping disabled check")
