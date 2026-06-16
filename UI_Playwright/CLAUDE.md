# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Playwright-based pytest UI automation framework for testing a SonicWall firewall web UI (SonicOS 7). The framework root is `bin/` — all test execution, configuration, and most test code live there. Feature directories like `112_Network_Interfaces/`, `128_DPI_SSL_CLIENT_SSL/`, etc. at the repo root contain test plans, definitions, and legacy suite code that are NOT the primary test entry points. Always work from `bin/`.

## Commands

```bash
# Run all tests
python3 bin/run_tests.py

# Run a specific test file or directory
python3 bin/run_tests.py -t bin/tests/test_example.py

# Run with a mark filter
python3 bin/run_tests.py -m auto_login

# Run with a keyword expression
python3 bin/run_tests.py -k login

# Common options
python3 bin/run_tests.py --browser chromium --headed --slowmo 500
python3 bin/run_tests.py --retries 2 --timeout 60
python3 bin/run_tests.py --fw_ip 10.0.0.1 --password mypassword
python3 bin/run_tests.py --dry_run            # collect-only mode
python3 bin/run_tests.py --debug              # verbose DEBUG logging
```

The runner (`run_tests.py`) builds a pytest command and executes it with `cwd=bin/`. `Settings.ROOT_DIR` is set to `bin/` in `bin/config/settings.py`.

### AI-assisted test generation pipeline (two-step)

This is the framework's core innovation — automate page object and test case generation from a live firewall page.

```bash
# Step 1: Extract page skeleton from a live firewall page
python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --fw_ip 10.8.165.150 --headed
# Output: bin/test_data/page_structure/arp_structure.json

# Step 1 (alt): Interactive manual capture mode — user clicks UI, press Enter to snapshot
python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --headed --manual

# Step 2: Feed skeleton to GLM AI → generate Page Object + tests + CSV
python3 bin/tools/generate_tests.py --feature arp

# Connectivity diagnostic (if GLM API calls fail)
python3 bin/tools/check_connectivity.py
```

`page_inspector.py` automatically explores the target page: extracts breadcrumb, tabs (L1/L2), tables (headers, row identifiers, column types, footer counters), toolbar buttons, page-level dropdowns, and then safely clicks "Add" type buttons to open and extract modal/popover dialogs (forms, fields, snaphot HTML) — closing them with Cancel afterward. Row-hover action buttons and row-click dialogs are also discovered.

`generate_tests.py` sends the structured JSON to the Zhipu GLM API (`zai` SDK) with a comprehensive system prompt (`SYSTEM_PROMPT` in the script) that generates 4 outputs:
- CSV test cases (`bin/test_data/manual_testcases/SonicWall_{FEATURE}_Test_Cases.csv`)
- Page Object (`bin/pages/{subdir}/{feature}.py`)
- Test file (`bin/tests/test_{number}_{feature}.py`)
- `fw_pages.py` update snippet (import + @property)

The API key is hardcoded in the script or passed via `--api-key`. Model default: `glm-5.1`.

## Architecture

### Execution flow

1. `run_tests.py` — CLI entry point; builds a pytest command from CLI args, runs via `subprocess.run(cwd=bin/…)`
2. `pytest.ini` — declares test discovery rules (`test_*.py`, `Test*` classes, `test_*` functions) and custom markers
3. `conftest.py` — pytest hooks and fixtures (browser lifecycle, auto-login, CSV reporting, screenshots)
4. Test files under `bin/tests/` use the `fw_page` fixture (and optionally `auto_login`) to interact with the firewall UI

### Key fixtures (defined in `conftest.py`)

- **`playwright_manager`** (session) — launches/closes Playwright browser via `bin/config/playwright_manager.py`
- **`browser_context`** (module, autouse) — creates a new browser context per test module
- **`page`** (module, autouse) — creates a fresh Playwright `Page` per module
- **`auto_login`** (module) — triggered only when `@pytest.mark.auto_login` is present; performs login, caches the logged-in page by `cache_key`, and returns the logged-in `Page`. Without the marker, returns the raw (unauthenticated) page
- **`fw_page`** (module, autouse) — wraps the `Page` in an `FWPage` object, the main page facade

### Login flow

`LoginPage.login()` handles the full SonicOS 7 login sequence automatically:
1. Fill username + password, click "LOG IN"
2. If the "launch screen" container appears (first-time setup), click "Manual Configure" link
3. If a "Config" button appears (preempt mode prompt), click it
4. If a "Proceed" button appears (warning dialog), click it
5. Wait for main page (`.fw-app-content`) to load
6. Return success/failure based on whether URL contains `/dashboard`

All of this is transparent to tests — they just use `pytestmark = pytest.mark.auto_login(cache_key="feature_name")`.

### `auto_login` cache_key behavior

The `cache_key` parameter on `@pytest.mark.auto_login` controls session caching. Tests with the same `cache_key` share a single logged-in browser context across modules. Tests with different `cache_key` values get separate login sessions. This allows isolation between feature modules while avoiding redundant logins within a module.

