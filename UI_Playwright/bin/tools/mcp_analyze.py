#!/usr/bin/env python3
"""
MCP Analysis Script v2 — Optimized for SonicWall SonicOS 7.

Reads mcp_request.json → login → navigate → open dialog → analyze target → write mcp_response.json

Uses SonicWall-specific selectors:
  - Tabs:    .sw-tab--l1, .sw-tab--l2
  - Buttons: .sw-icon-button__label-cont, .sw-action-button__label-text
  - Dialogs: .sw-modal, .sw-dialog
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

REQUEST_FILE = PROJECT_ROOT / "bin" / "test_data" / "healing_reports" / "mcp_request.json"
RESPONSE_FILE = PROJECT_ROOT / "bin" / "test_data" / "healing_reports" / "mcp_response.json"


def evaluate(page, selector):
    """Test a Playwright selector on the live page."""
    try:
        loc = page.locator(selector)
        count = loc.count()
        visible = False
        text = ""
        if count > 0:
            try:
                visible = loc.first.is_visible()
                text = loc.first.inner_text()[:80] if visible else (
                    loc.first.text_content() or "")[:80]
            except Exception:
                pass
        return {"selector": selector, "count": count, "is_visible": visible,
                "text": text, "valid": count > 0,
                "ideal": count == 1 and visible}
    except Exception as e:
        return {"selector": selector, "count": 0, "is_visible": False, "text": "",
                "error": str(e)[:100], "valid": False, "ideal": False}


def snapshot(page):
    """Extract page structure using SonicWall-specific selectors."""
    return page.evaluate("""() => {
        const r = {url: window.location.href, buttons: [], tabs: [], dialogs: []};

        // SonicWall toolbar icon buttons
        document.querySelectorAll('.sw-icon-button__label-cont, .sw-action-button__label-text').forEach(el => {
            if (!el.offsetParent) return;
            const text = (el.textContent || '').trim().substring(0, 60);
            if (text) r.buttons.push({tag: 'sw-icon-btn', text,
                className: (el.className || '').substring(0, 100)});
        });

        // Native buttons
        document.querySelectorAll('button, [role="button"]').forEach(el => {
            if (!el.offsetParent || el.closest('.sw-icon-button__label-cont, .sw-action-button__label-text')) return;
            const text = (el.textContent || '').trim().substring(0, 60);
            if (text) r.buttons.push({tag: el.tagName.toLowerCase(), text,
                className: (el.className || '').substring(0, 100)});
        });

        // SonicWall L1/L2 tabs (NOT generic [class*=tab] — that matches table cells!)
        document.querySelectorAll('.sw-tab--l1, .sw-tab--l2').forEach(el => {
            if (!el.offsetParent) return;
            const text = (el.textContent || '').trim();
            if (text && text.length < 40) {
                r.tabs.push({text,
                    level: el.classList.contains('sw-tab--l2') ? 'L2' : 'L1',
                    active: el.classList.contains('sw-tab--active')});
            }
        });

        // Modals / Dialogs
        document.querySelectorAll('.sw-modal, .sw-dialog, [role="dialog"]').forEach(el => {
            const visible = !!el.offsetParent;
            const titleEl = el.querySelector('.sw-modal__title, .sw-dialog__title, h2, h3, [class*="title"]');
            const title = titleEl ? titleEl.textContent.trim() : '';
            if (visible || title) {
                const buttons = [...el.querySelectorAll('button, .sw-btn, [class*="btn"]')].map(b => ({
                    text: (b.textContent || '').trim(),
                    className: (b.className || '').substring(0, 100),
                }));
                r.dialogs.push({title, visible, buttons});
            }
        });

        return r;
    }""")


def main():
    print("=" * 60)
    print("Step 2 (v2): MCP Analysis — SonicWall-optimized")
    print("=" * 60)

    request = json.loads(REQUEST_FILE.read_text())
    print(f"\n📋 Request:")
    print(f"   broken_selector: `{request['broken_selector']}`")
    print(f"   element: {request['element_description']}")
    print(f"   url: {request['page_url']}")
    if request.get('page_buttons'):
        print(f"   known buttons: {request['page_buttons'][:8]}")
    if request.get('page_tabs'):
        print(f"   known tabs: {request['page_tabs'][:5]}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(10000)

        # ═══ Step 1: browser_login ═══
        print("\n🔐 Step 1: browser_login...")
        login_page = LoginPage(page)
        login_page.navigate_to_login_page()
        if not login_page.login():
            print("❌ Login failed")
            browser.close()
            return 1
        print("   ✅ Authenticated")

        # ═══ Step 2: browser_navigate ═══
        print(f"\n📄 Step 2: browser_navigate → {request['page_url']}")
        page.goto(request['page_url'], wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # ═══ Step 3: browser_snapshot → find tabs & buttons ═══
        print("\n📸 Step 3: browser_snapshot")
        snap = snapshot(page)
        print(f"   URL: {snap['url']}")
        print(f"   Buttons ({len(snap['buttons'])}):")
        for b in snap['buttons'][:10]:
            print(f"     [{b['tag']}] \"{b['text']}\"")
        print(f"   Tabs ({len(snap['tabs'])}):")
        for t in snap['tabs']:
            print(f"     [{t['level']}] \"{t['text']}\" {'[ACTIVE]' if t['active'] else ''}")
        print(f"   Dialogs ({len(snap['dialogs'])}):")
        for d in snap['dialogs']:
            print(f"     '{d['title']}' visible={d['visible']} buttons={[b['text'] for b in d['buttons']]}")

        # ═══ Step 4: Open the dialog ═══
        print("\n🖱️  Step 4: Opening dialog...")

        # 4a: Switch to correct tab if needed
        # Derive tab name from element description (e.g. "Add/Edit Static Entry" → "Static ARP Entries")
        target_desc = request['element_description']
        tab_keywords = {
            "Static": ["Static ARP Entries", "Static"],
            "ARP": ["Static ARP Entries", "ARP Cache"],
            "Cache": ["ARP Cache"],
        }
        target_tab = None
        for kw, names in tab_keywords.items():
            if kw.lower() in target_desc.lower():
                target_tab = names[0]
                break

        if not target_tab:
            # Default: look for a non-active L1 tab
            for t in snap['tabs']:
                if not t['active'] and t['level'] == 'L1':
                    target_tab = t['text']
                    break

        if target_tab:
            # Find exact tab text from snapshot
            matched_tab = None
            for t in snap['tabs']:
                if target_tab in t['text'] and not t['active']:
                    matched_tab = t
                    break

            if matched_tab:
                # Use .sw-tab--l1 or .sw-tab--l2 with :has-text()
                level_sel = f".sw-tab--{matched_tab['level'].lower()}"
                tab_sel = f'{level_sel}:has-text("{matched_tab["text"]}")'
                print(f"   Clicking tab: {tab_sel}")
                try:
                    page.locator(tab_sel).first.click()
                    page.wait_for_timeout(2000)
                    print(f"   ✅ Tab switched")
                except Exception as e:
                    print(f"   ⚠️ Tab click failed: {e}")
            else:
                print(f"   ⚠️ Tab '{target_tab}' not found or already active")
        else:
            print("   No tab switch needed")

        # 4b: Click Add button
        add_selectors = [
            '.sw-icon-button__label-cont:has-text("+ Add")',
            '.sw-action-button__label-text:has-text("+ Add")',
            '.sw-icon-button__label-cont:has-text("Add")',
            '.sw-action-button__label-text:has-text("Add")',
            'button:has-text("+ Add")',
            'button:has-text("Add")',
            '[class*="icon-button"]:has-text("Add")',
        ]

        add_clicked = False
        for sel in add_selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    print(f"   ✅ Add clicked: {sel}")
                    add_clicked = True
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        if not add_clicked:
            print("   ⚠️ Could not click Add — analyzing page as-is")

        # 4c: Re-snapshot to see dialog
        if add_clicked:
            page.wait_for_timeout(1000)
            snap2 = snapshot(page)
            print(f"\n📸 Post-dialog snapshot:")
            new_dialogs = [d for d in snap2['dialogs'] if d['visible']]
            for d in new_dialogs:
                print(f"   Dialog: '{d['title']}' buttons={[b['text'] for b in d['buttons']]}")
            snap = snap2

        # ═══ Step 5: browser_evaluate candidates ═══
        print("\n🧪 Step 5: Testing Cancel button candidates...")

        # Build candidate list based on element description
        candidates = []

        # If dialog is open, use dialog buttons as candidates
        visible_dialogs = [d for d in snap['dialogs'] if d['visible']]
        has_open_dialog = len(visible_dialogs) > 0

        if has_open_dialog:
            # Extract Cancel button info from the dialog
            for d in visible_dialogs:
                for b in d['buttons']:
                    if 'cancel' in b['text'].lower():
                        candidates.append({
                            "selector": f'text="{b["text"]}"',
                            "strategy": "text",
                            "confidence": "high",
                            "reasoning": f"Exact text match from open dialog '{d['title']}'",
                        })
                        # Also try class-based selector
                        if b.get('className'):
                            cls = b['className'].split()[0]  # first class
                            if cls:
                                candidates.append({
                                    "selector": f'.{cls}',
                                    "strategy": "css",
                                    "confidence": "high",
                                    "reasoning": f"Class match from open dialog '{d['title']}'",
                                })

        # Always add generic fallbacks
        fallback_candidates = [
            'text="Cancel"',
            'button:has-text("Cancel")',
            '[class*="modal"] button:has-text("Cancel")',
            '[class*="dialog"] button:has-text("Cancel")',
            '[class*="footer"] button:has-text("Cancel")',
            '[class*="modal-footer-cancel"]',
            '[class*="footer-cancel"]',
            '[class*="cancel-btn"]',
            '[class*="btn-cancel"]',
        ]
        for sel in fallback_candidates:
            strategy = "text" if sel.startswith("text=") else "css"
            candidates.append({
                "selector": sel,
                "strategy": strategy,
                "confidence": "medium",
                "reasoning": "Fallback candidate",
            })

        # Evaluate all candidates
        results = []
        for c in candidates:
            r = evaluate(page, c["selector"])
            status = "✅ IDEAL" if r["ideal"] else (
                "⚠️ MULTI" if r["count"] > 1 else (
                    "👻 HIDDEN" if r["count"] == 1 and not r["is_visible"] else "❌ NONE"))
            if r["count"] > 0:
                print(f"   {status} `{c['selector']}` → count={r['count']}, visible={r['is_visible']}"
                      + (f", text='{r['text']}'" if r['text'] else ""))
            results.append({**c, **r})

        # ═══ Step 6: Write mcp_response.json ═══
        print("\n📝 Step 6: Writing mcp_response.json...")

        ideal = [r for r in results if r["ideal"]]
        single = [r for r in results if r["count"] == 1 and not r["is_visible"]]
        multi = [r for r in results if r["count"] > 1]

        response_candidates = []
        for r in ideal:
            response_candidates.append({
                "selector": r["selector"], "strategy": r["strategy"],
                "confidence": r["confidence"], "reasoning": r["reasoning"],
                "count": r["count"], "is_visible": r["is_visible"],
                "score": 100, "valid": True, "ideal": True,
            })

        for r in single[:2]:
            response_candidates.append({
                "selector": r["selector"], "strategy": r["strategy"],
                "confidence": r["confidence"], "reasoning": r["reasoning"],
                "count": r["count"], "is_visible": r["is_visible"],
                "score": 70, "valid": True, "ideal": False,
            })

        for r in multi[:1]:
            response_candidates.append({
                "selector": r["selector"], "strategy": r["strategy"],
                "confidence": r["confidence"], "reasoning": r["reasoning"],
                "count": r["count"], "is_visible": r["is_visible"],
                "score": 40, "valid": False, "ideal": False,
            })

        if not response_candidates:
            response_candidates.append({
                "selector": 'text="Cancel"',
                "strategy": "text",
                "confidence": "medium",
                "reasoning": "Last-resort text fallback — Cancel text is stable across SonicWall versions",
                "score": 50,
                "valid": True,
                "ideal": False,
            })

        response = {
            "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "page_url": request["page_url"],
            "element_description": request["element_description"],
            "broken_selector": request["broken_selector"],
            "candidates": response_candidates,
            "dialog_was_open": add_clicked,
            "page_snapshot_summary": {
                "total_buttons": len(snap["buttons"]),
                "total_dialogs": len(snap["dialogs"]),
                "total_tabs": len(snap["tabs"]),
            },
            "response": json.dumps({"candidates": response_candidates}),
        }

        RESPONSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        RESPONSE_FILE.write_text(json.dumps(response, indent=2, ensure_ascii=False))
        print(f"   ✅ Written to: {RESPONSE_FILE}")

        print(f"\n🏆 Top {min(5, len(response_candidates))} candidates:")
        for i, c in enumerate(response_candidates[:5]):
            print(f"   {i+1}. `{c['selector']}` (score: {c['score']}, {c['strategy']})")

        browser.close()

    print("\n✅ MCP analysis complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
