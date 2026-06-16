import pytest
import inspect
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="interfaces", username='admin', password='S0nic@uto')
# pytestmark = pytest.mark.auto_login


class Test_01_navigate_to_network_interface_page:
    uuid = 'SOSAIOT-TC-94884'
    def test_01_navigate_to_network_interface_page(self, fw_page):
        # fw_page.page.click(selector ='.sw-top-nav:has-text("Network")')
        logger.info(f"go to network url")
        fw_page.navigate_to_url(Settings.BASE_URL + '/m/mgmt/network/interfaces')
        # verifications = ['Add Interface', ]
        # res = fw_page.is_element_visible_by_selector("div.sw-form-row__label:text-is('Add Interface')", timeout=100000)
        res = fw_page.verify_text_exists("Add Interface", timeout=100000)
        assert res, "Interfaces page not loaded"

class Test_02_check_interface_page_navigation:
    uuid = 'SOSAIOT-TC-94885'
    def test_01_check_breadcrumb_text(self, fw_page):
        breadcrumb_text = fw_page.page.locator('.sw-breadcrumb').inner_text()
        breadcrumb_text = breadcrumb_text.replace('\n', ' ').strip()
        logger.info(f"breadcrumb text is: {breadcrumb_text}")
        assert "Network / System / Interfaces" in breadcrumb_text, "Breadcrumb text does not contain expected path"


class Test_03_check_l1_tab:
    uuid = 'SOSAIOT-TC-94886'
    def check_active_tab(self, fw_page):
        tab_text = ''
        active_tab = fw_page.page.locator('.sw-tab--l1.sw-tab--active')
        if active_tab.count() > 0:
            tab_text = active_tab.inner_text().strip()
            logger.info(f"active tab is: {tab_text}")
        assert tab_text == "Interface Settings", "Default active tab is not 'Interface Settings'"

    def switch_tab(self, fw_page):
        switch_tab_name = "Traffic Statistics"
        clear_stats_btn = None
        res = fw_page.click_tab(switch_tab_name, tab_level="l1")
        logger.info(f"click_tab result: {res}")
        if res:
            logger.info(f"Successfully switched to tab: {switch_tab_name}")
            clear_stats_btn = fw_page.find_element(text='Clear Statistics')
            logger.info(f"Clear Statistics button element: {clear_stats_btn}")
        assert clear_stats_btn is not None, "Clear Statistics button not found after switching tabs"
    
    def switch_back_tab(self, fw_page):
        switch_tab_name = "Interface Settings"
        add_interface_btn = None
        res = fw_page.click_tab(switch_tab_name, tab_level="l1")
        if res:
            logger.info(f"Successfully switched to tab: {switch_tab_name}")
            add_interface_btn = fw_page.find_element(text='Add Interface')
        assert add_interface_btn is not None, "Add Interface button not found after switching back to Interface Settings tab"

    def test_all(self, fw_page):
        self.check_active_tab(fw_page)
        self.switch_tab(fw_page)
        self.switch_back_tab(fw_page)


class Test_04_check_l2_tab:
    uuid ="SOSAIOT-TC-94887"
    def check_active_tab(self, fw_page):
        tab_text = ''
        active_tab = fw_page.page.locator('.sw-tab--l2.sw-tab--active')
        if active_tab.count() > 0:
            tab_text = active_tab.inner_text().strip()
            logger.info(f"active tab is: {tab_text}")
        assert tab_text == "IPv4", "Default active tab is not 'IPv4'"

    def switch_tab(self, fw_page):
        switch_tab_name = "IPv6"
        link_count = 0
        res = fw_page.click_tab(switch_tab_name, tab_level="l2")
        logger.info(f"click_tab result: {res}")
        if res:
            logger.info(f"Successfully switched to tab: {switch_tab_name}")
            fw_page.page.wait_for_timeout(10000)
            link_btn = fw_page.page.locator('text=fe80:')
            # link_btn = fw_page.page.locator(':has-text("fe80:")')
            logger.info(f"fe80 link element: {link_btn}")

            if link_btn:
                link_count = link_btn.count()
                logger.info(f"fe80 link element count: {link_count}")
        assert link_count > 0, "fe80 link not found after switching tabs"
    
    def switch_back_tab(self, fw_page):
        switch_tab_name = "IPv4"
        add_interface_btn = None
        res = fw_page.click_tab(switch_tab_name, tab_level="l2")
        if res:
            logger.info(f"Successfully switched to tab: {switch_tab_name}")
            add_interface_btn = fw_page.find_element(text='Add Interface')
        assert add_interface_btn is not None, "Add Interface button not found after switching back to Interface Settings tab"

    def test_all(self, fw_page):
        self.check_active_tab(fw_page)
        self.switch_tab(fw_page)
        self.switch_back_tab(fw_page)


