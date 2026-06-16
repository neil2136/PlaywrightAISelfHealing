# conftest.py - Global pytest configuration and fixtures
from pages.fw_pages import FWPage
from pages.login_page import LoginPage
from config.logger import get_logger
from config.settings import *
from config.playwright_manager import PlaywrightManager
from config.csv_reporter import CSVReporter

logger = get_logger("conftest")

# ==================== pytest configure hook ====================
def pytest_addoption(parser):
    """Add custom command-line options to pytest"""
    parser.addoption(
        "--csv_file",
        action="store",
        help="CSV File Path"
    )
    parser.addoption(
        "--log_file",
        action="store",
        help="Log file path"
    )
    parser.addoption(
        "--password",
        action="store",
        default="S0nic@uto",
        help="Login password"
    )
    parser.addoption(
        "--fw_ip",
        action="store",
        default="192.168.168.168",
        help="Firewall IP of DUT"
    )


def pytest_configure(config):
    """pytest configure hook"""

    # Register custom markers
    markers = {
        "auto_login": "Auto Login marker, when use this marker, the page object with successful login will be automatically injected.",
    }
    
    for marker, description in markers.items():
        config.addinivalue_line("markers", f"{marker}: {description}")
    
    # Get CSV file path
    csv_file_path = config.getoption("--csv_file")
    if csv_file_path:
        csv_file_path = Path(csv_file_path)
    else:
        # Default CSV file path
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file_path = reports_dir / f"test_results_{timestamp}.csv"
    
    # Initialize CSV Reporter
    config._csv_reporter = CSVReporter(csv_file_path)

    logger.info("=" * 80)
    logger.info("pytest configuration completed")
    logger.info(f"Browser Type: {config.getoption('--browser')}")
    logger.info("=" * 80)


def pytest_sessionstart(session):
    """test session start"""
    logger.info("Test session started...")

def pytest_sessionfinish(session, exitstatus):
    """test session finish"""
    logger.info(f"Test session finished. Exit status: {exitstatus}")
    
    # show csv summary statistics
    if hasattr(session.config, '_csv_reporter'):
        csv_reporter = session.config._csv_reporter
        csv_file = csv_reporter.csv_file_path
        if csv_file.exists():
            csv_reporter.show_summary_statistics(csv_file)


# ==================== self-defined fixture ====================
@pytest.fixture(scope="session")
def csv_file(request):
    """record result to csv file fixture"""
    return request.config.getoption("--csv_file")

@pytest.fixture(scope="session")
def log_file(request):
    """record result to log file fixture"""
    return request.config.getoption("--log_file")

@pytest.fixture(scope="session", autouse=True)
def test_password(request):
    """set login password fixture"""
    pwd = request.config.getoption("--password")
    if pwd:
        Settings.PASSWORD = pwd
    logger.info(f"Login password: {Settings.PASSWORD}")
    return Settings.PASSWORD

@pytest.fixture(scope="session", autouse=True)
def test_fw_url(request):
    """set Firewall IP of DUT fixture"""
    ip = request.config.getoption("--fw_ip")
    if ip:
        Settings.FIREWALL_IP = ip
        Settings.BASE_URL = f"https://{ip}/sonicui/7"
    logger.info(f"Firewall IP of DUT: {Settings.FIREWALL_IP}")
    return Settings.BASE_URL

@pytest.fixture(scope="session")
def browser(request):
    """browser type fixture"""
    browser = request.config.getoption("--browser")
    return browser.pop() if isinstance(browser, list) else browser

@pytest.fixture(scope="session")
def csv_reporter(request):
    """CSV Reporter fixture"""
    return request.config._csv_reporter

@pytest.fixture(scope="session")
def playwright_manager(playwright, browser, request):
    """Playwright Manager fixture"""
    headless = not request.config.getoption("--headed")  # Default to headless mode unless --headed is specified
    manager = PlaywrightManager(
        playwright,
        browser_type=browser,
        headless=headless
    )
    
    try:
        manager.start()
        yield manager
    finally:
        manager.close()


@pytest.fixture(scope="module", autouse=True)
def browser_context(playwright_manager):
    """browser context fixture"""
    context = playwright_manager.create_context()
    
    yield context

@pytest.fixture(scope="module", autouse=True)
def page(browser_context):
    """page fixture"""
    page = browser_context.new_page()
    
    yield page
    
    # Close page
    if not page.is_closed():
        page.close()


