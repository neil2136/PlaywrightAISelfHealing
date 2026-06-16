# pages/fw_page.py, Firewall pages manager class for accessing different page objects 
from pages.base_page import *
from pages.Object.Match_Objects.Addresses import Addresses
from pages.Policy.DPI_SSL.Client_SSL import Client_SSL
from pages.Network.System.interface import Interface
from pages.Network.System.arp import ARP
from pages.Network.System.mac_ip_anti_spoof import MacIpAntiSpoof
from pages.Network.System.web_proxy import WebProxy

from pages.login_page import LoginPage


class FWPage(BasePage):
    """Firewall pages manager class for accessing different page objects"""
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page
        self._pages = {}  # Page instance cache
    
    # ========== Page Objects Accessor ==========
    
    @property
    def login(self):
        """Access all methods of  LoginPage"""
        if 'login' not in self._pages:
            self._pages['login'] = LoginPage(self.page)
        return self._pages['login']

    @property
    def match_objects_accesses(self):
        """Access all methods of Match_Objects.Addresses pages"""
        if 'match_objects_accesses' not in self._pages:
            self._pages['match_objects_accesses'] = Addresses(self.page)
        return self._pages['match_objects_accesses']

    @property
    def dpi_ssl_client_ssl(self):
        """Access all methods of Match_Objects.Addresses pages"""
        if 'dpi_ssl_client_ssl' not in self._pages:
            self._pages['dpi_ssl_client_ssl'] = Client_SSL(self.page)
        return self._pages['dpi_ssl_client_ssl']

    @property
    def arp(self):
        """Access all methods of ARP pages"""
        if 'arp' not in self._pages:
            self._pages['arp'] = ARP(self.page)
        return self._pages['arp']

    @property
    def interface(self):
        """Access all methods of Interface pages"""
        if 'interface' not in self._pages:
            self._pages['interface'] = Interface(self.page)
        return self._pages['interface']

    @property
    def mac_ip_anti_spoof(self):
        """Access all methods of MacIpAntiSpoof pages"""
        if 'mac_ip_anti_spoof' not in self._pages:
            self._pages['mac_ip_anti_spoof'] = MacIpAntiSpoof(self.page)
        return self._pages['mac_ip_anti_spoof']

    @property
    def web_proxy(self):
        """Access all methods of Web Proxy pages"""
        if 'web_proxy' not in self._pages:
            self._pages['web_proxy'] = WebProxy(self.page)
        return self._pages['web_proxy']