class Test_05_table_total_display_number_is_correct:
    uuid = "SOSAIOT-TC-94891"
    def test_01_check_table_total_count(self, fw_page):
        display_total_count = fw_page.extract_table_footer_total_count()
        logger.info(f"Extracted table total count: {display_total_count}")
        actual_total_count = fw_page.get_table_row_count_by_container("interface-settings-ipv4")
        logger.info(f"Actual table row count: {actual_total_count}")
        assert display_total_count == actual_total_count, "footer total count does not match actual row count"


class Test_06_check_ipv4_page_table_value:
    uuid = "SOSAIOT-TC-94888"
    def check_default_table_row_value(self, fw_page):
        row_list = fw_page.get_table_row_text("interface-settings-ipv4","X0")
        logger.info(f"X0 row text: {row_list}")
        checklist = ['X0', 'LAN', '192.168.168.168', '255.255.255.0', 'Static IP']
        resall = [item in str(row_list) for item in checklist]
        logger.info(f"resall is: {resall}")
        assert all(resall) == True, "ipv4 page value does not match expected value"

    def check_table_interface_status(self, fw_page):
        status = fw_page.interface.get_interface_status('X1') 
        logger.info(f"X1 interface status: {status}")
        assert status == "enabled", "X1 interface status should be enabled"
    
    def test_all(self, fw_page):
        self.check_default_table_row_value(fw_page)
        self.check_table_interface_status(fw_page)

class Test_07_check_ipv6_page_table_value:
    uuid = "SOSAIOT-TC-94889"
    def test_01_check_ipv6_table_interface_value(self, fw_page):
        fw_page.click_tab("IPv6", tab_level="l2")
        fw_page.page.wait_for_timeout(5000)
        row_list = fw_page.get_table_row_text("interface-settings-ipv6 ","X0")
        logger.info(f"X0 row text: {row_list}")
        checklist = ["Static","fe80::","Automatic"]
        resall = [item in str(row_list) for item in checklist]
        logger.info(f"resall: {resall}")
        assert all(resall) == True, "check ipv6 page value failed"

class Test_08_check_interface_table_header:
    uuid = "SOSAIOT-TC-94903"
    def test_01_check_table_header(self, fw_page):
        fw_page.click_tab("IPv4", tab_level="l2")
        fw_page.page.wait_for_timeout(5000)
        checkheaderlist = ['NAME', 'ZONE', 'GROUP', 'IP ADDRESS', 'SUBNET MASK', 'IP ASSIGNMENT', 'STATUS', 'ENABLED', 'COMMENT']
        get_table_header = fw_page.get_table_header("interface-settings-ipv4")
        logger.info(f"table header is: {get_table_header}")
        assert checkheaderlist == get_table_header, "table header does not match expected header list"


