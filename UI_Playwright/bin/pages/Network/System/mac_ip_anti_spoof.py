from pages.base_page import *

logger = get_logger('mac_ip_anti_spoof_page')

class MacIpAntiSpoof(BasePage):
    CONTAINER_SETTINGS = 'fw-mgmt-ftr-network-mac-ip-anti-spoof__panel-form'
    CONTAINER_CACHE = 'fw-mgmt-ftr-network-mac-ip-anti-spoof__panel'
    CONTAINER_SPOOF = 'fw-mgmt-ftr-network-mac-ip-anti-spoof__panel'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '/m/mgmt/network/mac-ip-anti-spoof'

    def navigate_to_mac_ip_anti_spoof(self):
        self.navigate_to_url(self.url)