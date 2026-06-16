#!/usr/bin/env python3
"""
MCP Playwright Server — exposes browser tools to Claude Code.
Uses Playwright Async API (compatible with MCP's asyncio framework).

Tools exposed:
  - browser_login(fw_ip, username, password)  Authenticate with SonicWall firewall
  - browser_navigate(url)        Open a page (auto-login if SonicWall login detected)
  - browser_snapshot()            Extract interactive elements as structured JSON
  - browser_evaluate(selector)    Test a locator: count, visibility, text
  - browser_click(selector)       Click an element
  - browser_type(selector, text)  Type text into an input field
  - browser_close()               Close browser
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ── Add project bin/ to path for config imports ──
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ServerCapabilities


# ── Credentials ──
FW_IP = os.environ.get("FW_IP", "192.168.168.168")
FW_USERNAME = os.environ.get("FW_USERNAME", "admin")
FW_PASSWORD = os.environ.get("FW_PASSWORD", "S0nic@uto")
BASE_URL = f"https://{FW_IP}/sonicui/7"

# ── Playwright async singleton ──
_playwright = None
_browser = None
_context = None
_page = None
_logged_in = False


async def _ensure_browser():
    """Ensure Playwright browser is launched (async)."""
    global _playwright, _browser, _context, _page
    if _browser is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        _context = await _browser.new_context(ignore_https_errors=True)
        _page = await _context.new_page()
        _page.set_default_timeout(10000)
    return _page


async def _get_page(url: str = "", auto_login: bool = True):
    """Lazy-init Playwright and return a page (navigate if URL given)."""
    global _logged_in
    page = await _ensure_browser()

    if url:
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Auto-detect SonicWall login page and authenticate
        if auto_login and await _is_login_page(page):
            await _do_login(page)
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

    return page


async def _is_login_page(page) -> bool:
    """Detect if we're on a SonicWall login/auth page."""
    try:
        url = page.url.lower()
        if any(kw in url for kw in ["/auth.html", "/login", "login.html"]):
            return True
        user_field = page.locator('input[name="username"]')
        pass_field = page.locator('input[name="password"]')
        if await user_field.count() > 0 and await pass_field.count() > 0:
            return True
    except Exception:
        pass
    return False


async def _do_login(page):
    """Handle the full SonicWall SonicOS 7 login sequence."""
    global _logged_in
    try:
        from config.settings import Settings
        username = Settings.USERNAME
        password = Settings.PASSWORD
    except ImportError:
        username = FW_USERNAME
        password = FW_PASSWORD

    try:
        # Step 1: Fill credentials and click LOG IN
        await page.locator('input[name="username"]').fill(username)
        await page.locator('input[name="password"]').fill(password)
        # LOG IN is a <div class="sw-login__trigger">, not a <button>
        login_btn = page.locator('.sw-login__trigger')
        btn_count = await login_btn.count()
        if btn_count > 0:
            await login_btn.click()
        else:
            await page.locator('button:has-text("LOG IN")').click()
        await asyncio.sleep(5)

        # Step 2: Handle "Config" button (preempt mode prompt)
        try:
            el = page.get_by_role("button", name="Config", exact=True)
            await el.wait_for(state="visible", timeout=5000)
            await el.click()
            await asyncio.sleep(2)
        except Exception:
            pass

        # Step 3: Handle "Proceed" button (warning dialog)
        try:
            el = page.get_by_role("button", name="Proceed", exact=True)
            await el.wait_for(state="visible", timeout=5000)
            await el.click()
            await asyncio.sleep(2)
        except Exception:
            pass

        # Step 4: Wait for main dashboard
        try:
            await page.wait_for_selector(".fw-app-content", timeout=15000)
            _logged_in = True
        except Exception:
            pass

    except Exception:
        pass