class Test_09_diag_window_after_click_add_interface_button:


    @pytest.mark.parametrize("option_text,uuid", [("Virtual Interface", "SOSAIOT-TC-94898"),
                                           ("VPN Tunnel Interface", "SOSAIOT-TC-94899"),
                                           ("4to6 Tunnel Interface", "SOSAIOT-TC-94900"),
                                           ]) 
    def test_01_check_diag_window_after_click_add_interface_button(self, fw_page, option_text, uuid):
        logger.info(f"click Add Interface dropdown option: {option_text}")
        fw_page.select_value_from_button_dropdown("Add Interface", option_text)
        fw_page.page.wait_for_timeout(3000)
        res = fw_page.verify_text_exists(f'Add {option_text}', timeout=10000)
        logger.info(f"Add Interface dropdown options: {res}")
        fw_page.click_close_icon_by_window_title(f"Add {option_text}")
        assert res, f"Add {option_text} page not loaded"





    


        # # "//div[contains(@class,'ssid-group-table__ssidGroups-cont')]/div[contins(@class,'sw-table')]//div[contains(@class, 'sw-table-body__cont__table') and not(ancestor::div[contains(@class, 'sw-table-expand-row')])]/div[contains(@class, 'sw-table-row')]"
        # fw_page.page.wait_for_timeout(5000)
        # row_elements = fw_page.page.locater("xpath=//div[contains(@class,'interface-settings-ipv4')]/div[contains(@class,'sw-table')]//div[contains(@class, 'sw-table-body__cont__table') and not(ancestor::div[contains(@class, 'sw-table-expand-row')])]/div[contains(@class, 'sw-table-row')]").click()
        # if row_elements:
        #     logger.info(f"Successfully located table rows")
        #     row_count = row_elements.count()
        #     logger.info(f"Table rows count: {row_count}")
        # else:
        #     logger.error("Failed to locate table rows")
        #     row_count = 0
        # assert row_count == 12, "Table rows count should be 12"



        # count = fw_page.get_table_count_by_class("interface-settings-ipv4")
        # assert count == 12, "Table rows count should be 12"

        # row_list = fw_page.get_table_row("interface-settings-ipv4","X1")
        # logger.info(f"X0 row text: {row_list}")

        # table_header = fw_page.get_table_header()
        # assert count == 12, "Table rows count should be 12"






# //div[@class='ssid-group-table__ssidGroups-cont']//div[contains(@class,'sw-table-body__cont__table')]/div[contains(@class,'sw-table-row') and .//div[contains(@class,'sw-table-row__cell__trigger__cont')]]


# //div[@class='interface-settings-ipv4 sw-flexbox sw-flexbox--column']//div[contains(@class,'sw-table-body__cont__table')]/div[contains(@class,'sw-table-row') and not(.//div[contains(@class,'sw-table-row__cell__trigger__cont')]]




    # def test_01_check_active_tab(self, fw_page):
    #     tab_text = ''
    #     active_tab = fw_page.page.locator('.sw-tab--l2.sw-tab--active')
    #     if active_tab.count() > 0:
    #         tab_text = active_tab.inner_text().strip()
    #         logger.info(f"active tab is: {tab_text}")
    #     assert tab_text == "IPv4", "Default active tab is not 'IPv4'"


    # def test_03_switch_back_tab(self, fw_page):
    #     switch_tab_name = "IPv4"
    #     add_interface_btn = None
    #     res = fw_page.click_tab(switch_tab_name, tab_level="l1")
    #     if res:
    #         logger.info(f"Successfully switched to tab: {switch_tab_name}")
    #         add_interface_btn = fw_page.find_element(text='X0:V11')
    #     assert add_interface_btn is not None, "Add Interface button not found after switching back to Interface Settings tab"


    
                


        




# class Test_02_check_b:
#     """测试Add Interface按钮下拉选项"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_once(self, fw_page):
#         """类级别：只执行一次"""
#         yield

#     @pytest.mark.parametrize("option_text,uuid", [("Virtual Interface", "12066"),
#                                            ("VPN Tunnel Interface", "12067"),
#                                            ("4to6 Tunnel Interface", "12068"),
#                                            ("WLAN Tunnel Interface", "12069"),
#                                            ]) 
#     def test_01_check_option(self, fw_page, option_text, uuid):
#         # 检查下拉选项
#         logger.info(f"check Add Interface dropdown option: {option_text}")
#         res = fw_page.get_options_from_button_dropdown("Add Interface")
#         logger.info(f"Add Interface dropdown options: {res}")
#         assert option_text in res, f"{option_text} option not found in Add Interface dropdown"

    