### Page Object Model

- **`BasePage`** (`bin/pages/base_page.py`) — ~1500 lines of reusable UI interaction methods, organized into:
  - **Basic ops**: `navigate_to_url`, `click`, `fill`, `get_text`, `get_element`, `get_element_by_text`
  - **Navigation**: `navigate_to_Top_tab`, `navigate_to_left_level_1_tab`, `navigate_to_main_tab`
  - **Wait**: `wait_for_selector`, `wait_for_load_state`, `wait_for_load_page`, `is_element_visible`
  - **Toggle/Checkbox/Radio**: `click_toggle`, `click_checkbox_by_input_name`, `click_radio_button_by_input_name`, `set_toggle_by_locator`
  - **Dropdown**: `select_value_in_dropdown_box` (by label), `select_value_in_dropdown_box_use_input_name` (by input name), `get_drop_down_list_values`
  - **Table**: `get_table_header`, `get_table_row_count_by_container`, `extract_table_footer_total_count`, `get_table_row_locator`, `get_table_row_text`
  - **Tab management**: `switch_tab`, `is_tab_active`, `get_active_tab`
  - **Dialog/Modal**: `get_confirmation_dialog`, `click_dialog_button`, `click_diag_button`, `click_close_icon_by_window_title`
  - **Status/Message**: `compare_status_message`, `accept_alert`, `verify_status_message`, `get_status_info`
  - **Color verification**: `is_orange_background`, `is_green_background`, `is_red_background`, `is_gray_background`, `check_background_color`
  - **Search**: `get_search_box_locator`, `fill_search_box`
  - **Button dropdowns**: `select_value_from_button_dropdown`, `get_values_from_button_dropdown`
  - **Flexible element finding**: `find_element` / `click_element` / `fill_input` / `fill_input_by_label_name` — unified API that resolves elements by text, selector, role, name, placeholder, or label
- **`LoginPage(BasePage)`** (`bin/pages/login_page.py`) — login flow with Config mode auto-handling
- **`FWPage(BasePage)`** (`bin/pages/fw_pages.py`) — facade that lazily instantiates and caches sub-page objects:
  - `.interface` → `Interface(BasePage)`
  - `.dpi_ssl_client_ssl` → `Client_SSL(BasePage)`
  - `.match_objects_accesses` → `Addresses(BasePage)`
  - `.arp` → `ARP(BasePage)`
  - `.mac_ip_anti_spoof` → `MacIpAntiSpoof(BasePage)`
  - `.login` → `LoginPage(BasePage)`
- Feature-specific page objects live in `bin/pages/` mirroring the UI hierarchy (e.g., `bin/pages/Network/System/interface.py`, `bin/pages/Policy/DPI_SSL/Client_SSL.py`, `bin/pages/Object/Match_Objects/Addresses.py`)

### Registering a new page object

When adding a new Page Object, you must update `bin/pages/fw_pages.py`:
1. Add the import at the top (keep grouped by directory, mirroring the UI hierarchy)
2. Add a `@property` that lazily instantiates and caches the page object

```python
from pages.Network.System.new_feature import NewFeature  # import

class FWPage(BasePage):
    @property
    def new_feature(self):                               # property
        if 'new_feature' not in self._pages:
            self._pages['new_feature'] = NewFeature(self.page)
        return self._pages['new_feature']
```

### Configuration

- `bin/config/settings.py` — `Settings` class: paths (`ROOT_DIR=bin/`), defaults (`FIREWALL_IP=192.168.168.168`, `PASSWORD=S0nic@uto`, `USERNAME=admin`), browser config, directory setup on import
- `bin/config/playwright_manager.py` — browser launch, context creation, cleanup; ignores HTTPS errors
- `bin/config/csv_reporter.py` — writes test results (uuid, status, error_message) to CSV
- `bin/config/logger.py` — global logging setup with colored console output + file output
- `bin/test_data/manual_testcases/` — place manual test case CSV files here, organized by feature module
- `bin/test_data/page_structure/` — page skeleton JSON files produced by `page_inspector.py`

### Test conventions

- Tests use class-per-feature with `uuid` class attributes mapping to test case IDs (e.g., `SOSAIOT-TC-94884`)
- Some tests use a `test_all()` pattern that calls sub-methods sequentially within a single test (used for tab switching, IP version switching — anything where multiple steps share the same UUID)
- Other tests use `test_01_`, `test_02_` prefixed methods within a class
- Parameterized tests use `@pytest.mark.parametrize` with UUIDs as parameters
- Module-level `pytestmark = pytest.mark.auto_login` applies auto_login to all tests in a file
- Test class naming: `Test_01_`, `Test_02_`, etc. ordered by CSV row

### Dynamic settings via CLI

`--fw_ip` and `--password` are passed via custom pytest options (registered in `conftest.py`), applied through `autouse` session fixtures that override `Settings.FIREWALL_IP`, `Settings.BASE_URL`, and `Settings.PASSWORD` before any test runs.

