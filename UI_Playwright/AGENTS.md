# AI Coding Agent Instructions for UI Playwright Project

## Project overview
- This is a Playwright-based pytest UI automation repository.
- The effective framework root is `bin/`, where the test framework, configuration, and most test code live.
- Test case files are under `bin/tests/` and follow pytest naming rules: `test_*.py`.
- Common debug and execution operations are performed from `bin/`.

## Primary entrypoint
- Run tests with:
  - `python3 bin/run_tests.py`
- The runner builds a pytest command and executes it with `cwd=bin/`.
- Do not assume the repository root is the test root; `Settings.ROOT_DIR` is set to `bin/` in `bin/config/settings.py`.

## Test structure and conventions
- Pytest configuration is defined in `bin/pytest.ini`.
- Global fixtures and custom options are in `bin/conftest.py`.
- Page objects are in `bin/pages/`, including:
  - `bin/pages/login_page.py`
  - `bin/pages/fw_pages.py`
- Tests use pytest markers such as `auto_login`, `smoke`, `regression`, `gui`, `slow`, and `integration`.
- `@pytest.mark.auto_login` triggers login on the target DUT before the module runs.

## Remote DUT and login environment
- The target firewall DUT is configured with `--fw_ip` and `--password`.
- Default DUT login values are in `bin/config/settings.py`:
  - `FIREWALL_IP = 192.168.168.168`
  - `PASSWORD = S0nic@uto`
- The test environment matches the user description: from one PC login to another DUT and run pytest UI cases remotely.

## Important commands and options
- Run all tests:
  - `python3 bin/run_tests.py`
- Run a specific test file or directory:
  - `python3 bin/run_tests.py -t bin/tests/test_example.py`
- Run with marks:
  - `python3 bin/run_tests.py -m auto_login`
- Run with a specific keyword filter:
  - `python3 bin/run_tests.py -k login`
- Common runner options:
  - `--browser [chromium|firefox|webkit|all]`
  - `--headed` to open the browser UI
  - `--slowmo <ms>` for debug slowdown
  - `--retries <n>` retry failed tests
  - `--timeout <s>` test timeout
  - `--password <password>` DUT login password
  - `--fw_ip <ip>` DUT firewall IP

## Notes for the AI agent
- Prefer editing and reasoning around `bin/`, not the repository root directories like `112_Network_Interfaces/`.
- For debugging or reproducing failures, use `bin/run_tests.py` and `bin/pytest.ini` rather than guessing a new pytest setup.
- When adding or updating UI tests, preserve the existing pytest marker and fixture conventions.
- Keep changes compatible with the `auto_login` fixture and the `LoginPage` / `FWPage` page objects.
- Do not change the core test root path unless explicitly required by the user; the project assumes `bin/` is the runnable root.

## Recommended next customization
- Consider adding a dedicated `.github/copilot-instructions.md` or `AGENTS.md` section for remote DUT setup and login debugging.
- A future skill could help generate test commands for `bin/run_tests.py` and verify `auto_login` fixture usage in new test files.