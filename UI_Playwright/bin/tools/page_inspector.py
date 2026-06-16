#!/usr/bin/env python3
"""
Page Inspector — extracts structured page skeleton from SonicOS 7 firewall UI.

Usage:
    python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp
    python3 bin/tools/page_inspector.py --feature client_ssl --url /m/policy/dpi-ssl/client-ssl --headed
    python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --fw_ip 10.8.165.150

Output: bin/test_data/page_structure/{feature}_structure.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Make bin/ importable from project root or from bin/tools/
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from playwright.sync_api import sync_playwright
from config.settings import Settings
from config.logger import get_logger

logger = get_logger("page_inspector")

# ── buttons that are safe to click (open dialogs, don't mutate data) ──
SAFE_BUTTON_PATTERNS = ["add", "edit", "settings", "statistics", "configure", "new", "create", "import"]
SKIP_BUTTON_PATTERNS = ["delete", "flush", "remove", "clear", "reset", "restart", "reboot", "apply", "save", "update", "ok"]


def _is_safe_to_click(button_text: str) -> bool:
    """Only click buttons that are likely to open a dialog, not destructive ones."""
    text_lower = button_text.strip().lower()
    for skip in SKIP_BUTTON_PATTERNS:
        if skip in text_lower:
            return False
    for safe in SAFE_BUTTON_PATTERNS:
        if safe in text_lower:
            return True
    return False


def login_to_firewall(page, username: str, password: str):
    """Log into the firewall and return the logged-in page."""
    from pages.login_page import LoginPage
    login_page = LoginPage(page)
    login_page.navigate_to_login_page()
    success = login_page.login(username, password)
    if not success:
        raise RuntimeError("Login failed — check credentials and firewall IP")
    logger.info("Login successful")


def extract_breadcrumb(page) -> str:
    """Extract breadcrumb text from the page."""
    try:
        bc = page.locator(".sw-breadcrumb")
        if bc.count() > 0:
            return bc.first.inner_text().replace("\n", " / ").strip()
    except Exception:
        pass
    return ""


def extract_tabs(page) -> dict:
    """Extract L1 and L2 tab names visible on the page."""
    tabs = {"l1": [], "l2": []}
    for level in ("l1", "l2"):
        selector = f".sw-tab--{level}"
        try:
            elements = page.locator(selector).all()
            for el in elements:
                text = el.inner_text().strip()
                if text:
                    tabs[level].append(text)
        except Exception:
            pass
    return tabs


def _find_container_class(table_locator) -> str:
    """Walk up from a .sw-table element to find its feature-specific container class."""
    try:
        parent = table_locator.locator("..")
        parent_classes = (parent.get_attribute("class") or "").split()
        # prefer the longest non-sw class (feature-specific ones are usually verbose)
        candidates = [c for c in parent_classes if not c.startswith("sw-")]
        if candidates:
            return max(candidates, key=len)
        # fallback: try another level up
        grandparent = parent.locator("..")
        gp_classes = (grandparent.get_attribute("class") or "").split()
        candidates = [c for c in gp_classes if not c.startswith("sw-")]
        if candidates:
            return max(candidates, key=len)
    except Exception:
        pass
    return ""


def _detect_cell_type(cell) -> str:
    """Detect the type of content in a table cell.

    Returns one of: 'text', 'toggle', 'icon_toggle', 'checkbox'.
    """
    try:
        if cell.locator(".sw-toggle").count() > 0:
            return "toggle"
        if cell.locator("input[type='checkbox']").count() > 0:
            return "checkbox"
        # SonicWall green-check / icon-based toggles
        if cell.locator(".sw-icon, .sw-icon__inner, [class*='icon-check'], [class*='icon-close'], "
                        "[class*='icon-true'], [class*='icon-false'], [class*='icon-status']").count() > 0:
            return "icon_toggle"
    except Exception:
        pass
    return "text"


def extract_tables_in_view(page, current_tab: str = "") -> list:
    """Extract all tables visible in the current view (excluding modals)."""
    tables = []
    # find .sw-table elements NOT inside a modal
    table_elements = page.locator(".sw-table-body__cont__table").all()
    for i, body in enumerate(table_elements):
        try:
            # skip if inside a modal
            if body.locator("xpath=ancestor::div[contains(@class,'sw-modal')]").count() > 0:
                continue
            # skip if hidden
            if not body.is_visible():
                continue

            # find the nearest .sw-table ancestor
            sw_table = page.locator(".sw-table").nth(i) if i < page.locator(".sw-table").count() else None
            container_class = ""
            if sw_table and sw_table.count() > 0:
                container_class = _find_container_class(sw_table)

            # extract headers
            headers = []
            header_el = body.locator("..").locator("..").locator(".sw-table-header")
            if header_el.count() == 0:
                # try sibling approach
                header_el = page.locator(f".{container_class} > .sw-table .sw-table-header") if container_class else page.locator(".sw-table-header").first

            if header_el.count() > 0:
                header_text = header_el.first.inner_text().strip()
                headers = [h.strip() for h in header_text.split("\n") if h.strip()]

            # count rows and extract row identifiers (first non-empty text cell)
            rows = body.locator("> .sw-table-row")
            row_count = rows.count()
            row_identifiers = []
            for r in range(min(row_count, 50)):  # cap at 50 rows
                try:
                    row_el = rows.nth(r)
                    if not row_el.is_visible():
                        continue
                    # Iterate all cells, pick the first one with non-empty text as the row ID.
                    # The first few cells are often zero-col (row number) or checkbox which are blank.
                    cells = row_el.locator(".sw-table-row__cell, > div, > td")
                    for ci in range(cells.count()):
                        try:
                            cell = cells.nth(ci)
                            ident = cell.inner_text().strip()[:60]
                            if ident:
                                row_identifiers.append(ident)
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

            # Detect column types by inspecting the first data row
            column_types = {}
            if row_count > 0 and headers:
                first_row = rows.first
                if first_row.count() > 0:
                    cells = first_row.locator("> div, > span, > .sw-table-cell, > td")
                    cell_count = cells.count()
                    for ci, header in enumerate(headers):
                        if ci < cell_count:
                            column_types[header] = _detect_cell_type(cells.nth(ci))
                        else:
                            column_types[header] = "text"

            # check for footer counter
            has_footer = False
            footer_counter = page.locator(".sw-table-footer__total-cont__value").first
            if footer_counter.count() > 0:
                has_footer = True

            table_info = {
                "tab": current_tab,
                "container": container_class,
                "headers": headers,
                "row_count": row_count,
                "row_identifiers": row_identifiers,
                "column_types": column_types,
                "has_footer_counter": has_footer,
            }
            tables.append(table_info)
        except Exception as e:
            logger.warning(f"Error extracting table {i}: {e}")
            continue
    return tables


def extract_buttons(page, current_tab: str = "") -> list:
    """Extract visible action buttons in the main content area (not in modals)."""
    buttons = []

    # icon buttons (toolbar)
    try:
        icon_buttons = page.locator(".sw-icon-button__label-cont").all()
        for btn in icon_buttons:
            try:
                if btn.is_visible():
                    text = btn.inner_text().strip()
                    if text:
                        buttons.append({
                            "text": text,
                            "type": "icon_button",
                            "tab": current_tab,
                            "safe_to_click": _is_safe_to_click(text),
                        })
            except Exception:
                pass
    except Exception:
        pass

    # regular buttons not in modals
    try:
        all_buttons = page.locator("button:visible").all()
        for btn in all_buttons:
            try:
                # skip if inside modal or confirm dialog (we handle those separately)
                if btn.locator("xpath=ancestor::div[contains(@class,'sw-modal')]").count() > 0:
                    continue
                if btn.locator("xpath=ancestor::div[contains(@class,'sw-confirm-modal')]").count() > 0:
                    continue
                text = btn.inner_text().strip()
                if text and text not in [b["text"] for b in buttons]:
                    buttons.append({
                        "text": text,
                        "type": "button",
                        "tab": current_tab,
                        "safe_to_click": _is_safe_to_click(text),
                    })
            except Exception:
                pass
    except Exception:
        pass

    return buttons


def extract_page_dropdowns(page, current_tab: str = "") -> list:
    """Extract visible dropdown/select elements in the main content area (not modals)."""
    dropdowns = []
    try:
        selects = page.locator(".sw-select:visible").all()
        for sel in selects:
            try:
                if sel.locator("xpath=ancestor::div[contains(@class,'sw-modal')]").count() > 0:
                    continue
                # Get label from nearby element or placeholder
                label = ""
                try:
                    input_el = sel.locator("input")
                    if input_el.count() > 0:
                        placeholder = input_el.first.get_attribute("placeholder") or ""
                        label = placeholder
                except Exception:
                    pass
                text = sel.inner_text().strip()[:80]
                dropdowns.append({
                    "label": label or text,
                    "tab": current_tab,
                })
            except Exception:
                pass
    except Exception:
        pass
    return dropdowns


def extract_row_hover_actions(page, table_container: str, tab_name: str) -> list:
    """Hover over table rows to discover floating action buttons (Edit, Delete, etc.).

    Searches for buttons that appear near a hovered row by looking at icon classes,
    aria-label, and title attributes — not text content (hover buttons are often icon-only).
    """
    actions = []
    try:
        if table_container:
            rows = page.locator(f".{table_container} .sw-table-row, "
                               f".{table_container} .sw-table-body__cont__table > .sw-table-row")
        else:
            rows = page.locator(".sw-table-body__cont__table > .sw-table-row")

        # Find first visible row
        first_row = None
        for i in range(min(rows.count(), 5)):
            try:
                r = rows.nth(i)
                if r.is_visible():
                    first_row = r
                    break
            except Exception:
                pass
        if first_row is None:
            return actions

        # Hover over the row
        first_row.hover()
        page.wait_for_timeout(1200)

        # Try to find action buttons by their icon patterns — these are usually
        # icon-only buttons so we can't rely on text content.
        action_patterns = [
            ("edit", ["icon-edit", "icon-pencil", "icon-edit-pencil", "pencil"]),
            ("delete", ["icon-delete", "icon-trash", "icon-remove", "trash"]),
            ("configure", ["icon-configure", "icon-gear", "icon-settings", "gear"]),
            ("statistics", ["icon-statistics", "icon-chart", "icon-stats", "chart"]),
        ]

        found_actions = {}
        for action_name, icon_hints in action_patterns:
            escaped = action_name.replace("'", "\\'")
            for hint in icon_hints:
                escaped_hint = hint.replace("'", "\\'")
                result = page.evaluate(f"""
                    (() => {{
                        const btns = document.querySelectorAll(
                            '.sw-icon-button, .sw-icon, [class*="icon-btn"], ' +
                            '[class*="action-btn"], [class*="row-action"], button, [role="button"]'
                        );
                        for (const el of btns) {{
                            if (!el.offsetParent) continue;
                            const cls = (el.className || '').toString().toLowerCase();
                            const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                            const title = (el.getAttribute('title') || '').toLowerCase();
                            const allInfo = cls + ' ' + aria + ' ' + title;
                            if (allInfo.includes('{escaped_hint}') || allInfo.includes('{escaped}')) {{
                                return true;
                            }}
                        }}
                        return false;
                    }})()
                """)
                if result:
                    found_actions[action_name] = True
                    break

        if found_actions:
            logger.info(f"  Row hover icons found: {list(found_actions.keys())}")
            for action_name in found_actions:
                actions.append({
                    "text": action_name,
                    "type": "row_hover_button",
                    "tab": tab_name,
                    "table_container": table_container,
                    "safe_to_click": _is_safe_to_click(action_name),
                })

        page.mouse.move(0, 0)
        page.wait_for_timeout(300)

    except Exception as e:
        logger.warning(f"  Error extracting row hover actions: {e}")

    return actions


def extract_dialog(page, trigger_button_text: str, tab_name: str = "") -> dict | None:
    """Click a button, wait for a modal dialog, extract its structure, then close it."""
    logger.info(f"  Exploring dialog triggered by: [{trigger_button_text}] on tab [{tab_name}]")

    # click the button
    try:
        btn = page.locator(".sw-icon-button__label-cont").get_by_text(trigger_button_text, exact=True)
        if btn.count() == 0:
            btn = page.get_by_role("button", name=trigger_button_text, exact=True)
        if btn.count() == 0:
            btn = page.get_by_text(trigger_button_text, exact=True)
        if btn.count() == 0:
            logger.info(f"    Button not found: {trigger_button_text}")
            return None
        btn.first.click()
    except Exception as e:
        logger.warning(f"    Failed to click button: {e}")
        return None

    # wait for modal
    page.wait_for_timeout(1500)

    # Check confirm dialog FIRST — it's often wrapped in a .sw-modal overlay
    confirm = page.locator(".sw-confirm-modal__dialog:visible")
    if confirm.count() > 0:
        d = _extract_confirm_dialog(confirm.first, trigger_button_text)
        d["tab"] = tab_name
        _close_confirm_dialog_safely(page)
        page.wait_for_timeout(500)
        return d

    modal = page.locator(".sw-modal:visible")
    if modal.count() == 0:
        # maybe a popover?
        popover = page.locator(".sw-popover__board:visible")
        if popover.count() > 0:
            d = _extract_popover(page, popover.first, trigger_button_text)
            d["tab"] = tab_name
            return d
        logger.info(f"    No dialog appeared after clicking [{trigger_button_text}]")
        return None

    modal_el = modal.first
    dialog = _extract_modal(page, modal_el, trigger_button_text)
    dialog["tab"] = tab_name

    # close the dialog (ALWAYS cancel, never save)
    _close_modal_safely(page, modal_el)
    page.wait_for_timeout(500)

    return dialog


def _extract_modal(page, modal, trigger: str) -> dict:
    """Extract structure from a modal dialog, including an HTML snapshot."""
    result = {"trigger": trigger, "type": "modal"}

    # title
    try:
        title_el = modal.locator(".sw-modal__title")
        result["title"] = title_el.first.inner_text().strip() if title_el.count() > 0 else ""
    except Exception:
        result["title"] = ""

    # buttons in footer
    try:
        footer_btns = modal.locator(".sw-modal__footer .sw-button, .sw-modal__footer button").all()
        result["buttons"] = [b.inner_text().strip() for b in footer_btns if b.inner_text().strip()]
    except Exception:
        result["buttons"] = []

    # form fields (structured)
    result["fields"] = _extract_form_fields(modal)

    # HTML snapshot of the dialog body (for LLM to see actual DOM)
    try:
        body = modal.locator(".sw-modal-body, .sw-modal__body")
        if body.count() > 0:
            html = body.first.inner_html()
            lines = [l for l in html.split("\n") if l.strip() and "<!--" not in l]
            result["html"] = "\n".join(lines[:200])
        else:
            result["html"] = modal.first.inner_html()[:8000]
    except Exception:
        result["html"] = ""

    return result


def _extract_popover(page, popover, trigger: str) -> dict:
    """Extract structure from a popover."""
    result = {"trigger": trigger, "type": "popover"}

    try:
        title_el = popover.locator(".sw-popover__board__title__text")
        result["title"] = title_el.first.inner_text().strip() if title_el.count() > 0 else ""
    except Exception:
        result["title"] = ""

    result["fields"] = _extract_form_fields(popover)
    result["buttons"] = []

    # HTML snapshot
    try:
        body = popover.locator(".sw-popover__board__body")
        if body.count() > 0:
            html = body.first.inner_html()
            lines = [l for l in html.split("\n") if l.strip() and "<!--" not in l]
            result["html"] = "\n".join(lines[:60])
        else:
            result["html"] = popover.first.inner_html()[:2000]
    except Exception:
        result["html"] = ""

    # close popover
    try:
        close_btn = popover.locator(".sw-popover__board__title__close .sw-icon, .sw-icon-close")
        if close_btn.count() > 0:
            close_btn.first.click()
            page.wait_for_timeout(300)
    except Exception:
        pass

    return result


def _extract_form_fields(container) -> list:
    """Extract form fields from a modal or popover container."""
    fields = []
    try:
        rows = container.locator(".sw-form-row").all()
    except Exception:
        rows = []

    # Fallback: if no .sw-form-row, try simpler row-like elements
    if not rows:
        try:
            rows = container.locator("[class*='row'], [class*='item'], [class*='field'], [class*='stat']").all()
        except Exception:
            pass

    for row in rows:
        try:
            if not row.is_visible():
                continue

            # label
            label = ""
            label_el = row.locator(".sw-form-row__label, [class*='label'], [class*='key'], [class*='name']")
            if label_el.count() > 0:
                label = label_el.first.inner_text().strip().rstrip("*").strip()

            # if no dedicated label, use the row's own text (popover k-v rows)
            if not label:
                label = row.inner_text().strip()

            # field container
            field_cont = row.locator(".sw-form-row__field, [class*='value'], [class*='field'], [class*='content']")
            if field_cont.count() == 0:
                # no field container — this might be a pure text row (e.g., Statistics popover)
                # treat the whole row text as the field value
                field_info = {"label": label, "type": "display"}
                fields.append(field_info)
                continue

            field_info = {"label": label}

            # detect field type
            if field_cont.locator(".sw-toggle").count() > 0:
                field_info["type"] = "toggle"
            elif field_cont.locator(".sw-select").count() > 0:
                field_info["type"] = "dropdown"
                try:
                    dropdown_input = field_cont.locator("input")
                    if dropdown_input.count() > 0:
                        field_info["input_name"] = dropdown_input.first.get_attribute("name") or ""
                except Exception:
                    pass
            elif field_cont.locator(".sw-checkbox").count() > 0:
                field_info["type"] = "checkbox"
                try:
                    cb_input = field_cont.locator("input[type='checkbox']")
                    if cb_input.count() > 0:
                        field_info["input_name"] = cb_input.first.get_attribute("name") or ""
                except Exception:
                    pass
            elif field_cont.locator("input[type='radio']").count() > 0:
                field_info["type"] = "radio"
            elif field_cont.locator("textarea").count() > 0:
                field_info["type"] = "textarea"
            elif field_cont.locator("input[type='number']").count() > 0:
                field_info["type"] = "number"
            elif field_cont.locator("input").count() > 0:
                inp = field_cont.locator("input").first
                inp_type = inp.get_attribute("type") or "text"
                field_info["type"] = inp_type
                field_info["input_name"] = inp.get_attribute("name") or ""
            else:
                # has field container but no form control → display-only text
                field_info["type"] = "display"

            # check required
            is_required = row.locator(".sw-form-row__label .required, [class*='required']").count() > 0
            if is_required:
                field_info["required"] = True

            fields.append(field_info)
        except Exception:
            continue

    return fields


def _close_modal_safely(page, modal):
    """Close a modal safely — try Cancel first, then X button."""
    try:
        # try Cancel button first
        cancel_btn = modal.locator(".sw-modal__footer .sw-button").get_by_text("Cancel", exact=True)
        if cancel_btn.count() > 0 and cancel_btn.first.is_visible():
            cancel_btn.first.click()
            page.wait_for_timeout(500)
            return

        # try X close button
        close_btn = modal.locator(".sw-modal__close")
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
            page.wait_for_timeout(500)
            return

        # last resort: press Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def _extract_confirm_dialog(confirm, trigger: str) -> dict:
    """Extract structure from a .sw-confirm-modal__dialog confirmation dialog."""
    result = {"trigger": trigger, "type": "confirm_dialog"}

    # message paragraphs
    try:
        paras = confirm.locator(".sw-status-info__text__message__para")
        messages = []
        for i in range(paras.count()):
            try:
                t = paras.nth(i).inner_text().strip()
                if t:
                    messages.append(t)
            except Exception:
                pass
        result["title"] = " | ".join(messages) if messages else ""
    except Exception:
        result["title"] = ""

    # footer buttons
    try:
        footer_btns = confirm.locator(".sw-confirm-modal__footer button, .sw-action-bar button")
        buttons = []
        for i in range(footer_btns.count()):
            try:
                b = footer_btns.nth(i)
                if b.is_visible():
                    text = b.inner_text().strip()
                    if text:
                        buttons.append(text)
            except Exception:
                pass
        result["buttons"] = buttons
    except Exception:
        result["buttons"] = []

    # HTML snapshot
    try:
        html = confirm.inner_html()
        lines = [l for l in html.split("\n") if l.strip() and "<!--" not in l]
        result["html"] = "\n".join(lines[:150])
    except Exception:
        result["html"] = ""

    return result


def _close_confirm_dialog_safely(page):
    """Close a confirmation dialog safely — click 'No' (default safe option)."""
    try:
        # prefer "No" button (safe cancel)
        no_btn = page.locator(".sw-confirm-modal__dialog button:has-text('No')")
        if no_btn.count() > 0 and no_btn.first.is_visible():
            no_btn.first.click()
            page.wait_for_timeout(500)
            return

        # fallback: click the first non-default button (leftmost = cancel)
        btns = page.locator(".sw-confirm-modal__dialog button:visible")
        if btns.count() > 0:
            btns.first.click()
            page.wait_for_timeout(500)
            return

        # last resort: Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def _navigate_to_known_page(page) -> str:
    """Navigate to a known working page (ARP) to bootstrap the SPA menu."""
    arp_url = f"{Settings.BASE_URL}/m/mgmt/network/arp"
    logger.info(f"Bootstrapping SPA via: {arp_url}")
    page.goto(arp_url)
    page.wait_for_load_state("domcontentloaded")
    try:
        page.locator(".sw-blocking-progress").wait_for(state="hidden", timeout=10000)
        page.locator(".fw-app-main__blocking").wait_for(state="hidden", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    return page.url


def navigate_via_menu(page, feature_name: str) -> dict:
    """Navigate to a page by clicking its label in the left sidebar nav.

    Uses normalized text matching (strip non-alphanumeric, lowercase) so that
    'mac_ip_anti_spoof' matches 'MAC IP Anti-Spoof' regardless of case/hyphens.

    Returns True if navigation succeeded.
    """
    logger.info(f"Searching left nav for '{feature_name}' (normalized) ...")

    result = page.evaluate(f"""
        (() => {{
            const normalize = s => s.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
            const target = normalize('{feature_name}');

            // Step 1: expand ALL collapsed nav groups so items become visible
            const allEls = document.querySelectorAll('*');
            let expanded = 0;
            for (const el of allEls) {{
                const cls = (el.className || '').toString();
                const tag = el.tagName.toLowerCase();
                // Click on elements that look like collapsed nav groups
                if (/collapsed|expandable|toggle|arrow|chevron|caret|tree/.test(cls) ||
                    (el.getAttribute('aria-expanded') === 'false')) {{
                    try {{ el.click(); expanded++; }} catch(e) {{}}
                }}
            }}
            // Also try clicking any element whose click handler expands a submenu
            const expanders = document.querySelectorAll(
                '.sw-tree-toggle, .sw-nav-toggle, [class*="toggle"], [class*="expand"], ' +
                '[class*="collapse"], [class*="arrow"], [class*="chevron"], [aria-expanded="false"]'
            );
            for (const el of expanders) {{
                try {{ el.click(); expanded++; }} catch(e) {{}}
            }}

            // Step 2: collect visible nav items for debug
            const navTexts = [];
            const navItems = document.querySelectorAll(
                '.sw-nav-item, .sw-nav__item, [class*="nav-item"], [class*="nav__item"], ' +
                '[class*="menu-item"], [class*="sidebar"] a, [class*="sidebar"] li, [class*="sidebar"] span'
            );
            for (const el of navItems) {{
                if (el.offsetParent !== null) {{
                    const t = el.textContent.trim();
                    if (t && t.length < 80) navTexts.push(t);
                }}
            }}

            // Step 3: find target — search within sidebar/nav containers first
            const containers = document.querySelectorAll(
                '.sw-nav, nav, [class*="sidebar"], [class*="left-panel"], [class*="nav-tree"], [class*="nav-menu"]'
            );
            for (const container of containers) {{
                if (!container.isConnected || container.offsetParent === null) continue;
                const children = container.querySelectorAll('a, li, span, button, div');
                for (const el of children) {{
                    if (el.offsetParent === null) continue;
                    if (normalize(el.textContent || '').includes(target)) {{
                        const info = {{
                            href: el.getAttribute('href') || '',
                            id: el.id || '',
                            className: el.className || '',
                            dataset: el.dataset || {{}},
                            outerHTML: (el.outerHTML || '').slice(0,200)
                        }};
                        el.click();
                        return {{ok: true, text: el.textContent.trim().slice(0,60), elementInfo: info,
                                expanded: expanded, navPreview: navTexts.slice(0,20)}};
                    }}
                }}
            }}

            // Step 4: fallback — search any left-positioned element
            const all = document.querySelectorAll('a, li, span, button, div');
            for (const el of all) {{
                if (el.offsetParent === null) continue;
                const rect = el.getBoundingClientRect();
                if (rect.x > 400 || rect.width > 400) continue;
                if (normalize(el.textContent || '').includes(target)) {{
                    const info = {{
                        href: el.getAttribute('href') || '',
                        id: el.id || '',
                        className: el.className || '',
                        dataset: el.dataset || {{}},
                        outerHTML: (el.outerHTML || '').slice(0,200)
                    }};
                    el.click();
                    return {{ok: true, text: el.textContent.trim().slice(0,60), elementInfo: info,
                            expanded: expanded, navPreview: navTexts.slice(0,20)}};
                }}
            }}

            return {{ok: false, expanded: expanded, navPreview: navTexts.slice(0, 20)}};
        }})()
    """)

    # Log debug info
    expanded = result.get("expanded", 0)
    nav_preview = result.get("navPreview", [])
    logger.info(f"  Menu groups expanded: {expanded}")
    if nav_preview:
        logger.info(f"  Visible nav items ({len(nav_preview)}): {nav_preview[:10]}")

    page.wait_for_timeout(2000)
    try:
        page.locator(".sw-blocking-progress").wait_for(state="hidden", timeout=10000)
    except Exception:
        pass

    # return the full result dict so caller can make fallback decisions
    if result.get("ok"):
        logger.info(f"  ✓ clicked '{result['text']}' → {page.url}")
    else:
        logger.warning(f"  ✗ search failed — target not found in nav")
    return result


def explore_page(page, feature_url: str, feature_name: str = "") -> dict:
    """Main orchestrator: navigate, extract static skeleton, then explore interactively."""
    # ── Step 0: Navigate ──
    target_url = f"{Settings.BASE_URL}{feature_url}"
    logger.info(f"Navigating to: {target_url}")
    page.goto(target_url, wait_until="domcontentloaded")
    # Wait for SPA framework to fully render — try multiple signals
    try:
        page.locator(".sw-blocking-progress").wait_for(state="hidden", timeout=15000)
    except Exception:
        pass
    try:
        page.locator(".fw-app-main__blocking").wait_for(state="hidden", timeout=15000)
    except Exception:
        pass
    # Wait for actual page content to appear (tabs, tables, or any sw-* component)
    for selector in [".sw-tab--l1", ".sw-table", ".sw-form-row", ".sw-breadcrumb"]:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=5000)
            logger.info(f"  Content signal: '{selector}' appeared")
            break
        except Exception:
            pass
    page.wait_for_timeout(4000)
    logger.info(f"Landed on: {page.url}")

    # ── Step 1: Static skeleton ──
    logger.info("Extracting static page skeleton...")
    result = {
        "url": feature_url,
        "breadcrumb": extract_breadcrumb(page),
    }

    # tabs
    result["tabs"] = extract_tabs(page)
    logger.info(f"  Tabs: L1={result['tabs']['l1']}, L2={result['tabs']['l2']}")

    # determine current active tab BEFORE scanning buttons
    current_tab = ""
    try:
        active = page.locator(".sw-tab--l1.sw-tab--active")
        if active.count() > 0:
            current_tab = active.first.inner_text().strip()
    except Exception:
        pass

    # buttons on initial tab
    result["buttons"] = extract_buttons(page, current_tab)
    logger.info(f"  Buttons (tab=[{current_tab}]): {[b['text'] for b in result['buttons']]}")

    # tables in initial view
    result["tables"] = extract_tables_in_view(page, current_tab)
    logger.info(f"  Tables (initial): {len(result['tables'])} found")

    # page-level dropdowns on initial tab
    initial_dropdowns = extract_page_dropdowns(page, current_tab)
    if initial_dropdowns:
        result["page_dropdowns"] = initial_dropdowns
        logger.info(f"  Page dropdowns: {[d['label'] for d in initial_dropdowns]}")

    # ── Step 2: Explore each tab (L1 + L2 subtabs) ──
    result["dialogs"] = []
    seen_buttons = {b["text"] for b in result["buttons"]}

    all_l1 = list(result["tabs"]["l1"])
    all_l2 = list(result["tabs"]["l2"])
    if current_tab and current_tab in all_l1:
        all_l1.remove(current_tab)
        all_l1.insert(0, current_tab)

    for l1_name in all_l1:
        logger.info(f"  Exploring L1 tab: [{l1_name}]")

        try:
            # switch to L1 tab
            if l1_name != current_tab:
                tab_el = page.locator(f'.sw-tab--l1:has-text("{l1_name}")').first
                if tab_el.count() > 0:
                    tab_el.click()
                    page.wait_for_timeout(2000)

            # Determine which L2 tabs to explore for this L1 tab.
            # Find the active L2 tab after switching L1
            active_l2 = ""
            try:
                l2_active = page.locator(".sw-tab--l2.sw-tab--active")
                if l2_active.count() > 0:
                    active_l2 = l2_active.first.inner_text().strip()
            except Exception:
                pass
            l2_order = [t for t in all_l2 if t == active_l2] + [t for t in all_l2 if t != active_l2]

            # If no L2 tabs, just explore L1 tab once
            if not l2_order:
                l2_order = [""]

            for l2_name in l2_order:
                context_label = f"{l1_name}/{l2_name}" if l2_name else l1_name
                logger.info(f"    Context: [{context_label}]")

                if l2_name and l2_name != active_l2:
                    l2_el = page.locator(f'.sw-tab--l2:has-text("{l2_name}")').first
                    if l2_el.count() > 0:
                        l2_el.click()
                        page.wait_for_timeout(1500)
                        active_l2 = l2_name

                # extract tables
                tab_tables = extract_tables_in_view(page, context_label)
                for t in tab_tables:
                    if t not in result["tables"]:
                        result["tables"].append(t)
                logger.info(f"      Tables: {len(tab_tables)}")

                # extract buttons
                tab_buttons = extract_buttons(page, context_label)
                new_buttons = [b for b in tab_buttons if b["text"] not in seen_buttons]
                if new_buttons:
                    logger.info(f"      New buttons: {[b['text'] for b in new_buttons]}")
                    for btn_info in new_buttons:
                        seen_buttons.add(btn_info["text"])
                        result["buttons"].append(btn_info)

                # extract page-level dropdowns
                tab_dropdowns = extract_page_dropdowns(page, context_label)
                if tab_dropdowns:
                    existing = {d.get("label") for d in result.get("page_dropdowns", [])}
                    new_dd = [d for d in tab_dropdowns if d["label"] not in existing]
                    if new_dd:
                        result.setdefault("page_dropdowns", []).extend(new_dd)
                        logger.info(f"      Page dropdowns: {[d['label'] for d in new_dd]}")

                # explore safe toolbar buttons
                for btn_info in new_buttons:
                    if not btn_info.get("safe_to_click"):
                        continue
                    dialog = extract_dialog(page, btn_info["text"], context_label)
                    if dialog:
                        result["dialogs"].append(dialog)
                        logger.info(f"      Dialog: [{btn_info['text']}] → {dialog.get('title', 'no title')}")
                        if dialog.get("fields"):
                            field_strs = [f["label"] + " (" + f["type"] + ")" for f in dialog.get("fields", [])]
                            logger.info("        Fields: %s", field_strs)

                # explore row-hover actions for each table
                for tbl in tab_tables:
                    hover_btns = extract_row_hover_actions(page, tbl.get("container", ""), context_label)
                    for hb in hover_btns:
                        if hb["text"] not in seen_buttons:
                            seen_buttons.add(hb["text"])
                            result["buttons"].append(hb)
                        if not hb.get("safe_to_click"):
                            continue
                        logger.info(f"      Extracting hover dialog: [{hb['text']}]")
                        container = tbl.get("container", "")
                        try:
                            # Hover row, then click with JS so mouse never leaves
                            row = (page.locator(f".{container} .sw-table-row:visible").first
                                   if container else page.locator(".sw-table-row:visible").first)
                            row.hover()
                            page.wait_for_timeout(800)

                            # JS click — keeps mouse on row, avoids hover-lose issue.
                            # Search by text, aria-label, title, and icon class patterns.
                            btn_text_escaped = hb['text'].replace("'", "\\'")
                            js_clicked = page.evaluate(f"""
                                (() => {{
                                    const target = '{btn_text_escaped}'.toLowerCase();
                                    const iconMap = {{
                                        'edit': ['icon-edit', 'icon-pencil', 'icon-edit-pencil'],
                                        'delete': ['icon-delete', 'icon-trash', 'icon-remove'],
                                        'configure': ['icon-configure', 'icon-gear', 'icon-settings'],
                                        'statistics': ['icon-statistics', 'icon-chart', 'icon-stats'],
                                    }};
                                    const iconClasses = iconMap[target] || [];
                                    const candidates = document.querySelectorAll(
                                        'button, .sw-icon-button, .sw-icon-button__label-cont, ' +
                                        '[class*="action-btn"], [class*="row-action"], [class*="icon-btn"], ' +
                                        '.sw-icon, span[class*="icon"], svg, [role="button"]'
                                    );
                                    for (const el of candidates) {{
                                        if (!el.offsetParent) continue;
                                        const text = (el.textContent || '').trim().toLowerCase();
                                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                                        const title = (el.getAttribute('title') || '').toLowerCase();
                                        const cls = (el.className || '').toString().toLowerCase();
                                        const parentCls = (el.parentElement?.className || '').toString().toLowerCase();
                                        const allStr = text + ' ' + aria + ' ' + title + ' ' + cls + ' ' + parentCls;
                                        if (allStr.includes(target)) {{
                                            // Click the button or its clickable parent
                                            (el.closest('button') || el.closest('[role="button"]') || el).click();
                                            return true;
                                        }}
                                        // Also check icon class patterns
                                        for (const ic of iconClasses) {{
                                            if (cls.includes(ic) || parentCls.includes(ic)) {{
                                                (el.closest('button') || el.closest('[role="button"]') || el).click();
                                                return true;
                                            }}
                                        }}
                                    }}
                                    return false;
                                }})()
                            """)

                            if js_clicked:
                                page.wait_for_timeout(1500)
                                modal = page.locator(".sw-modal:visible")
                                if modal.count() > 0:
                                    dialog = _extract_modal(page, modal.first, hb["text"])
                                    dialog["tab"] = context_label
                                    dialog["trigger_source"] = "row_hover"
                                    dialog["table_container"] = container
                                    result["dialogs"].append(dialog)
                                    _close_modal_safely(page, modal.first)
                                    page.wait_for_timeout(500)
                                    logger.info(f"      Row-hover dialog: [{hb['text']}] → {dialog.get('title', 'no title')}")
                                    if dialog.get("fields"):
                                        field_strs = [f["label"] + " (" + f["type"] + ")" for f in dialog.get("fields", [])]
                                        logger.info("        Fields: %s", field_strs)
                                else:
                                    popover = page.locator(".sw-popover__board:visible")
                                    if popover.count() > 0:
                                        dialog = _extract_popover(page, popover.first, hb["text"])
                                        dialog["tab"] = context_label
                                        dialog["trigger_source"] = "row_hover"
                                        dialog["table_container"] = container
                                        result["dialogs"].append(dialog)
                                        logger.info(f"      Row-hover popover: [{hb['text']}] → {dialog.get('title', '?')}")
                                    else:
                                        logger.info(f"      No dialog appeared after JS-click [{hb['text']}]")
                            else:
                                logger.info(f"      JS click for [{hb['text']}] found no element")

                            page.mouse.move(0, 0)
                            page.wait_for_timeout(300)
                        except Exception as e:
                            logger.warning(f"      Error extracting hover dialog [{hb['text']}]: {e}")

                # Fallback: try clicking on row identifier text (e.g., interface name "X0")
                # to discover "Edit Interface - X0" style dialogs triggered by row links.
                for tbl in tab_tables:
                    identifiers = tbl.get("row_identifiers", [])
                    if not identifiers or identifiers[0] == "No Data":
                        continue
                    first_id = identifiers[0]
                    container = tbl.get("container", "")
                    # Check if we've already captured a dialog triggered by a similar name
                    already_has = any(
                        first_id in d.get("title", "") for d in result["dialogs"]
                    )
                    if already_has:
                        continue
                    logger.info(f"      Trying row-identifier click: [{first_id}]")
                    try:
                        row = (page.locator(f".{container} .sw-table-row:visible").first
                               if container else page.locator(".sw-table-row:visible").first)
                        # Click the first text-bearing cell via JS
                        id_escaped = first_id.replace("'", "\\'")
                        clicked = page.evaluate(f"""
                            (() => {{
                                const cells = document.querySelectorAll('.sw-table-row__cell, .sw-table-row td');
                                for (const cell of cells) {{
                                    if (!cell.offsetParent) continue;
                                    const txt = (cell.textContent || '').trim();
                                    if (txt === '{id_escaped}') {{
                                        cell.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }})()
                        """)
                        if clicked:
                            page.wait_for_timeout(1500)
                            modal = page.locator(".sw-modal:visible")
                            if modal.count() > 0:
                                dialog = _extract_modal(page, modal.first, f"Click-{first_id}")
                                dialog["tab"] = context_label
                                dialog["trigger_source"] = "row_click"
                                dialog["table_container"] = container
                                result["dialogs"].append(dialog)
                                _close_modal_safely(page, modal.first)
                                page.wait_for_timeout(500)
                                logger.info(f"      Row-click dialog: [{first_id}] → {dialog.get('title', 'no title')}")
                                if dialog.get("fields"):
                                    field_strs = [f["label"] + " (" + f["type"] + ")" for f in dialog.get("fields", [])]
                                    logger.info("        Fields: %s", field_strs)
                            else:
                                logger.info(f"      No dialog after clicking row ID [{first_id}]")
                        else:
                            logger.info(f"      Could not find cell with text [{first_id}]")
                    except Exception as e:
                        logger.warning(f"      Error exploring row click [{first_id}]: {e}")

        except Exception as e:
            logger.warning(f"    Failed to explore tab [{l1_name}]: {e}")

    # ── Step 3: Also explore safe buttons from the initial scan that haven't been clicked yet ──
    for btn_info in result["buttons"]:
        if not btn_info.get("safe_to_click"):
            continue
        # Check if already explored
        already_explored = any(d.get("trigger") == btn_info["text"] for d in result["dialogs"])
        if not already_explored:
            dialog = extract_dialog(page, btn_info["text"], btn_info.get("tab", ""))
            if dialog:
                result["dialogs"].append(dialog)
                logger.info(f"  Dialog: [{btn_info['text']}] → {dialog.get('title', 'no title')}")

    return result


def manual_capture(page, feature_url: str) -> dict:
    """Interactive mode: user manually clicks UI, presses Enter to capture state.

    Opens the browser in headed mode. The user navigates the UI freely.
    Pressing Enter in the terminal captures the current visible page/dialog state.
    Type 'done' to finish and save.
    """
    # Navigate first
    target_url = f"{Settings.BASE_URL}{feature_url}"
    logger.info(f"Navigating to: {target_url}")
    page.goto(target_url, wait_until="domcontentloaded")
    try:
        page.locator(".sw-blocking-progress").wait_for(state="hidden", timeout=15000)
    except Exception:
        pass
    try:
        page.locator(".fw-app-main__blocking").wait_for(state="hidden", timeout=15000)
    except Exception:
        pass
    # Wait for actual page content to appear
    for selector in [".sw-tab--l1", ".sw-table", ".sw-form-row", ".sw-breadcrumb"]:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=5000)
            logger.info(f"  Content signal: '{selector}' appeared")
            break
        except Exception:
            pass
    page.wait_for_timeout(4000)

    captures = {
        "url": feature_url,
        "tabs": {},
        "tables": [],
        "buttons": [],
        "dialogs": [],
        "page_dropdowns": [],
        "snapshots": [],
    }

    print("\n" + "=" * 60)
    print("  MANUAL CAPTURE MODE")
    print("=" * 60)
    print("  [Enter]  → capture current page / dialog state")
    print("  'list'   → show captured so far")
    print("  'done'   → save and exit")
    print("=" * 60)

    snap_idx = 0
    while True:
        cmd = input("\n> ").strip()

        if cmd.lower() == "done":
            break

        if cmd.lower() == "list":
            print(f"\n  Captures so far:")
            print(f"    Tabs L1: {captures['tabs'].get('l1', [])}")
            print(f"    Tabs L2: {captures['tabs'].get('l2', [])}")
            print(f"    Tables:  {len(captures['tables'])}")
            print(f"    Buttons: {[b['text'] for b in captures['buttons']]}")
            print(f"    Dialogs: {len(captures['dialogs'])} → {[d.get('title','?') for d in captures['dialogs']]}")
            print(f"    Page dropdowns: {[d['label'] for d in captures['page_dropdowns']]}")
            continue

        # ── CAPTURE current state ──
        snap_idx += 1
        print(f"\n  [Snapshot #{snap_idx}] Capturing...")

        # Determine current active tab
        current_tab = ""
        try:
            active = page.locator(".sw-tab--l1.sw-tab--active")
            if active.count() > 0:
                current_tab = active.first.inner_text().strip()
        except Exception:
            pass
        # Check L2 active
        try:
            l2_active = page.locator(".sw-tab--l2.sw-tab--active")
            if l2_active.count() > 0:
                current_tab += "/" + l2_active.first.inner_text().strip()
        except Exception:
            pass

        print(f"    Active tab: [{current_tab}]")

        # Breadcrumb
        bc = extract_breadcrumb(page)
        if bc and bc != captures.get("breadcrumb", ""):
            captures["breadcrumb"] = bc
            print(f"    Breadcrumb: {bc}")

        # Tabs
        tabs = extract_tabs(page)
        if tabs["l1"]:
            captures["tabs"]["l1"] = list(set(captures["tabs"].get("l1", []) + tabs["l1"]))
        if tabs["l2"]:
            captures["tabs"]["l2"] = list(set(captures["tabs"].get("l2", []) + tabs["l2"]))
        print(f"    Tabs: L1={tabs['l1']}, L2={tabs['l2']}")

        # Tables
        page_tables = extract_tables_in_view(page, current_tab)
        for t in page_tables:
            if t not in captures["tables"]:
                captures["tables"].append(t)
        print(f"    Tables in view: {len(page_tables)}")

        # Buttons
        bns = extract_buttons(page, current_tab)
        for b in bns:
            if b["text"] not in {x["text"] for x in captures["buttons"]}:
                captures["buttons"].append(b)
        print(f"    Buttons: {[b['text'] for b in bns]}")

        # Dropdowns
        dds = extract_page_dropdowns(page, current_tab)
        for d in dds:
            if d not in captures["page_dropdowns"]:
                captures["page_dropdowns"].append(d)

        # ── Dialog / Popover / Confirm Dialog capture ──
        # NOTE: check confirm dialog BEFORE modal — confirm dialogs are often
        # wrapped in a .sw-modal overlay container, so we need to detect them first.
        confirm = page.locator(".sw-confirm-modal__dialog:visible")
        modal = page.locator(".sw-modal:visible")
        popover = page.locator(".sw-popover__board:visible")

        if confirm.count() > 0:
            dialog = _extract_confirm_dialog(confirm.first, f"manual#{snap_idx}")
            dialog["tab"] = current_tab
            captures["dialogs"].append(dialog)
            print(f"    ✓ Confirm dialog captured:")
            print(f"      Messages: {dialog.get('title', '?')}")
            print(f"      Buttons: {dialog.get('buttons', [])}")
        if modal.count() > 0 and confirm.count() == 0:
            # only treat as regular modal if no confirm dialog is inside it
            dialog = _extract_modal(page, modal.first, f"manual#{snap_idx}")
            dialog["tab"] = current_tab
            captures["dialogs"].append(dialog)
            print(f"    ✓ Modal captured: {dialog.get('title', '?')}")
            print(f"      Fields: {[(f['label'], f['type']) for f in dialog.get('fields', [])]}")
        if popover.count() > 0 and confirm.count() == 0:
            dialog = _extract_popover(page, popover.first, f"manual#{snap_idx}")
            dialog["tab"] = current_tab
            captures["dialogs"].append(dialog)
            print(f"    ✓ Popover captured: {dialog.get('title', '?')}")
        if confirm.count() == 0 and modal.count() == 0 and popover.count() == 0:
            print(f"    (no dialog/popover visible)")

    return captures


def main():
    parser = argparse.ArgumentParser(description="Extract page skeleton from SonicOS 7 firewall UI")
    parser.add_argument("--feature", required=True, help="Feature name (e.g., arp, client_ssl)")
    parser.add_argument("--url", required=True, help="URL path (e.g., /m/mgmt/network/arp)")
    parser.add_argument("--fw_ip", default="192.168.168.168", help="Firewall IP address")
    parser.add_argument("--password", default="S0nic@uto", help="Login password")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--manual", action="store_true", help="Manual capture mode: click UI yourself, press Enter to capture")
    parser.add_argument("--output", help="Output JSON file path (default: test_data/page_structure/{feature}_structure.json)")
    args = parser.parse_args()

    # apply settings overrides
    Settings.FIREWALL_IP = args.fw_ip
    Settings.BASE_URL = f"https://{args.fw_ip}/sonicui/7"
    Settings.PASSWORD = args.password

    logger.info(f"Page Inspector — feature: {args.feature}, url: {args.url}, fw: {args.fw_ip}")

    with sync_playwright() as p:
        # Manual mode always requires headed
        headless = not args.headed and not args.manual
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            login_to_firewall(page, args.username, args.password)
            if args.manual:
                result = manual_capture(page, args.url)
            else:
                result = explore_page(page, args.url, args.feature)
        finally:
            context.close()
            browser.close()

    # determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = _project_root / "test_data" / "page_structure"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{args.feature}_structure.json"

    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Page structure saved to: {output_path}")

    # print summary
    print("\n" + "=" * 60)
    print(f"PAGE STRUCTURE SUMMARY: {args.feature}")
    print("=" * 60)
    print(f"  URL:         {result['url']}")
    print(f"  Breadcrumb:  {result['breadcrumb']}")
    print(f"  Tabs L1:     {result['tabs']['l1']}")
    print(f"  Tabs L2:     {result['tabs']['l2']}")
    print(f"  Tables:      {len(result['tables'])}")
    for t in result["tables"]:
        ids = t.get("row_identifiers", [])
        cols = t.get("column_types", {})
        print(f"    - [{t['tab'] or 'default'}] container={t['container']}, rows={t['row_count']}")
        if ids:
            print(f"        identifiers: {ids[:8]}{'...' if len(ids) > 8 else ''}")
        if cols:
            non_text = {k: v for k, v in cols.items() if v != "text"}
            if non_text:
                print(f"        column_types: {non_text}")
    print(f"  Dropdowns:   {[d['label'] for d in result.get('page_dropdowns', [])]}")
    print(f"  Buttons:     {[b['text'] for b in result['buttons']]}")
    hover_btns = [b for b in result['buttons'] if b.get('type') == 'row_hover_button']
    if hover_btns:
        print(f"  Row-hover:   {[b['text'] for b in hover_btns]}")
    print(f"  Dialogs:     {len(result['dialogs'])}")
    for d in result["dialogs"]:
        source = " (row-hover)" if d.get("trigger_source") == "row_hover" else ""
        print(f"    - [{d['trigger']}]{source} → {d.get('title', 'no title')}")
        for f in d.get("fields", []):
            required = " *" if f.get("required") else ""
            print(f"        {f['label']}{required}: {f['type']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