# class Test_01_check_add_vlan_interface_window_generl_tab_labels:
    
#     """测试Add Virtual Interface弹窗的所有标签"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.page.wait_for_timeout(2000)
#         fw_page.select_value_from_button_dropdown("Add Interface", "Virtual Interface")
#         fw_page.page.wait_for_timeout(2000)
#         yield
#         # fw_page.click_close_icon_by_window_title("Add Virtual Interface")
    
#     @pytest.mark.parametrize("label_text,uuid",[("Zone", "12001"),
#                                            ("VLAN Tag", "12002"),
#                                            ("Parent Interface", "12003"),
#                                            ("Mode / IP Assignment", "12004")
#                                            ])
#     def test_01_check_label(self, fw_page, label_text, uuid):
        
#         # 检查标签
#         logger.info(f"check label: {label_text}")
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{label_text}')")
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
        
#         assert count == 1, f"{label_text} label not found"


# class Test_02_check_add_vlan_interface_window_advanced_tab:
#     """测试Add Virtual Interface弹窗的所有标签"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.click(selector='span.sw-tab__inner__piece:text-is("Advanced")')
#         yield
#         fw_page.click_close_icon_by_window_title("Add Virtual Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Link Speed", "12005"),
#                                            ("Enable flow reporting", "12006"),
#                                            ("Enable Multicast Support", "12007"),
#                                            ("Exclude from Route Advertisement (NSM, OSPF, BGP, RIP)", "12008"),
#                                             ("Enable Default 802.1p CoS", "12009"),
#                                             ("Enable Asymmetric Route Support", "12010"),
#                                             ("Interface MTU", "12011")
#                                             # 第一个需要打开弹窗
#                                            ]) # 第一个需要打开弹窗
#     def test_01_check_label(self, fw_page, label_text, uuid):
        
#         # 检查标签
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{label_text}')")
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert count == 1, f"{label_text} label not found"


#     @pytest.mark.parametrize("button_name,button_locator,uuid",
#                              [("Cancel","button.configure-modal-ipv4__button-cancel", "12012"),
#                               ("OK", "button.configure-modal-ipv4__button-ok", "12013")])
#     def test_02_check_label(self, fw_page, button_name, button_locator, uuid):
#         logger.info(f'begin to check button {button_name} exist')
#         res = fw_page.page.locator(button_locator)
#         count = res.count()
#         logger.info(f'{button_name} button element count: {count}')
#         assert res, f"{button_name} button not found"

    
# class Test_03_check_add_vpn_tunnel_interface_window_generl_tab_labels:
#     """测试Add Virtual Interface弹窗的所有标签"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.page.wait_for_timeout(2000)
#         fw_page.select_value_from_button_dropdown("Add Interface", "VPN Tunnel Interface")
#         fw_page.page.wait_for_timeout(2000)
#         yield
#         # fw_page.click_close_icon_by_window_title("Add Virtual Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Zone", "12014"),
#                                            ("VPN Policy", "12015"),
#                                            ("Name", "12016"),
#                                            ("Mode / IP Assignment", "12017"),
#                                            ("IP Address", "12018"),
#                                            ("Subnet Mask", "12019"),
#                                            ("Interface MTU", "12020"),
#                                            ("Comment", "12021"),
#                                            ("Domain Name", "12022"),
#                                            ]) 
#     def test_01_check_label(self, fw_page, label_text, uuid):
#         # 检查标签
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{label_text}')")
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
        
#         assert count == 1, f"{label_text} label not found"