async def _browser_snapshot(page) -> dict:
    """Extract interactive elements from the current page using SonicWall-specific selectors."""
    return await page.evaluate("""() => {
        const result = { url: window.location.href, inputs: [], buttons: [], tabs: [],
                         tables: [], selects: [], toggles: [], headings: [], dialogs: [] };

        // ── Inputs ──
        document.querySelectorAll('input:not([type="hidden"]), textarea').forEach(el => {
            if (!el.offsetParent) return;
            result.inputs.push({
                type: el.type || 'text', name: el.name || '',
                id: el.id || '', placeholder: el.placeholder || '',
                className: (el.className || '').substring(0, 100),
            });
        });

        // ── Buttons ──
        const seenButtons = new Set();
        const addButton = (el, tag) => {
            const text = (el.textContent || '').trim().substring(0, 80);
            const key = text + (el.className || '');
            if ((text || el.getAttribute('aria-label')) && !seenButtons.has(key)) {
                seenButtons.add(key);
                result.buttons.push({
                    tag: tag || el.tagName.toLowerCase(),
                    text: text,
                    className: (el.className || '').substring(0, 120),
                });
            }
        };

        document.querySelectorAll('.sw-icon-button__label-cont, .sw-action-button__label-text').forEach(el => {
            if (el.offsetParent) addButton(el, 'sw-icon-btn');
        });

        document.querySelectorAll('.sw-btn, [class*="sw-btn"]').forEach(el => {
            if (el.offsetParent) addButton(el, 'sw-btn');
        });

        document.querySelectorAll('button, [role="button"]').forEach(el => {
            if (el.offsetParent && !el.closest('.sw-icon-button__label-cont, .sw-action-button__label-text'))
                addButton(el, el.tagName.toLowerCase());
        });

        // ── Tabs ──
        document.querySelectorAll('.sw-tab--l1, .sw-tab--l2').forEach(el => {
            if (!el.offsetParent) return;
            const text = (el.textContent || '').trim();
            if (text && text.length < 50) {
                const isActive = el.classList.contains('sw-tab--active') ||
                                 el.getAttribute('aria-selected') === 'true';
                result.tabs.push({ text, isActive, level: el.classList.contains('sw-tab--l2') ? 'L2' : 'L1' });
            }
        });

        // ── Tables ──
        document.querySelectorAll('.sw-table-body__cont__table').forEach((el, i) => {
            if (!el.offsetParent || el.closest('.sw-modal, .sw-dialog, [role="dialog"]')) return;
            const rows = el.querySelectorAll('.sw-table-row');
            const container = el.closest('[class*="-settings"], [class*="-container"], [class*="-panel"]');
            const containerClass = container ? (container.className || '').split(' ')[0].substring(0, 60) : '';
            const footer = document.querySelector('.sw-table-footer__total-cont__value');
            result.tables.push({
                index: i,
                rowCount: rows.length,
                containerClass: containerClass,
                footerCount: footer ? footer.textContent.trim() : '',
            });
        });

        // ── Selects ──
        document.querySelectorAll('.sw-select__label-cont').forEach(el => {
            if (!el.offsetParent) return;
            result.selects.push({ text: (el.textContent || '').trim().substring(0, 50) });
        });

        // ── Toggles ──
        document.querySelectorAll('.sw-toggle').forEach(el => {
            if (!el.offsetParent) return;
            const input = el.querySelector('input');
            result.toggles.push({
                name: input ? input.name || '' : '',
                checked: input ? input.checked : false,
            });
        });

        // ── Dialogs ──
        document.querySelectorAll('.sw-modal, .sw-dialog, [role="dialog"]').forEach(el => {
            const visible = !!el.offsetParent;
            const title = (el.querySelector('.sw-modal__title, .sw-dialog__title, h2, h3, ' +
                '[class*="title"]') || {}).textContent || '';
            if (visible || title) {
                const buttons = [...el.querySelectorAll('button, .sw-btn, ' +
                    '[class*="btn"], [class*="button"]')].map(b => ({
                    text: (b.textContent || '').trim(),
                    className: (b.className || '').substring(0, 100),
                }));
                const inputs = [...el.querySelectorAll('input:not([type="hidden"])')].map(i => ({
                    name: i.name || '', type: i.type || 'text',
                    placeholder: i.placeholder || '',
                }));
                result.dialogs.push({ title: title.trim(), visible, buttons, inputs });
            }
        });

        return result;
    }""")


