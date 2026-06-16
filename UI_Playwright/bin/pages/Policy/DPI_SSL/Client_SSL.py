# pages/Policy/DPI_SSL/Client_SSL.py, Page Methods for Client_SSL Page
from pages.base_page import *

logger = get_logger('client_ssl_page')


class Client_SSL(BasePage):
    ADD_BUTTON = '.icon-add'
    NAME_INPUT = 'input[name="name"]'
    ZONE_DROPDOWN = 'input[name="zoneAssignment"]'
    TYPE_DROPDOWN = 'input[name="type"]'
    IP_INPUT = 'input[name="ip-address"]'
    SAVE_BUTTON = 'text=Save'
    TOGGLES = {
        "Enable SSL Client Inspection": "input[name='enable-ssl-inspection']",
        "Intrusion Prevention": "input[name='intrusion-prevention']",
        "Gateway Anti-Virus": "input[name='gateway-antiVirus']",
        "Gateway Anti-Spyware": "input[name='gateway-antiSpyware']",
        "Application Firewall": "input[name='application-firewall']",
        "Content Filter": "input[name='content-filter']",
        "Always authenticate server for decrypted connections": "input[name='authServer-decryptedConnections']",
        "Allow Expired CA": "input[name='allow-expired-ca']",
        "Deployments wherein the Firewall sees a single server IP for different server domains, ex: Proxy setup": "input[name='deployment']",
        "Allow SSL without decryption (bypass) when connection limit exceeded": "input[name='ssl-without-decryption']",
        "Audit new default exclusion domain names prior to being added for exclusion": "input[name='default-exclusion']",
        "Always authenticate server before applying exclusion policy": "input[name='auth-server-exclusion']",
    }
    TOGGLE_TOOLTIP = '.sw-popover__board__content__inner'


    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + "/m/mgmt/dpi-ssl/client-ssl"
    
    def navigate_to_client_ssl(self):
        self.navigate_to_url(self.url)

    # def navigate_to_client_ssl_general_tab(self):
    #     self.navigate_to_main_tab('General')