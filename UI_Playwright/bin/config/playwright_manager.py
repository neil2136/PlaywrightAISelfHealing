# core/playwright_manager.py - Playwright Manager
from typing import Optional
from playwright.sync_api import Browser, BrowserContext, Page
from config.settings import Settings
from config.logger import get_logger

logger = get_logger('playwright_manager')


class PlaywrightManager:
    """Playwright Manager"""

    def __init__(self, playwright, browser_type: str = "chromium", headless: bool = True):
        self.browser_type = browser_type
        self.headless = headless
        self.playwright = playwright
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self):
        """Start Playwright and launch the browser"""
        logger.info(f"Launching Playwright - Browser: {self.browser_type}")

        # Get browser configuration
        browser_config = Settings.BROWSERS.get(self.browser_type, {})

        # Start browser
        browser_launcher = getattr(self.playwright, self.browser_type)
        self.browser = browser_launcher.launch(
            headless=self.headless,
            args=browser_config.get("args", []),
            slow_mo=browser_config.get("slow_mo", 0)
        )

        logger.info("Playwright Launched Successfully!")
        logger.info(f"headless: {self.headless}")

    def create_context(self, **kwargs):
        """Create a new browser context"""
        context_args = {
            "ignore_https_errors": True,
            "java_script_enabled": True,
        }
        context_args.update(kwargs)
        self.context = self.browser.new_context(**context_args)

        # Start tracing if necessary
        if kwargs.get('trace'):
            self.context.tracing.start(  # type: ignore
                screenshots=True,
                snapshots=True,
                sources=True
            )

        logger.info("Created Browser Context")
        return self.context

    def create_page(self):
        """Create a new page in the browser context"""
        if not self.context:
            self.create_context()

        self.page = self.context.new_page()

        # Configure default timeout
        self.page.set_default_timeout(Settings.DEFAULT_TIMEOUT * 1000)

        logger.info("Created New Page...")
        return self.page

    def close(self):
        """Clean up Playwright resources"""
        if self.page:
            self.page.close()
            logger.debug("Close Page")

        if self.context:
            self.context.close()
            logger.debug("Close Browser Context")

        if self.browser:
            self.browser.close()
            logger.debug("Close Browser")

        if self.playwright:
            self.playwright.stop()
            logger.info("Playwright Stopped")