# class Test_04_check_add_vpn_tunnel_interface_window_advanced_tab:
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.click(selector='span.sw-tab__inner__piece:text-is("Advanced")')
#         yield
#         fw_page.click_close_icon_by_window_title("Add VPN Tunnel Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Enable flow reporting", "12023"),
#                                            ("Enable Multicast Support", "12024"),
#                                            ("Enable Asymmetric Route Support", "12025"),
#                                            ("Enable Fragmented Packet Handling", "12026"),
#                                             ("Ignore Don\'t Fragment (DF) Bit", "12027"),
#                                             ("Do not send ICMP Fragmentation Needed for outbound packets over the Interface MTU", "12028"),
#                                            ]) 
#     def test_01_check_label(self, fw_page, label_text, uuid):
        
#         # 检查标签
#         res = fw_page.page.locator(f'div.sw-form-row__label:text-is("{label_text}")')
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert count == 1, f"{label_text} label not found"


#     @pytest.mark.parametrize("button_name,button_locator,uuid",
#                              [("Cancel","button.configure-modal-ipv4__button-cancel", "12029"),
#                               ("OK", "button.configure-modal-ipv4__button-ok", "12030")])
#     def test_02_check_label(self, fw_page, button_name, button_locator, uuid):
#         logger.info(f'begin to check button {button_name} exist')
#         res = fw_page.page.locator(button_locator)
#         count = res.count()
#         logger.info(f'{button_name} button element count: {count}')
#         assert res, f"{button_name} button not found"



# class Test_05_check_add_4to6_tunnel_interface_window_generl_tab_labels:
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.page.wait_for_timeout(2000)
#         fw_page.select_value_from_button_dropdown("Add Interface", "4to6 Tunnel Interface")
#         fw_page.page.wait_for_timeout(2000)
#         yield
#         # fw_page.click_close_icon_by_window_title("Add Virtual Interface")
    
#     @pytest.mark.parametrize("label_text,uuid", [("Zone", "12031"),
#                                            ("Tunnel Type", "12032"),
#                                            ("Name", "12033"),
#                                            ("Bound to", "12034"),
#                                            ("Local IPv6 Address", "12035"),
#                                            ("AFTR IPv6 Address", "12036"),
#                                            ("Comment", "12037"),
#                                            ]) 
#     def test_01_check_label(self, fw_page, label_text, uuid):
#         # 检查标签
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{label_text}')")
#         # res = fw_page.page.wait_for_timeout(2000)
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert res, f"{label_text} label not found"


#     @pytest.mark.parametrize("radio_text,uuid", [("Use Primary IPv6 Address", "12038"),
#                                            ("Specify Local IPv6 Address", "12039"),
#                                            ("Configure Static Address", "12040"),
#                                            ("Configure FQDN", "12041"),
#                                            ("Get via DHCP", "12042"),                    
#                                            ]) 
#     def test_02_check_radio_text(self, fw_page, radio_text, uuid):
#         # 检查标签
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{radio_text}')")
#         # res = fw_page.page.wait_for_timeout(2000)
#         count = res.count()
#         logger.info(f'{radio_text} label element count: {count}')
#         assert res, f"radio text {radio_text} radio text not found"


# class Test_06_check_add_4to6_tunnel_interface_window_advanced_tab:
#     """测试Add Virtual Interface弹窗的所有标签"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.click(selector='span.sw-tab__inner__piece:text-is("Advanced")')
#         yield
#         fw_page.click_close_icon_by_window_title("Add 4to6 Tunnel Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Enable flow reporting", "12043"),
#                                            ("Local IPv4 Address", "12044"),
#                                            ("Interface MTU", "12045"),
#                                            ("Fragment non-VPN outbound packets larger than this Interface's MTU", "12046"),
#                                            ("Do not send ICMP Fragmentation Needed for outbound packets over the Interface MTU", "12047"),
#                                            ]) 
#     def test_01_check_label_text(self, fw_page, label_text, uuid):
        
#         # 检查标签
#         res = fw_page.page.locator(f'div.sw-form-row__label:text-is("{label_text}")')
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert count == 1, f"{label_text} label not found"


