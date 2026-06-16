# pages/login_page.py, Page Methods for Login Page
from pages.base_page import *

logger = get_logger('login_page')


class LoginPage(BasePage):
    # Element locators
    USERNAME_INPUT = "input[name='username']"
    PASSWORD_INPUT = "input[name='password']"
    # OLD_USERNAME_INPUT = "input[name='oldPw']"
    # NEW_PASSWORD_INPUT = "input[name='newPw']"
    # CONFIRM_PASSWORD_INPUT = "input[name='confirmPw']"
    LOGIN_BUTTON = "text=LOG IN"
    CONTINUE_BUTTON = "text=Continue"
    CONFIG_BUTTON = "button[text='Config']"
    LAUNCH_SCREEN_CONTAINER = ".fw-mgmt-launch-screen__bottom-container"
    MANUAL_CONFIGURE_LINK = ".fw-mgmt-launch-screen__info-text div:nth-of-type(2) a"
    PREEMPT_LINE = ".login-ftr-preempt__line .sw-typo-heading-4"
    MAIN_PAGE = ".fw-app-content"
    
    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '/login'

    def navigate_to_login_page(self):
        """navigate to login page"""
        self.navigate_to_url(self.url)

    def login(self, username='admin', password=Settings.PASSWORD):
        # logger.info('Click accept button')
        # self.click('text=I Accept')
        logger.info(f'Login FW with user name: {username}')
        self.fill(self.USERNAME_INPUT, username)
        logger.info(f'Fill user password: {password}')
        self.fill(self.PASSWORD_INPUT, password)
        logger.info('Click login button')
        self.click(self.LOGIN_BUTTON)

        if self.is_element_visible(self.LAUNCH_SCREEN_CONTAINER):
            logger.info('Get launch screen container and click manual configure link')
            self.click(self.MANUAL_CONFIGURE_LINK)

        try:
            self.page.get_by_role("button", name='Config', exact=True).wait_for(state='visible', timeout=5000)
            logger.info('Preempt to config mode')
            self.click_button('Config')
        except:
            pass
        
        try:
            self.page.get_by_role("button", name='Proceed', exact=True).wait_for(state='visible', timeout=5000)
            logger.info('Proceed to config mode')
            self.click_button('Proceed')           
        except:
            pass


        logger.info('Wait for main page to load......')
        self.wait_for_selector(self.MAIN_PAGE, timeout=30000)
   
        res = self.is_login_successful()
        logger.info(f'Check login status......{res}')

        if not res:
            error_msg = self.get_error_message()
            logger.error(f'Login failed with error message: {error_msg}')
        
        return res

    def get_error_message(self) -> str:
        """Get login error message"""
        return self.get_text(self.STATUS_MESSAGE)
    
    def is_login_successful(self) -> bool:
        """Check login status"""
        return "/dashboard" in self.page.url