# ── MCP Server ──
server = Server("playwright-mcp")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="browser_login",
            description="Log into a SonicWall firewall. Call this first before navigating to firewall pages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fw_ip": {"type": "string", "description": "Firewall IP address"},
                    "username": {"type": "string", "description": "Admin username (default: admin)"},
                    "password": {"type": "string", "description": "Admin password"},
                },
                "required": [],
            },
        ),
        Tool(
            name="browser_navigate",
            description="Open a URL in the Playwright browser. Auto-detects SonicWall login page and authenticates if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to navigate to"},
                    "auto_login": {
                        "type": "boolean",
                        "description": "Auto-login if SonicWall login page detected (default: true)",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="browser_snapshot",
            description="Extract interactive elements from the current page as JSON (buttons, inputs, tabs, dialogs).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_evaluate",
            description="Test a Playwright locator: returns count, visibility, and text of matched elements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Playwright selector to test, e.g. 'button:has-text(\"Cancel\")'",
                    },
                },
                "required": ["selector"],
            },
        ),
        Tool(
            name="browser_click",
            description="Click an element by Playwright selector. Returns error info with page state if click fails.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Playwright selector for the element to click",
                    },
                },
                "required": ["selector"],
            },
        ),
        Tool(
            name="browser_type",
            description="Type text into an input field. Use after browser_snapshot to find the correct input name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Playwright selector for the input field, e.g. 'input[name=\"interface\"]'",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into the field",
                    },
                },
                "required": ["selector", "text"],
            },
        ),
        Tool(
            name="browser_close",
            description="Close the browser and clean up resources.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    global _playwright, _browser, _context, _page, _logged_in
    global FW_IP, FW_USERNAME, FW_PASSWORD, BASE_URL

    try:
        if name == "browser_login":
            if arguments.get("fw_ip"):
                FW_IP = arguments["fw_ip"]
            if arguments.get("username"):
                FW_USERNAME = arguments["username"]
            if arguments.get("password"):
                FW_PASSWORD = arguments["password"]
            BASE_URL = f"https://{FW_IP}/sonicui/7"

            page = await _get_page(f"{BASE_URL}/7/", auto_login=False)
            if await _is_login_page(page):
                await _do_login(page)
                return [TextContent(
                    type="text",
                    text=f"✅ Logged into {FW_IP} successfully. Current URL: {page.url}"
                )]
            else:
                _logged_in = True
                return [TextContent(
                    type="text",
                    text=f"Already authenticated or no login needed. Current URL: {page.url}"
                )]

        elif name == "browser_navigate":
            url = arguments["url"]
            auto_login = arguments.get("auto_login", True)
            page = await _get_page(url, auto_login=auto_login)
            login_note = " (auto-login performed)" if auto_login and _logged_in else ""
            return [TextContent(
                type="text",
                text=f"Navigated to: {page.url}{login_note}"
            )]

        elif name == "browser_snapshot":
            page = await _get_page()
            data = await _browser_snapshot(page)
            summary = (
                f"URL: {data.get('url', '')}\n"
                f"Inputs: {len(data.get('inputs', []))}, "
                f"Buttons: {len(data.get('buttons', []))}, "
                f"Tabs: {len(data.get('tabs', []))}, "
                f"Dialogs: {len(data.get('dialogs', []))}\n\n"
            )
            for d in data.get("dialogs", []):
                summary += f"Dialog '{d['title']}' visible={d['visible']} buttons={d['buttons']}\n"
            summary += "\nButtons:\n"
            for b in data.get("buttons", []):
                summary += f"  [{b['tag']}] \"{b['text']}\" class=\"{b.get('className', '')[:80]}\"\n"
            return [TextContent(
                type="text",
                text=summary + "\n\n--- RAW JSON ---\n" + json.dumps(data, indent=2, ensure_ascii=False)
            )]

        elif name == "browser_evaluate":
            page = await _get_page()
            selector = arguments["selector"]
            try:
                loc = page.locator(selector)
                count = await loc.count()
                info = {"selector": selector, "count": count, "elements": []}
                for i in range(min(count, 5)):
                    el = loc.nth(i)
                    info["elements"].append({
                        "index": i,
                        "visible": await el.is_visible() if count > 0 else False,
                        "text": (await el.inner_text())[:100] if count > 0 else "",
                    })
                return [TextContent(
                    type="text",
                    text=json.dumps(info, indent=2, ensure_ascii=False)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"selector": selector, "error": str(e)[:200]})
                )]

        elif name == "browser_click":
            page = await _get_page()
            selector = arguments["selector"]
            try:
                await page.locator(selector).first.click(timeout=5000)
                await asyncio.sleep(0.5)
                return [TextContent(type="text", text=f"Clicked: {selector}")]
            except Exception as e:
                new_data = await _browser_snapshot(page)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e)[:300],
                        "page_state_after_error": {
                            "url": new_data.get("url"),
                            "dialogs": new_data.get("dialogs", []),
                        }
                    }, indent=2, ensure_ascii=False)
                )]

        elif name == "browser_type":
            page = await _get_page()
            selector = arguments["selector"]
            text = arguments["text"]
            try:
                await page.locator(selector).fill(text)
                return [TextContent(
                    type="text",
                    text=f"Typed '{text}' into: {selector}"
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)[:200], "selector": selector})
                )]

        elif name == "browser_close":
            if _browser:
                await _browser.close()
                if _playwright:
                    await _playwright.stop()
                _playwright = _browser = _context = _page = None
                _logged_in = False
            return [TextContent(type="text", text="Browser closed")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="playwright-mcp",
                server_version="2.0",
                capabilities=ServerCapabilities(tools={}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
