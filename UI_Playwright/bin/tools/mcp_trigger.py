#!/usr/bin/env python3
"""
End-to-end MCP healing demo — Step 1: Trigger self-healing → generate mcp_request.json
Uses the project's own LoginPage for reliable authentication.
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path("/home/UI_Playwright_Local/UI_Playwright")
sys.path.insert(0, str(PROJECT_ROOT / "bin"))

from playwright.sync_api import sync_playwright
from config.settings import Settings

Settings.FIREWALL_IP = "10.8.165.150"
Settings.BASE_URL = f"https://10.8.165.150/sonicui/7"

from pages.login_page import LoginPage
from tools.self_healing_locator import SelfHealingLocator

REQUEST_FILE = PROJECT_ROOT / "bin" / "test_data" / "healing_reports" / "mcp_request.json"


def main():
    print("=" * 60)
    print("Step 1: Trigger self-healing → generate mcp_request.json")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(10000)

        # Use project's LoginPage
        login_page = LoginPage(page)
        login_page.navigate_to_login_page()  # Must navigate first!
        success = login_page.login()
        print(f"🔐 Login: {'✅ success' if success else '❌ failed'}")
        if not success:
            browser.close()
            return 1

        # Navigate to ARP page
        arp_url = f"{Settings.BASE_URL}/m/mgmt/network/arp"
        print(f"\n📄 Navigating to ARP: {arp_url}")
        page.goto(arp_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Switch to Static ARP tab
        try:
            tabs = page.locator('[class*="tab"]')
            for i in range(tabs.count()):
                text = tabs.nth(i).text_content()
                if "Static" in text:
                    tabs.nth(i).click()
                    print(f"  ✅ Switched to: {text.strip()}")
                    page.wait_for_timeout(2000)
                    break
        except Exception as e:
            print(f"  ⚠️ Tab: {e}")

        # Open Add dialog
        print("\n➕ Opening Add dialog...")
        dialog_opened = False
        for sel in ['button:has-text("Add")', '[class*="action-button"]:has-text("Add")', 'text="Add"']:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    print(f"  ✅ Opened with: {sel}")
                    page.wait_for_timeout(2000)
                    dialog_opened = True
                    break
            except Exception:
                continue

        if not dialog_opened:
            print("  ⚠️ Could not open Add dialog")

        # Trigger MCP healing
        broken_selector = '.static-entry-modal__modal-footer-cancel-old'
        description = 'Click the Cancel button on the Add/Edit Static Entry dialog to close it'

        print(f"\n🩺 Triggering MCP healing for: `{broken_selector}`")
        healer = SelfHealingLocator(
            page,
            ai_backend="mcp",
            enable_rules=False,   # Force MCP path
            enable_cache=False,
        )

        result = healer.heal(broken_selector, description)
        healer.save_report()

        # Show generated mcp_request.json
        if REQUEST_FILE.exists():
            request = json.loads(REQUEST_FILE.read_text())
            print(f"\n📤 mcp_request.json generated:")
            print(f"   broken_selector: `{request['broken_selector']}`")
            print(f"   element_description: {request['element_description']}")
            print(f"   page_url: {request['page_url']}")
            print(f"   page_summary: {request.get('page_summary', 'N/A')}")
            print(f"\n   instructions:")
            for line in request['instructions'].split('\n'):
                print(f"     {line}")
        else:
            print("❌ mcp_request.json was NOT generated!")

        print(f"\n📊 Healing result: success={result['success']}")
        if result['success']:
            print(f"   healed_selector: `{result['healed_selector']}`")
        print(f"   method: {result.get('healing_event', {}).get('method', 'unknown')}")

        browser.close()

    print("\n✅ mcp_request.json ready for Claude Code MCP analysis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