#### `--fw_ip` 参数流转时序

Page Object 中**禁止**在类体（class-level）读取 `Settings.BASE_URL`，必须在 `__init__` 中设置。原因是类体在 `import` 时求值，早于 fixture 执行。

```
┌─ 1. Python import 阶段 ───────────────────────────────────────────────────┐
│                                                                           │
│   bin/run_tests.py                                                        │
│        │                                                                  │
│        ├── from config.settings import Settings                           │
│        │   → Settings.FIREWALL_IP = "192.168.168.168"  (默认值)           │
│        │   → Settings.BASE_URL = "https://192.168.168.168/sonicui/7"      │
│        │                                                                  │
│        └── (间接) import pages.* / conftest.py                            │
│                                                                           │
│   ❌ 如果此时执行 URL = Settings.BASE_URL + '/arp'                         │
│       → 字符串固化为 https://192.168.168.168/...，之后无法改变             │
│                                                                           │
├─ 2. pytest 启动阶段 ──────────────────────────────────────────────────────┤
│                                                                           │
│   用户: python3 bin/run_tests.py --fw_ip 10.8.165.150 --headed            │
│                                                                           │
│   run_tests.py 解析 --fw_ip → 传入 pytest: --fw_ip=10.8.165.150           │
│                                                                           │
├─ 3. pytest fixture 执行阶段 (session, autouse) ───────────────────────────┤
│                                                                           │
│   conftest.py::test_fw_url(request)                                       │
│       ip = request.config.getoption("--fw_ip")   # "10.8.165.150"         │
│       Settings.FIREWALL_IP = ip                                           │
│       Settings.BASE_URL = f"https://{ip}/sonicui/7"                       │
│                                ↓                                          │
│   conftest.py::test_password(request)                                     │
│       Settings.PASSWORD = request.config.getoption("--password")          │
│                                                                           │
├─ 4. Page Object 实例化 (测试执行中, 懒加载) ──────────────────────────────┤
│                                                                           │
│   FWPage.arp (第一次访问)                                                 │
│       → ARP(self.page)                                                    │
│       → __init__: self.url = Settings.BASE_URL + '/m/mgmt/network/arp'    │
│                     ↓                                                     │
│         此时 Settings.BASE_URL = "https://10.8.165.150/sonicui/7"  ✅     │
│                                                                           │
│   ✅ __init__ 在步骤4执行 → 读到步骤3更新后的值                            │
│   ❌ 类体 在步骤1执行 → 读到默认值，固化                                    │
└───────────────────────────────────────────────────────────────────────────┘
```

**正确写法**（和现有 `LoginPage`、`Client_SSL` 保持一致）：

```python
class ARP(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '/m/mgmt/network/arp'  # ✅ 实例化时求值
```

**错误写法**：

```python
class ARP(BasePage):
    URL = Settings.BASE_URL + '/m/mgmt/network/arp'  # ❌ import 时求值，拿到默认 IP
```

## Prompts and Skills system

The project uses a two-layer AI guidance system:

### `bin/prompts/` — Role-defining prompts (设定 AI 人设)

These establish the AI's expertise and domain knowledge:
- **`gen-testcases.md`** — "SonicWall UI 自动化测试工程师" role; defines the JSON-to-code mapping rules, pattern matching for CSV generation, and file templates. This is the reference prompt used by `generate_tests.py`'s `SYSTEM_PROMPT`.
- **`gen-basic-tests.md`** — Same role, focused on CSV-driven generation of 6 basic test patterns (Navigation, Breadcrumb, Tab Switching, IP Version, Table Headers, Table Count).
- **`create-suite.md`** — "测试套件架构师" role; defines how to package Playwright-pytest tests into legacy unittest suite directories for CI/CD integration.

### `.claude/skills/` — Triggerable Claude Code skills (定义流程)

These are invoked by the user and drive Claude Code to execute specific workflows:
- **`gen-basic-tests`** — Generate Page Object + test file + fw_pages update from a CSV test case file. Trigger: "generate basic cases", "create test for new page".
- **`create-suite`** — Create a legacy unittest suite directory tree (8 files) for CI/CD. Trigger: "create suite", "generate suite for".

### Recommended workflow for new features

1. Run `page_inspector.py` to extract the page skeleton JSON
2. Run `generate_tests.py` to auto-generate all 4 outputs via GLM AI
3. Review generated files: verify container class names, tab names, and table headers against actual HTML
4. Run the generated test with `--headed` to validate
5. Optionally, create a legacy suite with the `create-suite` skill for CI/CD

## Feature directories vs. bin/tests

The numbered directories at repo root (`33_Policy_Access_Rules/`, `112_Network_Interfaces/`, etc.) contain legacy `definition/settings.py` files that set up API/CLI-based test infrastructure. They are NOT used by the Playwright framework. The Playwright test cases for these features live in `bin/tests/test_*.py`. When adding new UI tests, work exclusively in `bin/tests/` and `bin/pages/`.
