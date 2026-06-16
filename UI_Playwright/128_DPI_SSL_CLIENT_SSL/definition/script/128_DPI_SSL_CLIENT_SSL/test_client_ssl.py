from config.settings import *
from config.logger import get_logger

logger = get_logger(__name__)
"""Get a named logger"""

pytestmark = pytest.mark.auto_login(cache_key=__name__)

class TestClientSSL:
    """Client SSL Test Cases"""

    def test_navigate_to_client_ssl(self, fw_page):
        """Navigate to Client SSL Page"""
        logger.info("Navigating to Client SSL Page")
        fw_page.dpi_ssl_client_ssl.navigate_to_client_ssl()
        assert "client-ssl" in fw_page.page.url, 'Failed to navigate to Client SSL Page'
    
    @pytest.mark.parametrize("uuid, toggle_name", [
        ("SOSAIOT-TC-95316", "Enable SSL Client Inspection"),
        ("SOSAIOT-TC-95317", "Intrusion Prevention"),
        ("SOSAIOT-TC-95318", "Gateway Anti-Virus"),
        ("SOSAIOT-TC-95319", "Gateway Anti-Spyware"),
        ("SOSAIOT-TC-95320", "Application Firewall"),
        ("SOSAIOT-TC-95321", "Content Filter"),
        ("SOSAIOT-TC-95322", "Always authenticate server for decrypted connections"),
        ("SOSAIOT-TC-95326", "Deployments wherein the Firewall sees a single server IP for different server domains, ex: Proxy setup"),
        ("SOSAIOT-TC-95328", "Allow SSL without decryption (bypass) when connection limit exceeded"),
        ("SOSAIOT-TC-95330", "Audit new default exclusion domain names prior to being added for exclusion"),
        ("SOSAIOT-TC-95332", "Always authenticate server before applying exclusion policy")
        ])
    def test_toggles_enable_disable(self, fw_page, uuid, toggle_name):
        """Test toggling options on Client SSL Page"""
        logger.info(f"STEP - Testing Enable toggle '{toggle_name}'......")
        # Example toggle actions
        selector = fw_page.dpi_ssl_client_ssl.TOGGLES.get(toggle_name)
        fw_page.dpi_ssl_client_ssl.click_toggle(selector=selector, enable=True)
        assert fw_page.get_toggle_status(selector) == "1", f"Failed to enable {toggle_name} on Client SSL page"
        
        logger.info(f"STEP - Testing Disable toggle '{toggle_name}'......")
        fw_page.dpi_ssl_client_ssl.click_toggle(selector=selector, enable=False)
        assert fw_page.get_toggle_status(selector) == "0", f"Failed to disable {toggle_name} onClient SSL page"

    @pytest.mark.parametrize("uuid", ["SOSAIOT-TC-95324"])
    def test_enable_disable_Allow_Expired_CA(self, fw_page, uuid):
        """Test toggling options on Client SSL Page"""
        toggle_name = "Allow Expired CA"
        parent_toggle_name = "Always authenticate server for decrypted connections"
        
        logger.info(f"STEP - Enable parent toggle '{parent_toggle_name}'......")        
        parent_selector = fw_page.dpi_ssl_client_ssl.TOGGLES.get(parent_toggle_name)
        fw_page.dpi_ssl_client_ssl.click_toggle(selector=parent_selector, enable=True)

        logger.info(f"STEP - Enable toggle '{toggle_name}'......")        
        selector = fw_page.dpi_ssl_client_ssl.TOGGLES.get(toggle_name)
        fw_page.dpi_ssl_client_ssl.click_toggle(selector=selector, enable=True)
        assert fw_page.get_toggle_status(selector) == "1", f"Failed to enable {toggle_name} on Client SSL page"
        
        logger.info(f"STEP - Disable toggle '{toggle_name}'......")
        fw_page.dpi_ssl_client_ssl.click_toggle(selector=selector, enable=False)
        assert fw_page.get_toggle_status(selector) == "0", f"Failed to disable {toggle_name} onClient SSL page"

    @pytest.mark.parametrize("uuid, toggle_name, tooltip", [
        ("SOSAIOT-TC-95323", "Always authenticate server for decrypted connections", "For decrypted/intercepted connections, DPI-SSL will: Block connections to sites with untrusted certificates. Block connection if the domain name in Client Hello cannot be validated against the Server Certificate for this connection"),
        ("SOSAIOT-TC-95325", "Allow Expired CA", "Allow Expired CA or Intermediate CA."),
        ("SOSAIOT-TC-95327", "Deployments wherein the Firewall sees a single server IP for different server domains, ex: Proxy setup", "Disable usage of server IP address based dynamic cache for exclusion."),
        ("SOSAIOT-TC-95329", "Allow SSL without decryption (bypass) when connection limit exceeded", "Allow SSL without decryption (bypass) when connection limit exceeded. When disabled, new connections are dropped when the connection limit is exceeded."),
        ("SOSAIOT-TC-95331", "Audit new default exclusion domain names prior to being added for exclusion", "Audit new built-in exclusion domain names prior to being added for exclusion"),
        ("SOSAIOT-TC-95333", "Always authenticate server before applying exclusion policy", "For excluded connections, DPI-SSL will: Block connections to sites with untrusted certificates Block connection if the domain name in Client Hello cannot be validated against the Server Certificate for this connection")
        ])
    def test_toggles_tooltip(self, fw_page, uuid, toggle_name, tooltip):
        """Test toggling options on Client SSL Page"""
        logger.info(f"STEP - Mouse hover on the tooltip of toggle '{toggle_name}'......")        
        selector = fw_page.dpi_ssl_client_ssl.TOGGLES.get(toggle_name)
        fw_page.mouse_hover(f".sw-toggle:has({selector}) ~ .sw-icon")
        
        logger.info(f"STEP - Check the tooltip details......")
        detail = fw_page.get_text(fw_page.dpi_ssl_client_ssl.TOGGLE_TOOLTIP)
        logger.info(f"Tooltip detail:   {detail}")
        fw_page.page.mouse.move(0, 0)  # Move mouse away to hide tooltip
        assert tooltip in detail, f"Failed to disable {toggle_name} onClient SSL page"
