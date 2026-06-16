# Base Configuration Methods for All Pages
import time
import re
from typing import Dict, Any, Optional
from playwright.sync_api import Page
from config.settings import Settings
from config.logger import get_logger
from typing import Callable, Union, List, Tuple, Literal
from playwright.sync_api import Locator


logger = get_logger('base_page')

class BasePage:
    TOP_NAV_TAB = ".sw-top-nav"
    LEVEL_0_TAB = ".sw-nav-item--level-0"
    LEVEL_1_TAB = ".sw-nav-item--level-1"
    MAIN_LEVEL_1_TAB = ".sw-tab--l1"
    MAIN_LEVEL_2_TAB = ".sw-tab--l2"
    STATUS_MESSAGE = '.sw-status-info__text__message'
    FAILED_MESSAGE = '.sw-status-info__failed'
    CLOSE_STATUS_MESSAGE = '.sw-status-info__close'
    BLOCKING = '.sw-blocking-progress '
    MAIN_BLOCKING = '.fw-app-main__blocking '
    DROPDOWN_UNIT_OPTION = ".sw-dropdown-unit"
    TABLE_ICON_BUTTON_TEXT = ".sw-icon-button__label-cont"
    SEARCH_BOX_NAME = "searchText"

    def __init__(self, page: Page):
        self.page = page

    def navigate_to_url(self, url: str):
        logger.info(f'Navigating to URL:    {url}')
        self.page.goto(url)

    def navigate_to_Top_tab(self, top: str):
        logger.info(f'Navigating to Top Nav:    {top}')
        self.page.locator(self.TOP_NAV_TAB).get_by_text(top).click()
    
    def navigate_to_left_level_1_tab(self, level_0: str, level_1: str):
        # example: level_0='Policy', level_1='DPI-SSL'
        level_1_locator = self.page.locator(self.LEVEL_1_TAB).get_by_text(level_1, exact=True)
        if not level_1_locator.is_visible():
            logger.info(f'Navigating to Level_0 Tab:    {level_0}')
            self.page.locator(self.LEVEL_0_TAB).get_by_text(level_0).click()
        logger.info(f'Navigating to level_1 Tab:    {level_1}')
        level_1_locator.click()

    def navigate_to_main_tab(self, level_1: str, level_2: str = None):
        # example:In Policy/DPI-SSL/Client SSL page, l1_tab='General',...
        logger.info(f'Navigating to main Level_1 Tab:    {level_1}')
        self.page.locator(self.MAIN_LEVEL_1_TAB).get_by_text(level_1, exact=True).click()
        if level_2:
            logger.info(f'Navigating to main level_2 Tab:    {level_2}')
            self.page.locator(self.MAIN_LEVEL_2_TAB).get_by_text(level_2, exact=True).click()

    def get_element(self, selector: str):
        logger.info(f'Getting element: {selector}')
        return self.page.locator(selector)

    def get_element_by_text(self, text: str, exact=True):
        logger.info(f'Getting element by text: {text}, exact={exact}')
        return self.page.get_by_text(text, exact=exact)

    #-----------------Click Methods-----------------
    def click(self, selector: str, timeout: int = 30000):
        logger.info(f'Clicking element:   {selector}')
        self.page.click(selector, timeout=timeout)

    def click_icon_button(self, name: str, exact=True, timeout: int = 10000):
        ''' Example:
          Access Rules page: Top - Max Count, Reset Rules, Settings buttons, Buttom - Add, Edit...buttons
        '''
        logger.info(f'Clicking icon button:    {name}, exact={exact}')
        self.page.locator(self.TABLE_ICON_BUTTON_TEXT).get_by_text(text=name, exact=exact).click(timeout=timeout)

    def click_button(self, name: str, exact=True, timeout: int = 10000):
        ''' Example:
          Policy/DPI-SSL/Client SSL page: Accept, Cancel buttons
        '''
        logger.info(f'Clicking button:    {name}, exact={exact}')
        self.page.get_by_role('button', name=name, exact=exact).click(timeout=timeout)


    def get_toggle_status(self, selector: str | Locator, by_input_name=True):
        # Example: selector = "input[name='enable-ssl-inspection']"
        if by_input_name:
            return self.page.input_value(selector, strict=True)
        else:
            return selector.locator('input').input_value()

    def click_toggle(self, selector: str | Locator, enable=True, timeout: int = 30000, by_input_name=True):
        '''
        Parameter
            (bool) by_input_name: if use input name selector to locate the toggle, value is True or False, default to True.
                Example: 
                When this value is True: selector should be string to locator a input element, like "input[name='enable-ssl-inspection']";
                When false: selector should be a locator, like, fw_page.page.locator('.sw-form-row__field-cont ', has_text='1. Violence')
        '''
        stat = {'0': 'Disabled', '1': 'Enabled'}
        if selector:
            status = self.get_toggle_status(selector, by_input_name)
            if not enable and status == "0" or enable and status == "1":
                logger.info(f'Toggle already in desired state:    {stat[status]}')
                return True
            elif enable and status == "0":
                logger.info('Enable toggle ......')
            elif not enable and status == "1":
                logger.info('Disable toggle ......')
            if by_input_name:
                self.page.locator('.sw-toggle', has=self.page.locator(selector)).click(timeout=timeout)
            else:
                selector.locator('.sw-toggle ').click(timeout=timeout)
            new_status = self.get_toggle_status(selector, by_input_name)
            logger.info(f'Current Toggle status:    {stat[new_status]}')
            return True
        logger.info(f'Toggle locator not found:   {selector}')
        return False

    def get_checkbox_status_by_input_name(self, name: str):
        selector = f"input[name='{name}'] ~ .sw-checkbox__box "
        locator = self.page.locator(selector).locator('.sw-checkbox__box__mark ')
        locator_class = locator.get_attribute('class')
        return 'unchecked' if 'sw-checkbox__box__mark--no' in locator_class else 'checked'
    
    def click_checkbox_by_input_name(self, name: str, enable=True, timeout: int = 30000):
        '''check or uncheck checkbox by name of input element

        :param str name: the name of the input element, like:'enable-ssl-inspection'
        '''
        selector = f"input[name='{name}'] ~ .sw-checkbox__box "
        locator = self.page.locator(selector).locator('.sw-checkbox__box__mark ')
        if locator:
            status = self.get_checkbox_status_by_input_name(name)
            if not enable and status == "unchecked" or enable and status == "checked":
                logger.info(f'Checkbox already in desired state:    {status}')
                return True
            elif enable and status == "unchecked":
                logger.info('Check checkbox......')
            elif not enable and status == "checked":
                logger.info('Uncheck checkbox ......')
            locator.click(timeout=timeout)
            new_status = self.get_checkbox_status_by_input_name(name)
            logger.info(f'Current checkbox status:    {new_status}')
            return True
        logger.info(f'Checkbox locator not found:   {selector}')
        return False

    def get_radio_status_by_input_name(self, name: str):
        selector = f"input[name='{name}'] ~ .sw-radio__fake-radio-button "
        locator = self.page.locator(selector)
        locator_class = locator.get_attribute('class')
        return 'checked' if 'sw-radio__fake-radio-button--checked' in locator_class else 'unchecked'
    
    def click_radio_button_by_input_name(self, name: str, timeout: int = 30000):
        ''' Click radio button by name of input element

        :param str name: the name of the input element, like:'enable-ssl-inspection'
        '''
        selector = f"input[name='{name}'] ~ .sw-radio__fake-radio-button "
        locator = self.page.locator(selector)
        if locator:
            status = self.get_radio_status_by_input_name(name)
            if status == "checked":
                logger.info(f'Radio button is already Checked.')
                return True
            logger.info('Check radio button......')
            locator.click(timeout=timeout)
            new_status = self.get_radio_status_by_input_name(name)
            logger.info(f'Current radio button status:    {new_status}')
            return True
        logger.info(f'Radio button locator not found:   {selector}')
        return False

    def toggle_switch(self, selector: str, enable: bool):
        current_state = self.page.is_checked(selector)
        if current_state != enable:
            self.click(selector)

    #-----------------Other Methods-----------------
    def mouse_hover(self, selector: str, timeout: int = 30000):
        logger.info(f'Mouse hover on element: {selector}')
        self.page.hover(selector, timeout=timeout)
    
    def fill(self, selector: str, value: str):
        logger.info(f'Filling element: {selector} with value: {value}')
        self.page.fill(selector, value)
    
    def get_text(self, selector: str, timeout: int = 30000) -> str:
        logger.info(f'Getting text from element: {selector}')
        return self.page.text_content(selector, timeout=timeout)

    def get_search_box_locator(self):        
        return self.page.locator(f'input[name*="{self.SEARCH_BOX_NAME}"]')
    
    def fill_search_box(self, value: str):        
        box = self.get_search_box_locator()
        box.fill(value)
        # box.press('Enter')

    
    #-----------------Wait Methods-----------------
    def wait_for_selector(self, selector: str, timeout: int = 30000):
        self.page.wait_for_selector(selector, timeout=timeout)
    
    def wait_for_load_state(self, state: str = "load", timeout: int = 30000):
        self.page.wait_for_load_state(state, timeout=timeout)

    def wait_for_load_page(self, enforce=False, timeout: int = 30000):
        self.page.wait_for_load_state('domcontentloaded', timeout=30000)
        self.page.locator(self.BLOCKING).wait_for(state="hidden", timeout=30000)
        self.page.locator(self.MAIN_BLOCKING).wait_for(state="hidden", timeout=30000)
        self.page.get_by_text('loading').wait_for(state="hidden", timeout=30000)
        if enforce:
            self.page.wait_for_timeout(timeout)
    
    def is_element_visible(self, selector: str) -> bool:
        # No timeout
        return self.page.is_visible(selector)
    
    def take_screenshot(self, name: str):
        self.page.screenshot(path=f"{Settings.SCREENSHOTS_DIR}/{name}.png")

    # -------------------Dropdown Box----------------------
    @staticmethod
    def _build_dropdown_box_selector(box_name: str, element_type="arrow", strict=True, pane='') -> str:
        """get the specific type of element related to the dropdown_box with the identifier, and return the element xpath location

        USAGE EXAMPLES:
            mode_arrow = get_dropdown_box_element_xpath("Mode / IP Assignment", 'arrow')

        :param str identifier: identifier of the dropdown box, 
            example:In Device/Settings/Administration/Firewall Administrator page, 'Wireless Controller Mode' dropdown box, the identifier is 'Wireless Controller Mode'
        :param str element_type: target element type related to the box, like arrow, text, pencil, or info, defaults to "arrow"
        :return list: return ['xpath', {path}]
        """
        
        parent = f'[contains(@class, "sw-title-pane__header ") and normalize-space(.)="{pane}"]/following-sibling::*' if pane else ''
        if strict:
            common_path = f'//div{parent}[normalize-space(.)="{box_name}"]/following-sibling::*[contains(@class, "sw-form-row__field")]'
        else:
            common_path = f'//div{parent}[contains(text(), "{box_name}")]/following-sibling::*[contains(@class, "sw-form-row__field")]'
        path = common_path + '/descendant::*[contains(@class, "sw-select__icon")]'
        if element_type.lower() == 'text':
            path = common_path + '/descendant::*[contains(@class, "sw-select__label-cont")]'
        if element_type.lower() == 'pencil':
            path = common_path + '/descendant::*[contains(@class, "icon-pencil")]'
        if element_type.lower() == 'info':
            path = common_path + '/descendant::*[contains(@class, "icon-info")]'
        return path

    def get_current_value_in_dropdown_box(self, box_name: str,) -> str:
        current = self.page.locator(self._build_dropdown_box_selector(box_name, 'text')).text_content()
        logger.info(f'Current selected value:   "{current}"')
        return current

    def select_value_in_dropdown_box(self, box_name: str, value, timeout: int = 30000, pane='') -> str:
        ''' select dropdown box by name label text of the dropdown box
        
        :param str name: the name of the input element, like:'enable-ssl-inspection'
        '''
        logger.info(f'Click {box_name} dropdown box')
        selector = self._build_dropdown_box_selector(box_name=box_name, pane=pane)
        self.click(selector, timeout=timeout)

        logger.info(f'Select "{value}"')
        unit = self.page.locator(self.DROPDOWN_UNIT_OPTION)
        unit.get_by_text(value, exact=True).click()
        unit.wait_for(state="hidden", timeout=timeout)

        self.page.wait_for_timeout(500)
        current = self.get_current_value_in_dropdown_box(box_name)
        return current

    def get_current_value_in_dropdown_box_use_input_name(self, name: str,) -> str:
        # current = self.page.locator(f'input[name={name}] ~ .sw-select__icon').locator('.sw-select__label-text').text_content()
        box = self.page.locator(f'input[name={name}]')
        selector = self.page.locator('.sw-select', has=box).locator('.sw-select__label-text')
        current = selector.text_content()
        logger.info(f'Current selected value:   "{current}"')
        return current

    def select_value_in_dropdown_box_use_input_name(self, name: str, value, timeout: int = 30000) -> str:
        ''' select dropdown box by name of input element

        :param str name: the name of the input element, like:'enable-ssl-inspection'
        '''
        logger.info(f'Click {name} dropdown box')
        box = self.page.locator('.sw-select', has=self.page.locator(f'input[name={name}]')).locator('.sw-select__label-cont')
        box.click()

        logger.info(f'Select "{value}"')
        box.locator('.sw-select__label-input').fill(value)
        unit = self.page.locator(self.DROPDOWN_UNIT_OPTION)
        unit.get_by_text(value, exact=True).click()
        unit.wait_for(state="hidden", timeout=timeout)

        self.page.wait_for_timeout(500)
        current = self.get_current_value_in_dropdown_box_use_input_name(name)
        return current

    def get_drop_down_list_values(self, box_name, timeout: int = 30000) -> list:
        values = []
        logger.info(f'Click {box_name} dropdown box')
        selector = self._build_dropdown_box_selector(box_name=box_name)
        self.click(selector, timeout=timeout)

        logger.info(f'Get {box_name} dropdown box list')
        self.page.locator(".sw-dropdown__inner").wait_for(state="visible")
        values = self.page.locator(self.DROPDOWN_UNIT_OPTION).all_text_contents()
        self.click(selector, timeout=timeout)
        return values

    # -------------------Prompt Alert-------------------------------
    def compare_status_message(self, expected_message) -> bool:
        """Compare alert message"""
        actual_message = self.get_text(self.STATUS_MESSAGE).lower().lstrip().rstrip()
        logger.info('Comparing alert message......')
        logger.debug(f'Actual text\t:{actual_message}')
        logger.debug(f'Expected text\t:{str(expected_message)}')
        if isinstance(expected_message, list):
            expected_message_list = [msg.lower() for msg in expected_message]
            if actual_message in expected_message_list:
                return True
        if isinstance(expected_message, str) and actual_message == expected_message.lower().lstrip().rstrip():
            return True
        logger.error(f"Message mismatch\t:{actual_message}")
        logger.error(f"Target Message\t:{str(expected_message)}")
        return False

    def accept_alert(self):
        logger.info("Action - Clicking on Confirm button")
        parent = self.page.locator('.sw-confirm-modal__footer .sw-button')
        parent.get_by_text(re.compile("Confirm|OK|Ok|Accept")).click()

    def verify_status_message(self, targetMsg):
        self.compare_status_message(targetMsg)
        self.accept_alert()

    def verify_window_prompt(self, title:str, ):
        add_window = self.page.locator(f'.sw-modal:has-text("{title}")')
        style = add_window.get_attribute('style')
        logger.info(style)
        return 'display: none' not in style
    

    ############################################ add by jlian ########################################


    def switch_tab(self, tab_name: str, tab_level: Literal["l1", "l2"] = "l1", verify: bool = True, timeout: int = 10000) -> bool:
        """

        """
        try:
            active_selector = f'.sw-tab--{tab_level}.sw-tab--active:has-text("{tab_name}")'
            tab_selector = f'.sw-tab--{tab_level}:has-text("{tab_name}")'
            logger.info(f"Attempting to switch to tab: {tab_name} (level: {tab_level})")
            self.page.wait_for_selector(tab_selector, timeout=timeout)
            if self.is_tab_active(tab_name, tab_level):
                logger.info(f"Tab '{tab_name}' is already active at level {tab_level}")
                return True
            
            current_active = self.get_active_tab(tab_level)
            if current_active:
                logger.debug(f"Current active tab at level {tab_level}: {current_active}")
            
            logger.debug(f"Clicking tab: {tab_name}")
            tab_element = self.page.locator(tab_selector).first
            
            tab_element.wait_for(state="visible", timeout=timeout)
            tab_element.click()
            
            if verify:
                logger.debug(f"Verifying tab activation for: {tab_name}")
                self.page.wait_for_selector(active_selector, timeout=timeout)
                
                # Double-check using is_tab_active method
                if not self.is_tab_active(tab_name, tab_level):
                    logger.warning(f"Tab '{tab_name}' click completed but activation verification failed")
                    return False
                
                logger.info(f"Successfully switched to active tab: {tab_name}")
            else:
                logger.info(f"Tab '{tab_name}' clicked (verification skipped)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch tab '{tab_name}' at level {tab_level}: {str(e)}")
            return False
        

    def is_tab_active(self, tab_name: str, tab_level: Literal["l1", "l2"] = "l1") -> bool:
        """
        Example:
            >>> page.is_tab_active("Interface Settings", "l1")
        """
        logger.info(f"Checking if tab is active: {tab_name} (level: {tab_level})")
        
        try:
            active_selector = f'.sw-tab--{tab_level}.sw-tab--active:has-text("{tab_name}")'
            logger.debug(f"Using active tab selector: {active_selector}")
            is_active = self.page.locator(active_selector).count() > 0
            status = "active" if is_active else "inactive"
            logger.info(f"Tab '{tab_name}' is {status}")
            return is_active
            
        except Exception as e:
            logger.error(f"Error checking tab status for '{tab_name}': {str(e)}")
            return False
    
    def get_active_tab(self, level: str = "l1") -> Optional[str]:
        """
        Example:
            >>> page.get_active_tab("l1")
            >>> page.get_active_tab("l2")
        """
        try:
            active_tab_selector = f'.sw-tab--{level}.sw-tab--active'
            active_tab = self.page.locator(active_tab_selector).first
            
            if active_tab.count() == 0:
                logger.debug(f"No active tab found at level {level}")
                return None
            tab_text = active_tab.text_content()
            if tab_text and tab_text.strip():
                tab_name = tab_text.strip()
                logger.info(f"Active tab at level {level}: {tab_name}")
                return tab_name

            # tab_name = active_tab.get_attribute("data-tab-name")
            # if tab_name:
            #     logger.info(f"Active tab at level {level}: {tab_name} (from data-tab-name)")
            #     return tab_name
            
            # child_text = active_tab.locator('.sw-tab__label, .tab-label').first.text_content()
            # if child_text and child_text.strip():
            #     logger.info(f"Active tab at level {level}: {child_text.strip()} (from child)")
            #     return child_text.strip()
            
            logger.warning(f"Could not determine name of active tab at level {level}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting active tab: {str(e)}")
            return None

        
    def extract_table_footer_total_count(self) -> int:
        try:
            logger.info('begin to extract table footer total count.....')
            # table_total = self.page.locator('.sw-table-footer__total-cont__value')
            table_total = self.page.locator('.sw-table-footer__total-cont__value:not(.sw-modal .sw-table-footer__total-cont__value)')
            logger.info('waiting for table footer total element to be visible')
            # self.page.wait_for_selector('.sw-table-body__cont__table', state="attached", timeout=5000)
            self.page.wait_for_timeout(5000)
            
            # Handle multiple footer elements - get the first visible one with non-zero count
            if table_total.count() > 1:
                logger.info(f"Found {table_total.count()} table footer elements, checking each...")
                for i in range(table_total.count()):
                    element_text = table_total.nth(i).inner_text().strip()
                    logger.info(f"Footer element {i+1} text: {element_text}")
                    match = re.search(r'(\d+)', element_text)
                    if match:
                        total_number = int(match.group(1))
                        if total_number > 0:
                            logger.info(f"Using footer element {i+1} with count: {total_number}")
                            return total_number
                # If all have zero, use the first one
                element_text = table_total.first.inner_text().strip()
            else:
                element_text = table_total.inner_text().strip()
            
            logger.info(f"table footer total text is: {element_text}")
            match = re.search(r'(\d+)', element_text)
            if match:
                total_number = int(match.group(1))
                logger.info(f"extract table footer total count: {total_number}")
            else:
                logger.warning(f"did not extract table footer total count: {element_text}")
                total_number = 0
            
            return total_number
        except Exception as e:
            logger.error(f"failed to extract table footer total count: {str(e)}")
            return 0
        
    def get_table_row_count_by_container(self, table_container_class: str) -> int:
        """
        Get the number of rows in a table identified by its container class.
        
        This method waits for the table to load, then counts the rows excluding expanded rows.
        
        Args:
            table_container_class: The CSS class of the table container (e.g., 'interface-settings-ipv4')
        
        Returns:
            Number of rows in the table, or 0 if failed to get count
        """
        try:
            # Wait for the table to load
            self.page.wait_for_selector('.sw-table-body__cont__table', state="visible", timeout=5000)
            
            # Build XPath to find rows in the specified container, excluding expanded rows and modal rows
            xpath = f'''

            //div[contains(@class,'{table_container_class}')]
            /div[contains(@class,'sw-table')]
            //div[contains(@class, 'sw-table-body__cont__table')
                and not(ancestor::div[contains(@class, 'sw-table-expand-row')])]
                /div[contains(@class, 'sw-table-row') and not(ancestor::div[contains(@class, 'sw-modal')])]

            '''
            # xpath = f'''
            # # //div[contains(@class,'{table_container_class}')]
            # # /div[contains(@class,'sw-table')]
            # # //div[contains(@class, 'sw-table-body__cont__table')
            # #     and not(ancestor::div[contains(@class, 'sw-table-expand-row')])]]
            # #     /div[contains(@class, 'sw-table-row')
            
            # '''
            # Get table rows
            rows = self.page.locator(f'xpath={xpath}')
            count = rows.count()
            
            logger.info(f"Table '{table_container_class}' has {count} rows")
            return count
            
        except TimeoutError:
            logger.error(f"Timeout waiting for table with container class '{table_container_class}'")
            return 0
            
        except Exception as e:
            logger.error(f"Error getting table count for '{table_container_class}': {e}")
            return 0
    
    def get_table_row_text(self, table_container_class: str, selector_text: str = None, column_index: int = None) -> Optional[List[str]]:
        rowlist = [] 
        logger.info('wait for table to load')
        loading_selector = f'div.{table_container_class} div.sw-table-body__cont__table:has-text("Loading...")'
        self.page.wait_for_selector(loading_selector, state='hidden', timeout=10000)
        try:
            row = self.get_table_row_locator(table_container_class, selector_text, column_index) 
            if row:                    
                row_text = row.inner_text().strip()
                logger.info(f"Found row text: '{row_text}'")
                rowlist = row_text.split('\n')
                return rowlist
        except Exception as e:
            logger.error(f"Error getting table row text for '{table_container_class}': {e}")
            return rowlist
    
    
    def get_table_row_locator(self, table_container_class: str, selector_text: str, column_index: int = None) -> Optional[Locator]:
        """
        Find and return the locator for a specific row in a table.
        
        Args:
            container_class: The class name of the table container
            selector_text: Text to search for in the table rows
            column_index: Optional column index to search in (0-based)
            
        Returns:
            Locator: The locator for the matching row, or None if not found
        """
        try:
            # Wait for loading to complete first
            logger.info('Waiting for table to finish loading...')
            loading_selector = f'div.{table_container_class} div.sw-table-body__cont__table:has-text("Loading...")'
            self.page.wait_for_selector(loading_selector, state='hidden', timeout=10000)
            
            # Additional wait to ensure data is loaded
            self.page.wait_for_timeout(2000)
            
            # Get all rows in the table
            rows = self.get_table_rows(table_container_class)
            if not rows:
                logger.info(f"No rows found in container: {table_container_class}")
                return None
                
            logger.info(f"Found {rows.count()} rows in container: {table_container_class}")
            logger.info(f"Searching for text: '{selector_text}' in column {column_index if column_index is not None else 'any'}")
            
            # Iterate through each row to find the matching text
            for i in range(rows.count()):
                row = rows.nth(i)
                row_text = row.inner_text().strip()
                logger.info(f"  Row {i+1} text: '{row_text}'")
                
                # Skip loading rows
                if "Loading..." in row_text:
                    logger.info(f"  Skipping loading row {i+1}")
                    continue
                
                # If column_index is specified, search only in that column
                if column_index is not None:
                    cells = row.locator('.sw-table-row__cell')
                    if cells.count() > column_index:
                        cell_text = cells.nth(column_index).inner_text().strip()
                        logger.info(f" Column {column_index} text: '{cell_text}'")
                        if selector_text and selector_text == cell_text:
                            logger.info(f"  Found '{selector_text}' in row {i+1}, column {column_index}")
                            return row
                else:
                    # Search in entire row text
                    if selector_text and selector_text in row_text:
                        logger.info(f"  Found '{selector_text}' in row {i+1}")
                        return row
            logger.warning(f"Did not find any matching row in container: {table_container_class}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding row in container '{table_container_class}': {e}")
            return None
        
    def get_table_rows(self, table_container_class: str) -> Locator:
        """
        Get table row locators (returns Locator object)
        
        Args:
            table_container_class: The class name of the table container
            
        Returns:
            Locator: Locator for all rows
        """
        try:
            # Wait for table to load
            self.page.wait_for_selector('.sw-table-body__cont__table', state="visible", timeout=5000)
            
            # Build XPath
            row_xpath = f'''
            //div[contains(@class,'{table_container_class}')]
            /div[contains(@class,'sw-table')]
            //div[contains(@class, 'sw-table-body__cont__table')]
                /div[contains(@class, 'sw-table-row')]
            '''
            
            rows = self.page.locator(f'xpath={row_xpath}')
            count = rows.count()
            
            if count > 0:
                logger.info(f"Found {count} rows in container: '{table_container_class}'")
                return rows
            else:
                logger.warning(f"No rows found in container: '{table_container_class}'")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get table rows for '{table_container_class}': {e}")
            return None

    def get_table_header(self, table_container_class: str) -> List[str]:
        headerslist=[]
        try:
            # Wait for the table to load
            self.page.wait_for_selector('.sw-table__wrapper', state="attached", timeout=10000)
            self.page.wait_for_timeout(5000)
            header_css = f".{table_container_class} >.sw-table .sw-table-header"
            table_header = self.page.locator(header_css)
            if table_header:
                table_header = table_header.first
                header_text = table_header.inner_text().strip()

                headerslist = header_text.split('\n')
                logger.info(f"table headers: {headerslist}")
            else:
                logger.warning("Table header not found")
        except Exception as e:
            logger.error(f"Error getting table header: {e}")
        return headerslist   

    def select_value_from_button_dropdown(self,button_name: str,option_text: str) -> bool:
        """
        from button dropdown select option
        example:
            page.select_value_from_button_dropdown("Add Interface", "VLAN Interface")
        """
        try:
            logger.info(f'click button: {button_name}')
            # self.page.get_by_text(button_name, exact=True).click()
            self.find_element(selector='.sw-icon-button', text=f'{button_name}', exact=True).click()

            logger.info(f'wait for dropdown to appear')
            self.page.wait_for_selector("div.sw-dropdown__inner", timeout=10000)
            
            logger.info(f'select option: {option_text} from dropdown')
            self.page.locator(f"div.sw-dropdown__inner span:has-text('{option_text}')").click()
            return True
        except Exception as e:
            logger.error(f"failed: {e}")
            return False   

    def get_values_from_button_dropdown(self,button_name:str)->List[str]:
        """
        get value from button dropdown
        example:
            page.get_values_from_button_dropdown("Add Interface")
        """
        try:
            logger.info(f'click button: {button_name}')
            self.page.get_by_text(button_name, exact=True).click()
            
            logger.info(f'wait for dropdown to appear')
            self.page.wait_for_selector("div.sw-dropdown__inner", timeout=5000)
            
            logger.info(f'get options from dropdown')
            options = self.page.locator("div.sw-dropdown__inner span").all_inner_texts()
            logger.info(f"dropdown options: {options}")
            return options
        except Exception as e:
            logger.error(f"failed: {e}")
            return []  

    def click_close_icon_by_window_title(self, window_title: str, window_type: str = 'modal', verify: bool = True) -> bool:
        """Click close icon by window title
        
        Args:
            window_title: Window title text
            window_type: Window type, 'modal' or 'popover'
            verify: Whether to verify close result, default True
        """
        try:
            # Selector
            if window_type.lower() == 'modal':
                close_selector = f".sw-modal__title:text-is('{window_title}') ~ .sw-modal__close-cont .sw-modal__close"
            elif window_type.lower() == 'popover':
                close_selector = f".sw-popover__board__title__text:text-is('{window_title}') ~ .sw-popover__board__title__close .sw-icon"
            
            # Click close
            close_button = self.page.locator(close_selector)
            close_button.wait_for(state="visible", timeout=5000)
            close_button.click()
            
            # Verify close result
            if verify:
                try:
                    close_button.wait_for(state="hidden", timeout=3000)
                    logger.info(f"Window closed: {window_title}")
                    return True
                except:
                    logger.warning(f"Window '{window_title}' may not be fully closed")
                    return False
            else:
                logger.info(f"Close clicked: {window_title}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return False
        
    def find_element(
        self,
        text: str = None,
        selector: str = None,
        role: str = None,
        name: str = None,
        placeholder: str = None,
        has_text: str = None,
        exact: bool = True,
        timeout: int = 30000,
        wait_until: str = "visible",
        **kwargs
    ) -> Locator:
        # timeout = timeout
        
        try:
            # Support both text and has_text for backward compatibility
            if text and selector:
                # When both text and selector are provided, treat text as has_text
                has_text_param = text
                text = None
            else:
                has_text_param = has_text
                
            locator = self._resolve_element_locator(
                text=text,
                selector=selector,
                role=role,
                name=name,
                placeholder=placeholder,
                has_text=has_text_param,
                exact=exact,
                **kwargs
            )
                        
            if wait_until == "none":
                # check if element exists
                if locator.count() > 0:
                    return locator
                return self.page.locator('__not_found__')
            
            # wait for element
            if wait_until == "visible":
                locator.first.wait_for(state="visible", timeout=timeout)
            elif wait_until == "hidden":
                locator.first.wait_for(state="hidden", timeout=timeout)
            elif wait_until == "attached":
                locator.first.wait_for(state="attached", timeout=timeout)
            elif wait_until == "detached":
                locator.first.wait_for(state="detached", timeout=timeout)
            else:
                logger.warning(f"not supported wait_until value: {wait_until}")
                return self.page.locator('__invalid_wait_until__')
        
            # return locator.all() 
            return locator
            
        except TimeoutError:
            logger.warning(f"wait for element timeout: selector={selector}, text={text}")
            return self.page.locator('__timeout__')
        except Exception as e:
            logger.warning(f"find element failed: selector={selector}, text={text}, error={e}")
            return self.page.locator('__error__')


    def click_element(
        self,
        text: str = None,
        selector: str = None,
        role: str = None,
        name: str = None,
        placeholder: str = None,
        has_text: str = None,
        exact: bool = True,
        timeout: int = 30000,
        wait_until: str = "visible",
        **kwargs
        ) -> bool:
        try:
            element = self.find_element(
                text=text,
                selector=selector,
                role=role,
                name=name,
                placeholder=placeholder,
                has_text=has_text,
                exact=exact,
                timeout=timeout,
                wait_until=wait_until,
                **kwargs
            )
            
            if element.count() == 0:
                logger.error("Element not found for clicking")
                return False
            
            element.first.click(timeout=timeout)
            logger.info(f"Successfully clicked element: {text or selector or name or role}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False
        
    def _resolve_element_locator(self, 
                               text: str = None,
                               selector: str = None,
                               role: str = None,
                               name: str = None,
                               label: str = None,
                               placeholder: str = None,
                               has_text: str = None,
                               exact: bool = True) -> Locator:
        """resolve element locator"""
        if has_text and selector:
            return self.page.locator(selector).get_by_text(text=has_text, exact=exact)
        elif text:
            return self.page.get_by_text(text, exact=exact)
        elif selector:
            return self.page.locator(selector)
        elif role and name:
            return self.page.get_by_role(role, name=name, exact=exact)
        elif role:
            return self.page.get_by_role(role)
        elif label:
            return self.page.get_by_label(label, exact=exact)
        elif placeholder:
            return self.page.get_by_placeholder(placeholder, exact=exact)
        elif name:
            # return self.page.get_by_name(name)
            return self.page.locator(f'[name="{name}"]')
        
        # If no valid locator parameters are provided, return special marker locator
        return self.page.locator('__no_locator_params__')
    

    def fill_input(
        self,
        text: str = None,
        selector: str = None,
        role: str = None,
        name: str = None,
        placeholder: str = None,
        label: str = None,
        has_text: str = None,
        input_value: str = None,
        exact: bool = True,
        timeout: int = 30000,
        wait_until: str = "visible",
        clear_first: bool = True,
        **kwargs
        ) -> bool:

        try:
            # Use find_element to locate the input field
            element = self.find_element(
                text=text,
                selector=selector,
                role=role,
                name=name,
                placeholder=placeholder,
                label=label,
                has_text=has_text,
                exact=exact,
                timeout=timeout,
                wait_until=wait_until,
                **kwargs
            )
            
            if element.count() == 0:
                logger.error(f"Element not found for filling: {text or selector or name or role or placeholder or label}")
                return False
            
            # Clear the field if requested
            if clear_first:
                element.first.clear(timeout=timeout)
                logger.info(f"Cleared input field")
            
            # Fill the value
            element.first.fill(input_value, timeout=timeout)
            logger.info(f"Successfully filled '{input_value}' in element: {text or selector or name or role or placeholder or label}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill element: {e}")
            return False

    def get_input_value_by_label_name(
        self,
        label_text: str,
        label_exact: bool = True,
        timeout: int = 30000,
        **kwargs
    ) -> str:
        try:
            # Build selector - consistent with fill_input_by_label_name
            if label_exact:
                # Exact match: use complete label text
                selector = f'div.sw-form-row__label:has-text("{label_text}") ~ div.sw-form-row__field input'
            else:
                # Fuzzy match: use regex for case-insensitive matching
                selector = f'div.sw-form-row__label:text-matches("{label_text}", "i") ~ div.sw-form-row__field input'
            
            # Find input element
            input_element = self.find_element(
                selector=selector,
                timeout=timeout,
                wait_until="visible"
            )
            
            if input_element.count() == 0:
                logger.warning(f"Input element not found for label: {label_text}")
                return ""
            
            # Get input value
            input_value = input_element.first.input_value()
            logger.info(f"Retrieved input value for '{label_text}': {input_value}")
            
            return input_value
            
        except Exception as e:
            logger.error(f"Failed to get input value for label '{label_text}': {e}")
            return ""
    
    def fill_input_by_label_name(
        self,
        label_text: str,
        input_value: str,
        label_exact: bool = True,
        clear_first: bool = True,
        timeout: int = 30000,
        verify_filled: bool = True,  # Enable verification by default
        retry_count: int = 1,        # Retry count when verification fails
        **kwargs
    ) -> bool:

        try:
            # Build selector - adjust based on label_exact parameter
            if label_exact:
                # Exact match: use complete label text
                selector = f'div.sw-form-row__label:text-is("{label_text}") ~ div.sw-form-row__field input'
            else:
                # Fuzzy match: use regex for case-insensitive matching
                selector = f'div.sw-form-row__label:text-matches("{label_text}", "i") ~ div.sw-form-row__field input'
            
            # Use existing fill_input
            success = self.fill_input(
                selector=selector,
                input_value=input_value,
                clear_first=clear_first,
                timeout=timeout,
                # Don't pass has_text since selector already handles the matching
                **kwargs
            )
            
            if not success:
                logger.error(f"Failed to fill input with label '{label_text}'")
                return False
            
            # Basic verification: check if element exists and is visible
            if verify_filled:
                try:
                    # Lightweight verification: check if element still exists
                    element = self.find_element(
                        selector=selector,
                        timeout=2000,  # Short timeout
                        wait_until="visible"
                    )
                    
                    if element.count() == 0:
                        logger.warning(f"Element disappeared after filling: {label_text}")
                        return False
                    # Optional: verify input value
                    if retry_count > 0:
                        for attempt in range(retry_count + 1):
                            try:
                                actual_value = element.first.input_value()
                                if actual_value == input_value:
                                    logger.info(f"✓ Input verified: {label_text} = {input_value}")
                                    return True
                                else:
                                    logger.warning(f"Value mismatch attempt {attempt+1} for {label_text}: "
                                                f"Expected '{input_value}', Got '{actual_value}'")
                                    
                                    if attempt < retry_count:
                                        # Retry
                                        logger.info(f"Retrying fill for {label_text}...")
                                        element.first.fill("")
                                        element.first.fill(input_value)
                                        self.page.wait_for_timeout(500)
                            except Exception as e:
                                logger.warning(f"Verification attempt {attempt+1} failed: {e}")
                                continue
                        logger.error(f"All retry attempts failed for {label_text}")
                        return False
                    return True
                except Exception as verify_error:
                    # Verification failed but don't block main flow
                    logger.warning(f"Verification failed (non-blocking) for {label_text}: {verify_error}")
                    return True  # Still return success since fill operation succeeded
            return success
            
        except Exception as e:
            logger.error(f"fill_input_by_label_name failed: {e}")
            return False
            
    def set_toggle_by_locator(self, locator: Locator, enable: bool = True, verify: bool = True, 
                        handle_confirmation: bool = False, confirm_text: str = "OK") -> bool:
        try:
            if locator.count() == 0:
                logger.error("Toggle locator not found")
                return False
            # 1. First find the visible toggle element
            toggle_element = locator.locator('.sw-toggle')
            if toggle_element.count() == 0:
                logger.error("Toggle element not found in locator")
                return False
            
            # 2. Find the hidden input element within toggle
            hidden_input = toggle_element.locator('input[name="enable-button"]')
            if hidden_input.count() == 0:
                logger.error("Hidden input not found in toggle element")
                return False
            
            # 3. Get state value from hidden input
            current_value = hidden_input.get_attribute('value') 
            logger.info(f"Current state: {current_value}")
            target_value = "1" if enable else "0"
            
            # If already in target state
            if current_value == target_value:
                logger.info(f"Toggle already in target state: {target_value}")
                return True
            
            # Click toggle
            logger.info(f"Clicking toggle, target state: {target_value}")
            # Click visible toggle element
            toggle_element.first.click()
            
            # Handle confirmation dialog
            if handle_confirmation:
                logger.info(f"Waiting for confirmation dialog, confirm text: {confirm_text}")
                try:
                    # Use existing click_dialog_button method
                    success = self.click_dialog_button(confirm_text)
                    if success:
                        logger.info(f"Clicked confirm button: {confirm_text}")
                        # Wait for confirmation dialog to disappear
                        self.page.wait_for_timeout(1000)
                    else:
                        logger.warning("Confirm button not found, possibly no confirmation dialog")
                except Exception as e:
                    logger.warning(f"Error handling confirmation dialog: {e}")
            
            # If verification needed (enabled by default)
            if verify:
                # Wait for state change, retry up to 10 times with 1 second interval
                for retry in range(10):
                    self.page.wait_for_timeout(1000)
                    new_value = hidden_input.get_attribute('value')
                    logger.info(f"Retry {retry + 1}/10: Current state {new_value}, Target state {target_value}")
                    
                    if new_value == target_value:
                        logger.info(f"State toggle successful: {target_value}")
                        return True
                
                logger.error(f"State toggle failed: Expected {target_value}, Actual {new_value}")
                return False
            return True
        except Exception as e:
            logger.error(f"Toggle failed: {e}")
            return False   

    def click_diag_button(self, button_name: str) -> bool:
        """
        
        Clicks a button on the diagnosis page with the specified title
    
        Example:
            page.click_diag_button("Run Test")
        """
        try:
            self.click(selector=f"div.sw-confirm-modal__dialog button:has-text('{button_name}')")
                # button = self.page.locator("sw-confirm-modal__dialog button:has-text('OK')")
            # button.click()
            # self.page.wait_for_timeout(500)  
            logger.info(f"Clicking diagnosis button: {button_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to click diagnosis button: {e}")
            return False
        
    def verify_text_exists(self, text: str, timeout: int = 5000) -> bool:
        """verify_text_exists"""
        try:
            logger.debug(f"verify_text_exists: {text}")
            element = self.page.get_by_text(text)
            logger.debug(f"wait_for_element_state: {element}    ")
            element.wait_for(state="visible", timeout=timeout)
            return True
        except Exception as e:
            return False

    def get_background_color(self, locator: Locator, element_index: int = 0) -> str:
        """
        Get background color of an element
        
        Args:
            locator: Playwright Locator object
            element_index: Element index, default 0
            
        Returns:
            str: Background color string
        """
        try:
            if locator.count() <= element_index:
                logger.warning(f"Element not found at index: {element_index}")
                return ""
            
            bg_color = locator.nth(element_index).evaluate("""
                element => {
                    return window.getComputedStyle(element).backgroundColor;
                }
            """)
            
            logger.debug(f"Background color: {bg_color}")
            return bg_color
            
        except Exception as e:
            logger.error(f"Failed to get background color: {str(e)}")
            return ""

    def is_orange_background(self, locator: Locator, element_index: int = 0) -> bool:
        """
        Check if element has orange background color
        
        Args:
            locator: Playwright Locator object
            element_index: Element index, default 0
            
        Returns:
            bool: True if background is orange, False otherwise
        """
        try:
            bg_color = self.get_background_color(locator, element_index)
            
            if not bg_color:
                logger.debug("No background color retrieved")
                return False
            
            logger.debug(f"Checking if color is orange: {bg_color}")
            
            return self.is_orange_color(bg_color)
                
        except Exception as e:
            logger.error(f"Failed to check orange background: {str(e)}")
            return False

    def is_orange_color(self, color: str) -> bool:
        """
        Check if color string represents orange color
        
        Args:
            color: Color string, e.g. "rgba(255, 121, 26, 0.1)"
            
        Returns:
            bool: True if color is orange, False otherwise
        """
        try:
            pattern = r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)'
            match = re.search(pattern, color)
            
            if not match:
                logger.debug(f"Cannot parse RGBA: {color}")
                return False
            
            r, g, b, a = map(float, match.groups())
            
            # Orange color characteristics (based on the image color)
            # High red component (close to 255)
            # Medium green component (100-150)
            # Low blue component (<50)
            is_orange_hue = (
                r > 200 and        # High red component
                50 < g < 200 and   # Medium green component
                b < 100 and        # Low blue component
                r > g and g > b    # Red > Green > Blue
            )
            
            # Transparency check (highlight should be semi-transparent)
            is_highlight_transparency = 0.05 <= a <= 0.3
            
            result = is_orange_hue and is_highlight_transparency
            
            if result:
                logger.debug(f"Identified as orange: RGB({r}, {g}, {b}), Alpha: {a}")
            else:
                logger.debug(f"Not orange: RGB({r}, {g}, {b}), Alpha: {a}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check orange color: {str(e)}")
            return False

    def is_green_color(self, color: str) -> bool:
        """
        Check if color string represents green color
        
        Args:
            color: Color string, e.g. "rgba(255, 121, 26, 0.1)"
            
        Returns:
            bool: True if color is green, False otherwise
        """
        try:
            pattern = r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)'
            match = re.search(pattern, color)
            
            if not match:
                logger.debug(f"Cannot parse RGBA: {color}")
                return False
            
            r, g, b, a = map(float, match.groups())
            
            # Green color characteristics
            # Low red component (<100)
            # High green component (100-255)
            # Low to medium blue component (<150)
            is_green_hue = (
                r < 100 and         # Low red component
                100 <= g <= 255 and   # High green component
                b < 150 and         # Low to medium blue component
                g > r and g > b    # Green > Red and Green > Blue
            )
            
            # Transparency check (should be somewhat transparent for highlights)
            is_highlight_transparency = 0.05 <= a <= 0.3
            
            result = is_green_hue and is_highlight_transparency
            
            if result:
                logger.debug(f"Identified as green: RGB({r}, {g}, {b}), Alpha: {a}")
            else:
                logger.debug(f"Not green: RGB({r}, {g}, {b}), Alpha: {a}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check green color: {str(e)}")
            return False

    def is_red_color(self, color: str) -> bool:
        """
        Check if color string represents red color
        
        Args:
            color: Color string, e.g. "rgba(255, 0, 0, 0.1)"
            
        Returns:
            bool: True if color is red, False otherwise
        """
        try:
            pattern = r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)'
            match = re.search(pattern, color)
            
            if not match:
                logger.debug(f"Cannot parse RGBA: {color}")
                return False
            
            r, g, b, a = map(float, match.groups())
            
            # Red color characteristics
            # High red component (200-255)
            # Low green component (<100)
            # Low blue component (<100)
            is_red_hue = (
                r >= 200 and         # High red component
                g < 100 and           # Low green component
                b < 100               # Low blue component
            )
            
            # Transparency check (should be somewhat transparent for highlights)
            is_highlight_transparency = 0.05 <= a <= 0.3
            
            result = is_red_hue and is_highlight_transparency
            
            if result:
                logger.debug(f"Identified as red: RGB({r}, {g}, {b}), Alpha: {a}")
            else:
                logger.debug(f"Not red: RGB({r}, {g}, {b}), Alpha: {a}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check red color: {str(e)}")
            return False

    def is_gray_color(self, color: str) -> bool:
        """
        Check if color string represents gray color
        
        Args:
            color: Color string, e.g. "rgba(128, 128, 128, 0.1)"
            
        Returns:
            bool: True if color is gray, False otherwise
        """
        try:
            pattern = r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)'
            match = re.search(pattern, color)
            
            if not match:
                logger.debug(f"Cannot parse RGBA: {color}")
                return False
            
            r, g, b, a = map(float, match.groups())
            
            # Gray color characteristics
            # All RGB components are similar (within 20-30 range)
            # This covers light gray to dark gray
            color_diff = max(r, g, b) - min(r, g, b)
            is_gray_hue = color_diff <= 30
            
            # Transparency check (should be somewhat transparent for highlights)
            is_highlight_transparency = 0.05 <= a <= 0.3
            
            result = is_gray_hue and is_highlight_transparency
            
            if result:
                logger.debug(f"Identified as gray: RGB({r}, {g}, {b}), Alpha: {a}")
            else:
                logger.debug(f"Not gray: RGB({r}, {g}, {b}), Alpha: {a}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check gray color: {str(e)}")
            return False

    def check_background_color(self, locator: Locator, element_index: int = 0, color_type: str = "orange") -> bool:
        """
        Generic method to check if element has specific background color
        
        Args:
            locator: Playwright Locator object
            element_index: Element index, default 0
            color_type: Type of color to check ("orange", "green", "red", "gray")
            
        Returns:
            bool: True if element matches the specified color type
        """
        try:
            bg_color = self.get_background_color(locator, element_index)
            
            if not bg_color:
                logger.debug(f"No background color retrieved for {color_type} check")
                return False
            
            logger.debug(f"Checking if color is {color_type}: {bg_color}")
            
            # Route to appropriate color check method
            if color_type.lower() == "orange":
                return self.is_orange_color(bg_color)
            elif color_type.lower() == "green":
                return self.is_green_color(bg_color)
            elif color_type.lower() == "red":
                return self.is_red_color(bg_color)
            elif color_type.lower() == "gray":
                return self.is_gray_color(bg_color)
            else:
                logger.warning(f"Unknown color type: {color_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check {color_type} background: {str(e)}")
            return False

    # Convenience wrapper methods
    def is_orange_background(self, locator: Locator, element_index: int = 0) -> bool:
        """Check if element has orange background color"""
        return self.check_background_color(locator, element_index, "orange")
    
    def is_green_background(self, locator: Locator, element_index: int = 0) -> bool:
        """Check if element has green background color"""
        return self.check_background_color(locator, element_index, "green")
    
    def is_red_background(self, locator: Locator, element_index: int = 0) -> bool:
        """Check if element has red background color"""
        return self.check_background_color(locator, element_index, "red")
    
    def is_gray_background(self, locator: Locator, element_index: int = 0) -> bool:
        """Check if element has gray background color"""
        return self.check_background_color(locator, element_index, "gray")

    def get_status_info(self, timeout: int = 30000) -> str:
        self.page.wait_for_timeout(3000)
        status_info = self.find_element(selector='.sw-status-info', timeout=timeout)
        
        if status_info.count() == 0:
            logger.warning("Status info not found")
            return ""
        
        logger.info(f"Status info: {status_info.inner_text()}")
        return status_info.inner_text()
    
    def get_confirmation_dialog(self, timeout: int = 5000) -> Locator:
        """Check if confirmation dialog with specific title exists"""
        dialog_selector = f".sw-confirm-modal__dialog"
        dialog_locator = self.find_element(selector=dialog_selector, timeout=timeout)
        
        if dialog_locator.count() == 0:
            logger.warning("Confirmation dialog not found")
            return self.page.locator('__not_found__')
        
        logger.info("Confirmation dialog found")
        return self.page.locator(dialog_selector)
        
    def click_dialog_button(self, button_name: str) -> bool:
        try:
            dialog_locator = self.get_confirmation_dialog()
            if dialog_locator.count() == 0:
                return False
                
            button = dialog_locator.locator(f".sw-button:has-text('{button_name}')")
            button.wait_for(state="visible", timeout=5000)
            logger.info(f"Click confirmation dialog button: {button_name}")
            button.click()
            logger.info(f"Successfully clicked confirmation dialog button: {button_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to click confirmation dialog button: {e}")
            return False
    
    def get_info_from_confirmation_dialog(self, timeout: int = 5000) -> str:
        confirm_locator = self.get_confirmation_dialog(timeout)
        if confirm_locator.count() == 0:
            return ""
        
        logger.info("Extracting info from confirmation dialog")
        info_text = confirm_locator.inner_text()
        return info_text
        
    def get_top_message(self, timeout: int = 5000):
        top_message = self.find_element(selector='div.sw-message-container', timeout=timeout)
        
        if top_message.count() == 0:
            logger.warning("Top message not found")
            return ""
        return top_message.inner_text()