_login_cache: Dict[str, Any] = {}
def create_logged_in_page(test_page, cache_key = "default", username = Settings.USERNAME, password = Settings.PASSWORD) -> LoginPage:
    """Create a logged-in page"""
    # Check if login status is cached
    if cache_key in _login_cache:
        logger.info(f"Using cached login status: {cache_key}")
        return _login_cache[cache_key]
    
    # Create new login page
    login_page = LoginPage(test_page)
    # Run auto login
    try:
        login_page.navigate_to_login_page()
        success = login_page.login(username, password)
    except Exception as e:
        logger.error(f"Auto login failed: {e}")
        success = False
    
    if not success:
        raise ValueError("Auto login failed!")
    
    # Cache login status
    _login_cache[cache_key] = login_page
    return login_page

    # del _login_cache[cache_key]


@pytest.fixture(scope="module")
def auto_login(request, page):
    """
    auto login fixture, module level
    Auto login only triggered when @pytest.mark.auto_login is used
    """
    # Check for auto_login marker
    marker = request.node.get_closest_marker("auto_login")
    kwargs = marker.kwargs if marker else {}

    if marker is None:
        # Check for auto_login marker in parent
        if hasattr(request.node, 'parent') and request.node.parent is not None:
            marker = request.node.parent.get_closest_marker("auto_login")
            logger.info(f"Found auto_login marker in parent: {marker}")

    if not marker:
        # if no marker, return the original page
        logger.info("No auto_login marker found, returning original page")
        return page
    
    # Generate cache key based on marker arguments
    cache_key = kwargs.get("cache_key", "default")
    username = kwargs.get("username", Settings.USERNAME)
    password = kwargs.get("password", Settings.PASSWORD)
    
    logger.info(f"Auto Login Fixture triggered for cache_key: {cache_key}, username: {username}, password: {password}")
    login_page = create_logged_in_page(page, cache_key, username, password)
    # Return the logged-in page
    return login_page.page


# @pytest.fixture(scope="module", autouse=True)
# def fw_page(auto_login, url):
#     """fixture for FWPage"""
#     logger.info(f"FWPage fixture triggered for url: {url}")
#     fw_page = FWPage(auto_login)
#     fw_page.navigate_to_url(Settings.BASE_URL + url)
#     yield fw_page
#     # return fwpage
@pytest.fixture(scope="module", autouse=True)
def fw_page(auto_login):
    """fixture for FWPage"""
    return FWPage(auto_login)




def extract_uuid(item) -> str:
    """extract UUID from test item"""
    # extract uuid from arguments in test item
    if hasattr(item, "callspec"):
        params = item.callspec.params
        # Find 'uuid' key in params
        for key, value in params.items():
            if key.lower() == "uuid":
                return value
    
    # extract uuid from test class attribute
    if hasattr(item, 'cls') and item.cls:
        # Check if the class has a uuid attribute
        if hasattr(item.cls, 'uuid'):
            uuid_value = item.cls.uuid
            if isinstance(uuid_value, str) and len(uuid_value) >= 4:
                return uuid_value
    
    # extract uuid from test name pattern
    test_name = item.cls.__name__
    match = re.search(r'SOSAIOT_TC_\d{5,}', test_name)
    if match:
        uuid = match.group().replace('_', '-')
        return uuid
    
    return "N/A"


# ==================== Test Result Collection Hook ====================
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    """
    Print START/END log message before and after each test, only once per test
    """
    uuid = extract_uuid(item)
    logger.info(f'----- Test case {uuid} START --------------------------------')
    
    # Run the actual test
    outcome = yield

    logger.info(f'----- Test case {uuid} END --------------------------------\n')
    return outcome


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item):
    """Collect test results"""
    # Extract UUID for the test item
    uuid = extract_uuid(item)
    outcome = yield
    report = outcome.get_result()
    
    # Only handle the 'call' phase
    if report.when == "call":
        item.rep_call = report
        
        # Take screenshot on failure
        if report.failed and "page" in item.fixturenames:
            page = item.funcargs["page"]
            try:
                screenshot_dir = Settings.SCREENSHOTS_DIR / "failures"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%H%M%S")
                screenshot_file = screenshot_dir / f"{uuid}_{timestamp}.png"
                
                page.screenshot(path=str(screenshot_file))
                logger.info(f"Failure Screenshot saved: {screenshot_file}")
            except Exception as e:
                logger.error(f"Failed to save screenshot: {e}")

        # Record test result to CSV
        item.config._csv_reporter.record_test_result({
            "uuid": uuid,
            "status":'passed' if report.passed else 'failed' if report.failed else 'skipped',
            "error_message": str(report.longrepr) if report.failed else "",
        })
