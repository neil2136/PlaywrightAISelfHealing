import pytest
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="arp", username='admin', password='password2')


class Test_01_navigate_to_arp_page:
    uuid = 'SOSAIOT-TC-ARP-01'
    def test_01_navigate_to_arp_page(self, fw_page):
        logger.info("Navigate to Network > System > ARP page")
        fw_page.arp.navigate_to_arp()
        res = fw_page.verify_text_exists("ARP", timeout=10000)
        assert res, "ARP page not loaded"


# class Test_02_check_arp_breadcrumb:
#     uuid = 'SOSAIOT-TC-ARP-02'
#     def test_01_check_breadcrumb_text(self, fw_page):
#         breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
#         breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
#         logger.info(f"breadcrumb text is: {breadcrumb_text}")
#         assert "/ Network / System / ARP" in breadcrumb_text, \
#             f"Breadcrumb does not contain expected path, got: {breadcrumb_text}"


# class Test_03_check_arp_tab_switching:
#     uuid = 'SOSAIOT-TC-ARP-03'
#     def switch_to_arp_cache(self, fw_page):
#         res = fw_page.switch_tab("ARP Cache", tab_level="l1")
#         logger.info(f"Switch to ARP Cache tab: {res}")
#         assert res, "Failed to switch to ARP Cache tab"
#         assert fw_page.is_tab_active("ARP Cache", tab_level="l1"), "ARP Cache tab is not active"

#     def switch_to_static_arp(self, fw_page):
#         res = fw_page.switch_tab("Static ARP Entries", tab_level="l1")
#         logger.info(f"Switch to Static ARP Entries tab: {res}")
#         assert res, "Failed to switch to Static ARP Entries tab"
#         assert fw_page.is_tab_active("Static ARP Entries", tab_level="l1"), \
#             "Static ARP Entries tab is not active"

#     def switch_to_arp_settings(self, fw_page):
#         res = fw_page.switch_tab("ARP Settings", tab_level="l1")
#         logger.info(f"Switch to ARP Settings tab: {res}")
#         assert res, "Failed to switch to ARP Settings tab"
#         assert fw_page.is_tab_active("ARP Settings", tab_level="l1"), \
#             "ARP Settings tab is not active"

#     def test_all(self, fw_page):
#         self.switch_to_arp_cache(fw_page)
#         self.switch_to_static_arp(fw_page)
#         self.switch_to_arp_settings(fw_page)


# class Test_04_check_arp_cache_table_headers:
#     uuid = 'SOSAIOT-TC-ARP-04'
#     def test_01_check_arp_cache_headers(self, fw_page):
#         fw_page.switch_tab("ARP Cache", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ['#', 'IP ADDRESS', 'TYPE', 'MAC ADDRESS', 'VENDOR', 'INTERFACE', 'TIMEOUT']
#         actual_headers = fw_page.get_table_header(fw_page.arp.ARP_CACHE_CONTAINER)
#         logger.info(f"ARP Cache table headers: {actual_headers}")
#         assert actual_headers == expected_headers, \
#             f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"


# class Test_05_check_static_arp_table_headers:
#     uuid = 'SOSAIOT-TC-ARP-05'
#     def test_01_check_static_arp_headers_and_empty_state(self, fw_page):
#         fw_page.switch_tab("Static ARP Entries", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         expected_headers = ['#', 'IP ADDRESS', 'MAC ADDRESS', 'VENDOR', 'INTERFACE', 'PUBLISHED', 'BIND MAC']
#         actual_headers = fw_page.get_table_header(fw_page.arp.STATIC_ARP_CONTAINER)
#         logger.info(f"Static ARP Entries table headers: {actual_headers}")
#         if actual_headers:
#             assert actual_headers == expected_headers, \
#                 f"Table headers mismatch: expected {expected_headers}, got {actual_headers}"
#         else:
#             has_no_data = fw_page.verify_text_exists("No Data", timeout=3000)
#             logger.info(f"Table appears empty, 'No Data' visible: {has_no_data}")


# class Test_06_check_arp_cache_table_count:
#     uuid = 'SOSAIOT-TC-ARP-06'
#     def test_01_check_table_total_count(self, fw_page):
#         fw_page.switch_tab("ARP Cache", tab_level="l1")
#         fw_page.page.wait_for_timeout(5000)
#         display_total_count = fw_page.extract_table_footer_total_count()
#         logger.info(f"Extracted table total count: {display_total_count}")
#         actual_total_count = fw_page.get_table_row_count_by_container(fw_page.arp.ARP_CACHE_CONTAINER)
#         logger.info(f"Actual table row count: {actual_total_count}")
#         assert display_total_count == actual_total_count, \
#             f"Footer total ({display_total_count}) does not match actual rows ({actual_total_count})"


class Test_15_verify_add_button_opens_dialog:
    uuid = 'SOSAIOT-TC-ARP-0015'

    def test_01_add_button_opens_and_closes_dialog(self, fw_page):
        """Verify Add button opens the Add Static Entry dialog, then close it."""
        logger.info("Click Add button on Static ARP Entries tab")
        fw_page.switch_tab("Static ARP Entries", tab_level="l1")
        fw_page.page.wait_for_timeout(2000)

        fw_page.click_icon_button("Add")
        fw_page.page.wait_for_timeout(2000)

        # Verify dialog opened
        assert fw_page.verify_text_exists("Add Static Entry", timeout=5000), \
            "Add Static Entry dialog did not open"
        logger.info("✅ Add Static Entry dialog opened successfully")

        # Close dialog — uses @self_heal: if .sw-modal class name changes, auto-heals
        fw_page.arp.close_add_dialog()
        logger.info("✅ Dialog closed")