#     @pytest.mark.parametrize("button_name,button_locator,uuid",
#                              [("Cancel","button.configure-modal-ipv4__button-cancel", "12048"),
#                               ("OK", "button.configure-modal-ipv4__button-ok", "12049")])
#     def test_02_check_label(self, fw_page, button_name, button_locator, uuid):
#         logger.info(f'begin to check button {button_name} exist')
#         res = fw_page.page.locator(button_locator)
#         count = res.count()
#         logger.info(f'{button_name} button element count: {count}')
#         assert res, f"{button_name} button not found"



# class Test_07_check_add_wlan_tunnel_interface_window_generl_tab_labels:
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.page.wait_for_timeout(2000)
#         fw_page.select_value_from_button_dropdown("Add Interface", "WLAN Tunnel Interface")
#         fw_page.page.wait_for_timeout(2000)
#         yield
#         # fw_page.click_close_icon_by_window_title("Add Virtual Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Zone", "12050"),
#                                            ("Tunnel ID", "12051"),
#                                            ("Tunnel Source Interface", "12052"),
#                                            ("Mode / IP Assignment", "12053")
#                                            ])
#     def test_01_check_label(self, fw_page, label_text, uuid):
#         # 检查标签
#         res = fw_page.page.locator(f"div.sw-form-row__label:text-is('{label_text}')")
#         # res = fw_page.page.wait_for_timeout(2000)
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert res, f"{label_text} label not found"

# class Test_08_check_add_wlan_tunnel_interface_window_advanced_tab:
#     """测试Add Virtual Interface弹窗的所有标签"""
#     @pytest.fixture(scope="class", autouse=True)
#     def setup_modal_once(self, fw_page):
#         """类级别：只打开一次弹窗"""
#         fw_page.click(selector='span.sw-tab__inner__piece:text-is("Advanced")')
#         yield
#         fw_page.click_close_icon_by_window_title("Add WLAN Tunnel Interface")

#     @pytest.mark.parametrize("label_text,uuid", [("Link Speed", "12054"),
#                                            ("Enable flow reporting", "12055"),
#                                            ("Enable Multicast Support", "12056"),
#                                            ("Enable 802.1p tagging", "12057"),
#                                            ("Exclude from Route Advertisement (NSM, OSPF, BGP, RIP)", "12058"),
#                                            ("Management Traffic Only", "12059"),
#                                            ("Enable Asymmetric Route Support", "12060"),
#                                            ("Interface MTU", "12061"),
#                                            ]) 
#     def test_01_check_label(self, fw_page, label_text, uuid):
        
#         # 检查标签
#         res = fw_page.page.locator(f'div.sw-form-row__label:text-is("{label_text}")')
#         fw_page.page.wait_for_timeout(2000)
        
#         count = res.count()
#         logger.info(f'{label_text} label element count: {count}')
#         assert count == 1, f"{label_text} label not found"


#     @pytest.mark.parametrize("radio_text,uuid", [("Use Default MAC Address", "12062"),
#                                            ("Override Default MAC Address", "12063")])
#     def test_02_check_label(self, fw_page, radio_text, uuid):
#         # 检查标签
#         res = fw_page.page.locator(f"span.sw-radio__label:text-is('{radio_text}')")
#         # res = fw_page.page.wait_for_timeout(2000)
#         count = res.count()
#         logger.info(f'{radio_text} label element count: {count}')
#         assert count == 1, f"radio text {radio_text} radio text not found"


#     @pytest.mark.parametrize("button_name,button_locator,uuid",
#                              [("Cancel","button.configure-modal-ipv4__button-cancel", "12064"),
#                               ("OK", "button.configure-modal-ipv4__button-ok", "12065")])
#     def test_03_check_label(self, fw_page, button_name, button_locator, uuid):
#         logger.info(f'begin to check button {button_name} exist')
#         res = fw_page.page.locator(button_locator)
#         count = res.count()
#         logger.info(f'{button_name} button element count: {count}')
#         assert res, f"{button_name} button not found"


    



  
    












    

