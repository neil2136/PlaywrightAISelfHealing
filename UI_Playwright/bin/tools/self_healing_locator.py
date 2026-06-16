"""
Self-Healing Locator Engine — reusable module for AI-powered test self-healing.

Integrates with pytest and Playwright to automatically detect, heal, and
report broken locators during test execution.

Features (v2.0):
  - Rule-based fallback: tries pattern-matching first (no API call, covers ~60-70%)
  - Cache layer: same broken selector + URL → instant cache hit (no API call)
  - Auto-retry: @self_heal(auto_retry=True) actually retries with healed locator

Usage in tests:
    from tools.self_healing_locator import SelfHealingLocator

    def test_something(fw_page):
        healer = SelfHealingLocator(fw_page.page)
        try:
            fw_page.page.locator('.old-selector').click(timeout=5000)
        except Exception:
            result = healer.heal(
                '.old-selector',
                'Click the Add button on the toolbar',
            )
            if result['success']:
                fw_page.page.locator(result['healed_selector']).click()

Usage in Page Objects (decorator pattern):
    from tools.self_healing_locator import self_heal

    # Diagnose only (CI safe)
    @self_heal("Click the Add button to open the Add dialog")
    def click_add_button(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

    # Auto-retry (dev/debug mode) — actually recovers
    @self_heal("Click the Add button", auto_retry=True)
    def click_add_button_v2(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()
"""

import inspect
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Callable, Optional

# Make bin/ importable
_project_root = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(_project_root))

from config.logger import get_logger

logger = get_logger("self_healing")


def _load_api_key(name: str) -> str:
    """Load an API key from env var or bin/config/api_keys.json.

    Priority: env var > config file > empty string
    """
    env_val = os.environ.get(name, "")
    if env_val:
        return env_val
    # Try project config file
    config_path = _project_root / "config" / "api_keys.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get(name.lower(), "") or ""
        except (json.JSONDecodeError, OSError):
            pass
    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  Pluggable AI backends for self-healing
# ═══════════════════════════════════════════════════════════════════════════

class HealingBackend:
    """Abstract base for AI backends that generate locator candidates."""

    def heal(self, prompt: str, page_url: str = "") -> str:
        """Send prompt to AI, return raw response text."""
        raise NotImplementedError


class GLMBackend(HealingBackend):
    """Zhipu GLM API (default, existing)."""

    def __init__(self, api_key: str = "", model: str = "glm-4-flash"):
        self.api_key = api_key or _load_api_key("ZHIPU_API_KEY")
        self.model = model

    def heal(self, prompt: str, page_url: str = "") -> str:
        import urllib.request

        if not self.api_key:
            raise RuntimeError("ZHIPU_API_KEY not set — set env var or pass api_key")

        data = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]


class ClaudeBackend(HealingBackend):
    """Anthropic Claude API backend."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or _load_api_key("ANTHROPIC_API_KEY")
        self.model = model

    def heal(self, prompt: str, page_url: str = "") -> str:
        import urllib.request

        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — set env var or pass api_key")

        data = json.dumps({
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            # Anthropic returns content blocks
            for block in body.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
            return body["content"][0]["text"]


class MCPBackend(HealingBackend):
    """MCP backend — pytest writes request, CLI agent (demo_mcp.sh) heals it.

    TWO-TERMINAL WORKFLOW:
      Terminal 1 (pytest): test fails → @self_heal → writes mcp_request.json
      Terminal 2 (CLI):    AI reads request → uses MCP tools → writes mcp_response.json
      Terminal 1 (pytest): reads mcp_response.json → retries with healed selector → PASS

    This keeps the true MCP demo experience: the CLI agent calls
    mcp__playwright__browser_navigate / browser_snapshot / browser_evaluate
    to explore the live page and find the correct locator.
    """

    REQUEST_FILE = str(_project_root / "test_data" / "healing_reports" / "mcp_request.json")
    RESPONSE_FILE = str(_project_root / "test_data" / "healing_reports" / "mcp_response.json")

    def __init__(self, timeout: int = 30, demo: bool = False):
        self.timeout = timeout
        self.demo = demo

    def heal(self, prompt: str, page_url: str = "") -> str:
        # ── Extract context from the prompt ──
        broken_match = re.search(r'Broken Selector\s*\n\s*`([^`]+)`', prompt)
        broken_sel = broken_match.group(1).strip() if broken_match else ""
        target_match = re.search(r'Target Element\s*\n\s*(.+?)(?:\n##|\n```|\n\Z)', prompt, re.DOTALL)
        target_desc = target_match.group(1).strip() if target_match else ""
        page_url = page_url or self._extract_url_from_prompt(prompt)

        # ── Parse page structure from prompt ──
        page_summary = ""
        page_buttons = []
        page_tabs = []
        json_match = re.search(r'\{[\s\S]*"url"[\s\S]*\}', prompt)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                btn_count = len(parsed.get("buttons", []))
                input_count = len(parsed.get("inputs", []))
                tab_count = len(parsed.get("tabs", []))
                dialog_count = len(parsed.get("dialogs", []))
                page_summary = (
                    f"Page has {btn_count} buttons, {input_count} inputs, "
                    f"{tab_count} tabs, {dialog_count} dialogs"
                )
                page_buttons = [b.get("text", "")[:50] for b in parsed.get("buttons", [])[:15]]
                page_tabs = [t.get("text", "")[:30] for t in parsed.get("tabs", [])[:10]]
            except json.JSONDecodeError:
                pass

        # ── Build MCP instructions for CLI agent ──
        instructions = (
            f"Use MCP playwright tools to find the correct locator:\n"
            f"1. browser_login(fw_ip=\"10.8.165.150\", username=\"admin\", password=\"S0nic@uto\")\n"
            f"2. browser_navigate(url=\"{page_url}\")\n"
            f"3. If the element is in a dialog: browser_click the button that opens it first\n"
            f"4. browser_snapshot() to see all interactive elements\n"
            f"5. browser_evaluate(selector) to test each candidate\n"
            f"6. For buttons with duplicate text (e.g. two Cancel), use:\n"
            f"   - More specific parent: .sw-modal button:has-text('Cancel')\n"
            f"   - Nth match: button:has-text('Cancel') >> nth=0\n"
            f"7. Write your best candidates as JSON to {self.RESPONSE_FILE}"
        )

        request = {
            "broken_selector": broken_sel,
            "element_description": target_desc,
            "page_url": page_url,
            "page_summary": page_summary,
            "page_buttons": page_buttons,
            "page_tabs": page_tabs,
            "timestamp": datetime.now().isoformat(),
            "instructions": instructions,
        }
        Path(self.REQUEST_FILE).write_text(json.dumps(request, indent=2, ensure_ascii=False))

        logger.info(f"  📤 MCP request → {self.REQUEST_FILE}")
        logger.info(f"  🌐 Page URL: {page_url}")
        logger.info(f"  📣 Switch to CLI agent and say: 'heal the selector in mcp_request.json'")

        # ── Check for cached response (from previous CLI agent run) ──
        if Path(self.RESPONSE_FILE).exists():
            try:
                response = json.loads(Path(self.RESPONSE_FILE).read_text())
                done_path = Path(str(self.RESPONSE_FILE).replace('.json', '.done.json'))
                Path(self.RESPONSE_FILE).rename(done_path)
                logger.info(f"  ✅ MCP response applied (archived to {done_path.name})")
                return response.get("response", "")
            except (json.JSONDecodeError, KeyError):
                pass

        # ── No response yet — pause for CLI agent, return fallback ──
        logger.info("  ⏩ Waiting for CLI agent to write mcp_response.json...")
        # Sleep briefly so the CLI agent has time; in real CI this would block longer
        for _ in range(self.timeout):
            time.sleep(1)
            if Path(self.RESPONSE_FILE).exists():
                try:
                    response = json.loads(Path(self.RESPONSE_FILE).read_text())
                    done_path = Path(str(self.RESPONSE_FILE).replace('.json', '.done.json'))
                    Path(self.RESPONSE_FILE).rename(done_path)
                    logger.info(f"  ✅ MCP response received (waited {_+1}s)")
                    return response.get("response", "")
                except (json.JSONDecodeError, KeyError):
                    pass

        # Timeout — use text fallback
        logger.info(f"  ⏩ MCP timeout ({self.timeout}s) — using text fallback")
        return json.dumps({
            "candidates": [
                {"selector": f'text="{self._guess_keyword(prompt)}"',
                 "strategy": "text", "confidence": "low",
                 "reasoning": "MCP timeout fallback — run CLI agent to heal properly"}
            ]
        })

    @staticmethod
    def _extract_url_from_prompt(prompt: str) -> str:
        m = re.search(r'"url":\s*"([^"]+)"', prompt)
        return m.group(1) if m else ""

    @staticmethod
    def _guess_keyword(prompt: str) -> str:
        for line in prompt.split('\n'):
            if 'Target Element' in line or 'Click the' in line:
                words = re.findall(r'"([^"]+)"', line)
                if words:
                    return words[0]
                action = re.findall(
                    r'\b(Add|Delete|Cancel|Edit|OK|Save|Close|Search|'
                    r'Refresh|Export|Apply|Submit|Remove)\b', line, re.IGNORECASE
                )
                if action:
                    return action[0]
        return "Unknown"


# ── Backend factory ──

def _resolve_backend(backend: str | HealingBackend) -> HealingBackend:
    """Resolve a backend name or instance to a HealingBackend object.

    Accepted names:
        "glm"    → GLMBackend (default)
        "claude" → ClaudeBackend
        "mcp"    → MCPBackend (demo mode)
    """
    if isinstance(backend, HealingBackend):
        return backend
    name = backend.lower()
    if name == "glm":
        return GLMBackend()
    elif name == "claude":
        return ClaudeBackend()
    elif name == "mcp":
        return MCPBackend()
    else:
        raise ValueError(
            f"Unknown AI backend: '{backend}'. "
            f"Use 'glm', 'claude', 'mcp', or pass a HealingBackend instance."
        )


class SelfHealingLocator:
    """Heals broken Playwright locators by extracting page structure and using AI.

    Features (v2.0):
    - Rule-based fallback: tries pattern-matching first (no API call, covers ~60-70%)
    - Cache layer: same broken selector + URL -> instant cache hit (no API call)
    - Auto-retry: @self_heal(auto_retry=True) actually retries with healed locator
    """

    # Class-level cache: shared across all instances to avoid redundant AI calls
    _heal_cache: dict = {}

    # Common SonicWall CSS class name changes across firmware versions
    _CLASS_SUBSTITUTIONS = [
        ("sw-icon-button__label-cont", "sw-action-button__label-text"),
        ("sw-icon-button", "sw-action-button"),
        ("sw-select__label-cont", "sw-dropdown__label-cont"),
        ("sw-select__label-text", "sw-dropdown__label-text"),
        ("sw-modal", "sw-dialog"),
        ("sw-modal__title", "sw-dialog__title"),
        ("sw-popover__board", "sw-popover__panel"),
        ("sw-table-body__cont__table", "sw-table__body"),
        ("sw-status-info__text__message", "sw-alert__message"),
    

        # [rule-update 2026-06-16 02:29] AI healed `static-entry-modal__modal-footer-cancel-old` → `static-entry-modal__modal-footer-cancel`
        ("static-entry-modal__modal-footer-cancel-old", "static-entry-modal__modal-footer-cancel"),
]

    def __init__(self, page, ai_callable: Optional[Callable] = None,
                 ai_backend: str | HealingBackend = "glm",
                 enable_cache: bool = True, enable_rules: bool = True):
        """
        Args:
            page: Playwright Page object
            ai_callable: Optional custom AI function(prompt) -> str.
                         If None, uses the backend specified by `ai_backend`.
                         (Deprecated — prefer ai_backend.)
            ai_backend: Backend name or instance. Built-in options:
                        "glm" (default), "claude", "mcp" (demo).
                        Or pass any HealingBackend instance.
            enable_cache: Use in-memory cache to avoid redundant AI calls (default True).
            enable_rules: Try rule-based candidates before calling AI (default True).
        """
        self.page = page
        self.ai_backend = _resolve_backend(ai_backend)
        # Manual ai_callable takes precedence over backend
        self.ai_callable = ai_callable or self.ai_backend.heal
        self.healing_log = []
        self.enable_cache = enable_cache
        self.enable_rules = enable_rules

    # ── Page structure extraction ──

    def extract_page_elements(self) -> dict:
        """Extract interactive elements from current page as structured JSON."""
        try:
            return self.page.evaluate("""() => {
                const result = {
                    url: window.location.href,
                    inputs: [], buttons: [], tabs: [], tables: [],
                    selects: [], toggles: [], headings: [], links: []
                };

                document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
                    if (!el.offsetParent) return;
                    result.inputs.push({
                        type: el.type || 'text', name: el.name || '',
                        id: el.id || '', placeholder: el.placeholder || '',
                        className: (el.className || '').substring(0, 100),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        labelText: (() => {
                            const row = el.closest('[class*="form-row"], [class*="field"]');
                            if (row) {
                                const lbl = row.querySelector('[class*="label"]');
                                if (lbl) return lbl.textContent.trim().substring(0, 50);
                            }
                            const label = el.closest('label');
                            if (label) return label.textContent.trim().substring(0, 50);
                            return '';
                        })()
                    });
                });

                document.querySelectorAll(
                    'button, [role="button"], .sw-icon-button, .sw-button, ' +
                    '.sw-icon-button__label-cont, .sw-action-button, .sw-action-button__label-text, ' +
                    '[class*="icon-btn"], [class*="action-btn"], [class*="button"]'
                ).forEach(el => {
                    if (!el.offsetParent) return;
                    const text = (el.textContent || '').trim().substring(0, 80);
                    if (text || el.getAttribute('aria-label')) {
                        result.buttons.push({
                            tag: el.tagName.toLowerCase(),
                            text: text,
                            id: el.id || '',
                            name: el.name || el.getAttribute('aria-label') || '',
                            className: (el.className || '').substring(0, 120),
                        });
                    }
                });

                document.querySelectorAll('.sw-tab--l1, .sw-tab--l2, [role="tab"]').forEach(el => {
                    if (!el.offsetParent) return;
                    const text = (el.textContent || '').trim();
                    if (text && text.length < 50) {
                        result.tabs.push({
                            text: text,
                            className: (el.className || '').substring(0, 120),
                            isActive: el.classList.contains('sw-tab--active') ||
                                      el.getAttribute('aria-selected') === 'true'
                        });
                    }
                });

                document.querySelectorAll('.sw-table').forEach((el, i) => {
                    if (!el.offsetParent) return;
                    const headers = [...el.querySelectorAll('.sw-table-header > div, th')]
                        .map(h => h.textContent.trim()).filter(h => h);
                    if (headers.length) {
                        result.tables.push({
                            index: i, headers: headers,
                            containerClass: (el.parentElement?.className || '').substring(0, 120),
                            rowCount: el.querySelectorAll('.sw-table-row, tbody tr').length
                        });
                    }
                });

                document.querySelectorAll('.sw-select, select').forEach(el => {
                    if (!el.offsetParent) return;
                    const input = el.querySelector('input');
                    result.selects.push({
                        name: input ? (input.name || '') : (el.name || ''),
                        currentValue: (el.querySelector('.sw-select__label-text') || el)
                            .textContent.trim().substring(0, 50)
                    });
                });

                document.querySelectorAll('.sw-toggle, input[type="checkbox"]').forEach(el => {
                    if (!el.offsetParent) return;
                    result.toggles.push({
                        name: (el.querySelector('input') || el).name || '',
                        className: (el.className || '').substring(0, 80)
                    });
                });

                document.querySelectorAll('.sw-modal__title, .sw-breadcrumb, h1, h2, h3')
                    .forEach(el => {
                        if (!el.offsetParent) return;
                        const t = el.textContent.trim().substring(0, 100);
                        if (t) result.headings.push(t);
                    });

                document.querySelectorAll('a[href]').forEach(el => {
                    if (!el.offsetParent) return;
                    result.links.push({
                        text: (el.textContent || '').trim().substring(0, 60),
                        href: el.getAttribute('href') || ''
                    });
                });

                return result;
            }""")
        except Exception as e:
            logger.error(f"Failed to extract page elements: {e}")
            return {"url": "", "inputs": [], "buttons": [], "tabs": [],
                    "tables": [], "selects": [], "toggles": [], "headings": [], "links": []}

    # ── Rule-based candidate generation (no API call) ──

    def _rule_based_candidates(self, broken_selector: str, element_description: str,
                                page_elements: dict) -> list:
        """Generate candidate selectors using pattern-matching rules (no AI).

        Covers 60-70% of common locator failures without any API call.
        """
        candidates = []
        desc_lower = element_description.lower()

        # 1) Extract quoted text from the description
        quoted_words = re.findall(r'"([^"]+)"', element_description)
        # 2) Also extract important action words
        action_words = re.findall(
            r'\b(Add|Delete|Edit|Update|Refresh|Export|Statistics|Cancel|OK|'
            r'Apply|Save|Configure|Search|Flush|Clear|Remove|Enable|Disable|'
            r'Close|Next|Previous|Submit|Reset|Accept|Reject|Import)\b',
            element_description, re.IGNORECASE
        )
        key_words = list(dict.fromkeys(quoted_words + action_words))

        if not key_words:
            general_words = re.findall(
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', element_description
            )
            key_words = general_words[:3]

        # Determine element type from description + broken selector
        broken_lower = broken_selector.lower()
        is_button = any(kw in desc_lower for kw in
                        ["button", "click", "icon", "toolbar", "action"])
        is_button = is_button or "button" in broken_lower or "icon-button" in broken_lower
        is_tab = "tab" in desc_lower or "tab" in broken_lower
        is_input = any(kw in desc_lower for kw in
                       ["input", "fill", "textbox", "field", "enter", "type"])
        is_toggle = "toggle" in desc_lower or "toggle" in broken_lower
        is_dropdown = any(kw in desc_lower for kw in
                          ["dropdown", "select", "combo", "drop-down"])

        # ── Class-name substitution candidates (PRIORITY — most likely to work) ──
        # These go first because SonicWall firmware updates most commonly rename classes
        for old_class, new_class in self._CLASS_SUBSTITUTIONS:
            if old_class in broken_selector:
                candidates.append({
                    "selector": broken_selector.replace(old_class, new_class),
                    "strategy": "css", "confidence": "high",
                    "reasoning": f"Rule: '{old_class}' -> '{new_class}' (common SDK rename)",
                })

        # ── PRIORITY 2: Page-element class-based candidates (MOST specific) ──
        # These use actual CSS classes found in the live DOM for the target element.
        # They're more specific than the generic fallbacks below because they include
        # the element tag + real class name + has-text — e.g.
        #   button.static-entry-modal__modal-footer-cancel:has-text("Cancel")
        # Generated BEFORE the generic fallbacks so they don't get truncated by the
        # 8-candidate limit at the end of this method.
        if is_button and page_elements.get("buttons"):
            for btn in page_elements["buttons"][:5]:
                btn_text = btn.get("text", "").strip()
                if btn_text and len(btn_text) < 60:
                    for kw in key_words:
                        if kw.lower() in btn_text.lower():
                            cls_str = btn.get("className", "")
                            if cls_str:
                                # Sort classes by length desc — longer = more specific
                                classes = sorted(
                                    [c for c in cls_str.split() if len(c) > 5],
                                    key=len, reverse=True
                                )
                                tag = btn.get("tag", "")

                                # COMBINED class selector first (most specific):
                                # button.sw-btn.sw-btn--secondary.static-modal__cancel:has-text("Cancel")
                                # This is far more specific than any single-class selector
                                # and avoids matching hidden background buttons.
                                if len(classes) >= 2:
                                    combined = '.'.join([''] + classes)  # .cls1.cls2.cls3
                                    if tag:
                                        combined_sel = f'{tag}{combined}:has-text("{btn_text}")'
                                    else:
                                        combined_sel = f'{combined}:has-text("{btn_text}")'
                                    candidates.append({
                                        "selector": combined_sel,
                                        "strategy": "css", "confidence": "high",
                                        "reasoning": f"Rule: Combined classes from page DOM (tag={tag})",
                                    })

                                # Then individual class selectors
                                for cls in classes[:3]:
                                    if tag:
                                        selector = f'{tag}.{cls}:has-text("{btn_text}")'
                                    else:
                                        selector = f'.{cls}:has-text("{btn_text}")'
                                    candidates.append({
                                        "selector": selector,
                                        "strategy": "css", "confidence": "high",
                                        "reasoning": f"Rule: Actual class .{cls} from page DOM (tag={tag})",
                                    })
                            break

        # ── Generic fallback candidates (lower priority) ──

        # ── Button candidates ──
        if is_button and key_words:
            for word in key_words[:3]:
                candidates.append({
                    "selector": f'text="{word}"',
                    "strategy": "text", "confidence": "medium",
                    "reasoning": f'Rule: text="{word}" — immune to CSS changes',
                })
                candidates.append({
                    "selector": f'button:has-text("{word}")',
                    "strategy": "css", "confidence": "medium",
                    "reasoning": f'Rule: button:has-text("{word}")',
                })
                candidates.append({
                    "selector": f'getByRole("button", {{name: "{word}"}})',
                    "strategy": "role", "confidence": "high",
                    "reasoning": f'Rule: getByRole button with name="{word}"',
                })
                candidates.append({
                    "selector": f'[aria-label*="{word}"]',
                    "strategy": "css", "confidence": "low",
                    "reasoning": f'Rule: [aria-label*="{word}"]',
                })

        # ── Tab candidates ──
        if is_tab and key_words:
            for word in key_words[:2]:
                candidates.append({
                    "selector": f'.sw-tab--l1:has-text("{word}")',
                    "strategy": "css", "confidence": "high",
                    "reasoning": f'Rule: SonicOS L1 tab with text="{word}"',
                })
                candidates.append({
                    "selector": f'[role="tab"]:has-text("{word}")',
                    "strategy": "css", "confidence": "high",
                    "reasoning": f'Rule: ARIA tab with name="{word}"',
                })

        # ── Input candidates ──
        if is_input and key_words:
            for word in key_words[:2]:
                name_slug = re.sub(r'\s+', '', word).lower()
                candidates.append({
                    "selector": f'input[name*="{name_slug}" i]',
                    "strategy": "css", "confidence": "medium",
                    "reasoning": f'Rule: input[name*="{name_slug}"]',
                })
                candidates.append({
                    "selector": f'input[placeholder*="{word}" i]',
                    "strategy": "css", "confidence": "medium",
                    "reasoning": f'Rule: input[placeholder*="{word}"]',
                })

        # ── Toggle candidates ──
        if is_toggle and key_words:
            for word in key_words[:2]:
                candidates.append({
                    "selector": f'.sw-toggle:has(input[name*="{word}" i])',
                    "strategy": "css", "confidence": "medium",
                    "reasoning": f'Rule: .sw-toggle input[name*="{word}"]',
                })

        # ── Dropdown candidates ──
        if is_dropdown and key_words:
            for word in key_words[:2]:
                candidates.append({
                    "selector": f'.sw-select:has-text("{word}")',
                    "strategy": "css", "confidence": "medium",
                    "reasoning": f'Rule: .sw-select containing="{word}"',
                })

        # Safety net
        if not candidates:
            candidates = [
                {
                    "selector": broken_selector.replace(
                        "sw-icon-button__label-cont", "sw-action-button__label-text"
                    ),
                    "strategy": "css", "confidence": "low",
                    "reasoning": "Fallback: try most common class rename",
                },
                {
                    "selector": 'text="' + (key_words[0] if key_words else "Add") + '"',
                    "strategy": "text", "confidence": "low",
                    "reasoning": "Last-resort text match",
                },
            ]

        return candidates[:12]

    @staticmethod
    def _detect_selector_strategy(selector: str) -> str:
        """Detect the strategy category of a selector.

        Categories (roughly most-robust to least):
        - 'role'    — getByRole(...)
        - 'class'   — uses actual .class-name(s)
        - 'css'     — other CSS (id #, attribute [...], element > combo, ...)
        - 'pseudo'  — :has-text / :has without a real class
        - 'text'    — text="..."
        """
        if 'getByRole' in selector:
            return 'role'
        if selector.startswith('text='):
            return 'text'
        # Contains a real CSS class? (dot followed by letter, not just . in :has-text)
        has_class = bool(re.search(r'\.([a-zA-Z_-][\w-]*)', selector))
        if has_class:
            return 'class'
        if ':has-text' in selector or ':has(' in selector:
            return 'pseudo'
        if any(c in selector for c in ('#', '[', '>', '+', '~')):
            return 'css'
        return 'css'  # default (element selector, etc.)

    @staticmethod
    def _extract_class_names(selector: str) -> list:
        """Extract CSS class names (the parts after dots) from a selector string."""
        return re.findall(r'\.([a-zA-Z_-][\w-]+)', selector)

    @staticmethod
    def _extract_intent_keywords(selector: str) -> set:
        """Extract meaningful words from a broken selector's class names.

        e.g. 'static-entry-modal__modal-footer-cancel-old'
        → {'cancel', 'modal', 'footer', 'entry', 'static'}
        These are used to match candidates to the INTENDED target element.
        """
        classes = SelfHealingLocator._extract_class_names(selector)
        words = set()
        # Split on all common delimiters: __, --, -, _
        for cls in classes:
            for part in re.split(r'__|--|[-_]', cls):
                part_lower = part.lower()
                # Filter out noise words
                if part_lower and len(part_lower) > 2 and part_lower not in (
                    'old', 'new', 'cont', 'text', 'label', 'icon', 'auto',
                    'btn', 'sw', 'the', 'and', 'for',
                ):
                    words.add(part_lower)
        return words

    def _text_relevance(self, intent_keywords: set, candidate_selector: str) -> float:
        """How relevant is a candidate's text to the intended target?

        Checks whether :has-text("...") or text="..." in the candidate
        matches any of the intent keywords derived from the broken selector.
        Returns 0.0 (no match) to 1.0 (exact keyword match).
        """
        if not intent_keywords:
            return 0.0
        # Extract the text portion from the candidate
        # :has-text("X"), text="X", getByRole(..., {name: "X"})
        text_matches = re.findall(r':has-text\("([^"]+)"\)', candidate_selector)
        text_matches += re.findall(r'text="([^"]+)"', candidate_selector)
        text_matches += re.findall(r'name:\s*"([^"]+)"', candidate_selector)
        if not text_matches:
            return 0.0
        for text in text_matches:
            text_lower = text.lower()
            for kw in intent_keywords:
                if kw in text_lower or text_lower in kw:
                    return 1.0
        return 0.0

    def _class_similarity(self, broken_class: str, candidate_selector: str) -> float:
        """How similar are the class names in a candidate to the broken class?

        Returns 0.0–1.0. 1.0 = exact match; partial substring matches get
        proportional scores. Only used when the broken selector was class-based.
        """
        cand_classes = self._extract_class_names(candidate_selector)
        if not cand_classes or not broken_class:
            return 0.0
        # Exact match
        if broken_class in cand_classes:
            return 1.0
        # Substring overlap — "modal-footer-cancel" vs "modal-footer-cancel-old"
        for cc in cand_classes:
            if broken_class in cc or cc in broken_class:
                longer = max(len(broken_class), len(cc))
                shorter = min(len(broken_class), len(cc))
                return shorter / longer if longer > 0 else 0.0
        return 0.0

    def _try_rule_based_heal(self, broken_selector: str, element_description: str,
                              page_elements: dict) -> dict | None:
        """Try to heal the locator using rule-based candidates (no LLM call).

        Prefers candidates that use the same strategy as the broken selector.
        For class-based selectors, this means preferring candidates that also
        use actual CSS class names — not :has-text() pseudo-selectors.
        """
        candidates = self._rule_based_candidates(
            broken_selector, element_description, page_elements
        )
        if not candidates:
            return None

        logger.info(f"  🧩 Rule engine generated {len(candidates)} candidates")
        original_strategy = self._detect_selector_strategy(broken_selector)
        broken_classes = self._extract_class_names(broken_selector)
        intent_keywords = self._extract_intent_keywords(broken_selector)

        # Validate all rule-based candidates against the live page
        validations = [self.validate_candidate(c["selector"]) for c in candidates]

        # ── Collect all "ideal" candidates (exactly 1 visible match) ──
        ideal_candidates = [
            (c, v) for c, v in zip(candidates, validations) if v.get("ideal")
        ]
        if ideal_candidates:
            # If we have intent keywords, only accept ideal candidates that
            # actually match the intent. Otherwise a wrong-button candidate
            # (e.g. "Add" button for a "Cancel" broken selector) could win.
            if intent_keywords:
                intent_ideals = [
                    (c, v) for c, v in ideal_candidates
                    if self._text_relevance(intent_keywords, c["selector"]) > 0
                ]
                if intent_ideals:
                    picked_c, picked_v, strategy_note = self._pick_best_candidate(
                        intent_ideals, original_strategy, broken_classes, intent_keywords
                    )
                    logger.info(f"  ✅ Rule-based hit ({strategy_note}): `{picked_c['selector']}` "
                               f"— skipping AI call")
                    return {
                        "healed_selector": picked_c["selector"],
                        "success": True,
                        "candidates": [{**picked_c, **picked_v, "score": 110}],
                        "healing_event": {
                            "timestamp": datetime.now().isoformat(),
                            "broken_selector": broken_selector,
                            "element_description": element_description,
                            "method": "rule_based",
                            "healed_selector": picked_c["selector"],
                            "success": True,
                            "strategy_match": "same" in strategy_note,
                        },
                    }
                # else: intent_ideals empty — fall through to keyword_candidates
            else:
                picked_c, picked_v, strategy_note = self._pick_best_candidate(
                    ideal_candidates, original_strategy, broken_classes, intent_keywords
                )
                logger.info(f"  ✅ Rule-based hit ({strategy_note}): `{picked_c['selector']}` "
                           f"— skipping AI call")
                return {
                    "healed_selector": picked_c["selector"],
                    "success": True,
                    "candidates": [{**picked_c, **picked_v, "score": 110}],
                    "healing_event": {
                        "timestamp": datetime.now().isoformat(),
                        "broken_selector": broken_selector,
                        "element_description": element_description,
                        "method": "rule_based",
                        "healed_selector": picked_c["selector"],
                        "success": True,
                        "strategy_match": "same" in strategy_note,
                    },
                }

        # ── Intent-keyword match with elements on page ──
        # When the button only has generic framework classes (e.g. sw-btn),
        # even the combined class selector may match multiple hidden background
        # buttons (count > 1, first hidden → is_visible=False). But Playwright's
        # .click() skips display:none elements and hits the first visible one,
        # so we accept any keyword-matching candidate with count > 0.
        if intent_keywords:
            keyword_candidates = [
                (c, v) for c, v in zip(candidates, validations)
                if (v.get("valid") and v.get("count", 0) > 0 and
                    self._text_relevance(intent_keywords, c["selector"]) > 0)
            ]
            if keyword_candidates:
                picked_c, picked_v, strategy_note = self._pick_best_candidate(
                    keyword_candidates, original_strategy, broken_classes, intent_keywords
                )
                logger.info(f"  🟢 Rule-based hit ({strategy_note}): `{picked_c['selector']}` "
                           f"(keyword match, first visible) — skipping AI call")
                return {
                    "healed_selector": picked_c["selector"],
                    "success": True,
                    "candidates": [{**picked_c, **picked_v, "score": 95}],
                    "healing_event": {
                        "timestamp": datetime.now().isoformat(),
                        "broken_selector": broken_selector,
                        "element_description": element_description,
                        "method": "rule_based",
                        "healed_selector": picked_c["selector"],
                        "success": True,
                        "strategy_match": "same" in strategy_note,
                    },
                }

        # ── Collect "good enough" (1 match AND visible) ──
        good_candidates = [
            (c, v) for c, v in zip(candidates, validations)
            if v.get("valid") and v.get("count") == 1 and v.get("is_visible")
        ]
        if good_candidates:
            picked_c, picked_v, strategy_note = self._pick_best_candidate(
                good_candidates, original_strategy, broken_classes, intent_keywords
            )
            logger.info(f"  🟡 Rule-based candidate ({strategy_note}) "
                       f"`{picked_c['selector']}` (1 match, visible=True)")
            return {
                "healed_selector": picked_c["selector"],
                "success": True,
                "candidates": [{**picked_c, **picked_v, "score": 85}],
                "healing_event": {
                    "timestamp": datetime.now().isoformat(),
                    "broken_selector": broken_selector,
                    "element_description": element_description,
                    "method": "rule_based",
                    "healed_selector": picked_c["selector"],
                    "success": True,
                    "strategy_match": "same" in strategy_note,
                },
            }

        # Rule-based candidates weren't good enough — need AI
        logger.info(f"  🔄 Rule-based candidates insufficient, falling back to AI...")
        return None

    def _pick_best_candidate(self, scored_candidates, original_strategy,
                              broken_classes, intent_keywords=None):
        """Pick the best candidate from a list of (candidate, validation) tuples.

        Ranking (most preferred first):
        1. Same strategy + similar class name (if original was class-based)
        2. Same strategy + text matches intent keyword from broken class name
        3. Same strategy (class → class, role → role, etc.)
        4. Best-matching keyword relevance (any strategy)
        5. Strategy rank fallback
        """
        # Tier 1: same strategy AND similar class name
        if broken_classes and original_strategy == 'class':
            for c, v in scored_candidates:
                cand_strategy = self._detect_selector_strategy(c["selector"])
                if cand_strategy == 'class':
                    sim = self._class_similarity(broken_classes[0], c["selector"])
                    if sim > 0.3:
                        return c, v, "same-strategy+class-similar"

        # Tier 1.5: same strategy AND text matches intent keyword from broken class
        # e.g. broken class "modal-footer-cancel-old" → intent keyword "cancel"
        # This prevents picking an "Add" button candidate for a "Cancel" button.
        if intent_keywords:
            for c, v in scored_candidates:
                if self._detect_selector_strategy(c["selector"]) == original_strategy:
                    rel = self._text_relevance(intent_keywords, c["selector"])
                    if rel > 0:
                        return c, v, "same-strategy+keyword-match"

        # Tier 2: same strategy (class → class, role → role, etc.)
        for c, v in scored_candidates:
            if self._detect_selector_strategy(c["selector"]) == original_strategy:
                return c, v, "same-strategy"

        # Tier 2.5: any strategy + keyword match (prevents irrelevant fallback)
        if intent_keywords:
            for c, v in scored_candidates:
                rel = self._text_relevance(intent_keywords, c["selector"])
                if rel > 0:
                    return c, v, "keyword-match"

        # Tier 3: fallback — prefer class > role > css > pseudo > text
        strategy_rank = {'class': 0, 'role': 1, 'css': 2, 'pseudo': 3, 'text': 4}
        best = min(scored_candidates,
                   key=lambda cv: strategy_rank.get(
                       self._detect_selector_strategy(cv[0]["selector"]), 99))
        return best[0], best[1], "fallback-strategy"

    @classmethod
    def clear_cache(cls):
        """Clear the healing cache (e.g., after a UI framework upgrade)."""
        count = len(cls._heal_cache)
        cls._heal_cache.clear()
        logger.info(f"  🧹 Healing cache cleared ({count} entries)")

    # ── AI prompt builder ──

    def build_healing_prompt(self, broken_selector: str, element_description: str,
                              page_elements: dict) -> str:
        """Build the AI prompt for locator healing."""
        elements_summary = {
            "url": page_elements.get("url", ""),
            "inputs": page_elements["inputs"][:25],
            "buttons": page_elements["buttons"][:25],
            "tabs": page_elements["tabs"][:15],
            "tables": page_elements["tables"][:5],
            "selects": page_elements["selects"][:8],
            "toggles": page_elements["toggles"][:15],
            "headings": page_elements["headings"][:8],
            "links": page_elements["links"][:5],
        }

        return f"""You are a Playwright locator healing expert for SonicWall SonicOS 7.

## Broken Selector
`{broken_selector}`

## Target Element
{element_description}

## Live Page Structure
```json
{json.dumps(elements_summary, indent=2, ensure_ascii=False)}
```

## Task
Suggest 3 alternative Playwright selectors for the broken locator.
Priority: unique CSS class > id > name > `:has-text()` > `text=` > `getByRole`.

Return ONLY valid JSON:
```json
{{"candidates": [{{"selector": "...", "strategy": "css", "confidence": "high", "reasoning": "..."}}]}}
```"""

    # ── Candidate validation ──

    def validate_candidate(self, selector: str) -> dict:
        """Test a candidate selector against the live page."""
        try:
            locator = self.page.locator(selector)
            count = locator.count()
            is_visible = False
            if count > 0:
                try:
                    is_visible = locator.first.is_visible()
                except Exception:
                    pass
            return {
                "selector": selector, "count": count,
                "is_visible": is_visible,
                "valid": count > 0,
                "ideal": count == 1 and is_visible,
            }
        except Exception as e:
            return {
                "selector": selector, "count": 0,
                "is_visible": False, "valid": False, "ideal": False,
                "error": str(e)[:100],
            }

    def score_candidates(self, candidates: list, validations: list) -> list:
        """Score and rank locator candidates."""
        scored = []
        for c, v in zip(candidates, validations):
            score = 0
            if not v["valid"]:
                score = -1
            elif v["ideal"]:
                score = 100
            elif v["count"] == 1:
                score = 70
            elif v["count"] > 1:
                score = max(0, 40 - v["count"] * 5)

            conf = c.get("confidence", "low")
            score += {"high": 10, "medium": 5, "low": 0}.get(conf, 0)

            scored.append({**c, **v, "score": score})

        return sorted(scored, key=lambda x: x["score"], reverse=True)

    # ── Main healing pipeline ──

    def heal(self, broken_selector: str, element_description: str,
             page_url: str = "") -> dict:
        """Run the complete self-healing pipeline.

        Order: cache -> rule-based -> AI (with caching at each level).

        Returns:
            dict with keys: healed_selector, success, candidates, healing_event
        """
        # Resolve backend name for display
        backend_name = type(self.ai_backend).__name__.replace("Backend", "").lower()

        logger.info(f"🩺 Self-healing: `{broken_selector}` — {element_description}")

        # Step 0: Check cache
        cache_key = ""
        if self.enable_cache:
            cache_key = f"{broken_selector}|{page_url or self.page.url}"
            if cache_key in self._heal_cache:
                cached = self._heal_cache[cache_key]
                logger.info(
                    f"  📋 HEALED via cache -> `{cached['healed_selector']}` "
                    f"(original method: {cached.get('healing_event', {}).get('method', 'cached')})"
                )
                cached_event = dict(cached.get("healing_event", {}))
                cached_event["timestamp"] = datetime.now().isoformat()
                cached_event["from_cache"] = True
                self.healing_log.append(cached_event)
                return dict(cached)

        # Step 1: Extract page structure
        page_elements = self.extract_page_elements()
        total_el = sum(len(v) for v in page_elements.values() if isinstance(v, list))
        logger.info(f"  Extracted {total_el} elements from page")

        # Step 2: Try rule-based healing first (no API call, covers ~60-70%)
        result = None
        if self.enable_rules:
            result = self._try_rule_based_heal(
                broken_selector, element_description, page_elements
            )
            if result is not None:
                logger.info(
                    f"  📋 HEALED via rule-based -> `{result['healed_selector']}`"
                )
        else:
            logger.info(f"  ⏭️  Rules disabled, going straight to AI ({backend_name})")

        # Step 3: Fall back to AI if rules couldn't heal
        if result is None:
            if self.enable_rules:
                logger.info(
                    f"  🔄 Rule-based insufficient — falling back to AI ({backend_name})"
                )
            prompt = self.build_healing_prompt(
                broken_selector, element_description, page_elements
            )
            try:
                ai_response = self.ai_callable(prompt)
                logger.info(f"  🤖 AI ({backend_name}) response received ({len(ai_response)} chars)")
            except Exception as e:
                logger.error(f"  ❌ AI call failed ({backend_name}): {e}")
                result = {
                    "healed_selector": None, "success": False,
                    "error": str(e), "healing_event": {},
                    "candidates": [], "method": f"ai_{backend_name}_failed",
                }
                if self.enable_cache:
                    self._heal_cache[cache_key] = result
                self.healing_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "broken_selector": broken_selector,
                    "element_description": element_description,
                    "method": f"ai_{backend_name}_failed", "error": str(e), "success": False,
                })
                return result

            # Parse AI candidates
            try:
                json_match = re.search(r'\{[\s\S]*\}', ai_response)
                parsed = json.loads(json_match.group() if json_match else ai_response)
                candidates = parsed.get("candidates", [])
            except json.JSONDecodeError:
                logger.error(f"  ❌ Could not parse AI response ({backend_name})")
                result = {
                    "healed_selector": None, "success": False,
                    "error": "AI response parse error", "healing_event": {},
                }
                self.healing_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "broken_selector": broken_selector,
                    "element_description": element_description,
                    "method": f"ai_{backend_name}_parse_error", "success": False,
                })
                return result

            if not candidates:
                result = {
                    "healed_selector": None, "success": False,
                    "error": "No candidates from AI", "healing_event": {},
                }
                self.healing_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "broken_selector": broken_selector,
                    "element_description": element_description,
                    "method": f"ai_{backend_name}_no_candidates", "success": False,
                })
                return result

            # Validate AI candidates
            validations = [self.validate_candidate(c["selector"]) for c in candidates]
            scored = self.score_candidates(candidates, validations)
            best = scored[0]
            success = best["score"] > 0

            event = {
                "timestamp": datetime.now().isoformat(),
                "broken_selector": broken_selector,
                "element_description": element_description,
                "page_url": page_url or page_elements.get("url", ""),
                "candidates_evaluated": scored[:5],
                "healed_selector": best["selector"] if success else None,
                "success": success,
                "method": f"ai_{backend_name}",
            }
            self.healing_log.append(event)

            if success:
                logger.info(
                    f"  📋 HEALED via AI ({backend_name}) -> "
                    f"`{best['selector']}` (score: {best['score']})"
                )
            else:
                logger.warning(
                    f"  ❌ AI ({backend_name}) healing failed — "
                    f"best score: {best['score']}"
                )

            result = {
                "healed_selector": event["healed_selector"],
                "success": success,
                "candidates": scored,
                "healing_event": event,
            }
        else:
            # Rule-based result — log it
            self.healing_log.append(result["healing_event"])

        # Step 4: Cache the result
        if self.enable_cache and result.get("success"):
            self._heal_cache[cache_key] = result

        return result

    def save_report(self, report_dir: str = None) -> Path:
        """Save the healing log as a JSON report."""
        if not report_dir:
            report_dir = _project_root / "test_data" / "healing_reports"
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"healing_report_{timestamp}.json"
        report_path.write_text(json.dumps({
            "healing_events": self.healing_log,
            "summary": {
                "total": len(self.healing_log),
                "successful": sum(1 for e in self.healing_log if e["success"]),
                "failed": sum(1 for e in self.healing_log if not e["success"]),
                "rule_based": sum(1 for e in self.healing_log
                                 if e.get("method") == "rule_based"),
                "ai": sum(1 for e in self.healing_log if e.get("method") == "ai"),
                "from_cache": sum(1 for e in self.healing_log if e.get("from_cache")),
            }
        }, indent=2, ensure_ascii=False))
        logger.info(f"Healing report saved: {report_path}")
        return report_path

# ═══════════════════════════════════════════════════════════════════════════
#  Decorator: @self_heal — wraps Page Object methods with auto-healing
# ═══════════════════════════════════════════════════════════════════════════


def _try_update_rules(broken_selector: str, healed_selector: str) -> bool:
    """Analyze why rules failed and update _CLASS_SUBSTITUTIONS if possible.

    When the AI successfully heals a selector that rules missed, this function
    extracts the class-name difference and adds a new substitution rule so that
    future identical failures are caught by the rule engine without an API call.

    Returns True if rules were updated, False otherwise.
    """
    try:
        # Extract class names from both selectors
        broken_classes = set(re.findall(r'\.([a-zA-Z_-][\w-]+)', broken_selector))
        healed_classes = set(re.findall(r'\.([a-zA-Z_-][\w-]+)', healed_selector))

        # Find classes that differ: old → new
        only_broken = broken_classes - healed_classes
        only_healed = healed_classes - broken_classes

        if not only_broken or not only_healed:
            # Not a simple class rename — can't derive a clean substitution
            return False

        # Build candidate pairs (old_class, new_class)
        new_pairs = []
        for old_cls in sorted(only_broken, key=len, reverse=True):
            # Try to find the corresponding new class:
            # e.g. 'static-entry-modal__modal-footer-cancel-old' →
            #      'static-entry-modal__modal-footer-cancel'
            for new_cls in sorted(only_healed, key=len, reverse=True):
                # Check if old_cls is a suffix/prefix variant of new_cls
                if new_cls in old_cls or old_cls in new_cls:
                    new_pairs.append((old_cls, new_cls))
                    only_broken.discard(old_cls)
                    only_healed.discard(new_cls)
                    break

        if not new_pairs:
            return False

        # Read the current _CLASS_SUBSTITUTIONS from source
        source_file = Path(__file__).resolve()
        content = source_file.read_text(encoding='utf-8')

        # Check if any pair already exists
        existing_pairs = set()
        for old_c, new_c in re.findall(
            r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', content
        ):
            existing_pairs.add((old_c, new_c))

        really_new = [(o, n) for o, n in new_pairs if (o, n) not in existing_pairs]
        if not really_new:
            return False

        # Find the _CLASS_SUBSTITUTIONS list and append new pairs
        marker = '_CLASS_SUBSTITUTIONS = ['
        marker_pos = content.find(marker)
        if marker_pos < 0:
            return False

        # Find the closing bracket of the list
        list_start = content.index('[', marker_pos)
        depth = 1
        i = list_start + 1
        while i < len(content) and depth > 0:
            if content[i] == '[':
                depth += 1
            elif content[i] == ']':
                depth -= 1
            i += 1
        if depth != 0:
            return False
        insert_pos = i - 1  # position of ']'

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        indent = ' ' * 8  # match existing indentation

        # Build new entries with comment
        new_entries = []
        for old_c, new_c in really_new:
            new_entries.append(
                f'{indent}# [rule-update {timestamp}] AI healed `{old_c}` → `{new_c}`\n'
                f'{indent}("{old_c}", "{new_c}"),'
            )
        new_lines = '\n' + '\n'.join(new_entries)

        updated = content[:insert_pos] + new_lines + '\n' + content[insert_pos:]
        source_file.write_text(updated, encoding='utf-8')

        logger.info(
            f"  📐 Rules updated: added {len(really_new)} class substitution(s) "
            f"to _CLASS_SUBSTITUTIONS"
        )
        # Clear the class-level cache so the new rule takes effect immediately
        SelfHealingLocator._heal_cache.clear()
        return True

    except Exception as e:
        logger.debug(f"  [rule-update] Failed to update rules: {e}")
        return False


def _auto_fix_source(broken_selector: str, healed_selector: str, func) -> bool:
    """Replace the broken selector with the healed one in the source file.

    Only counts occurrences in CODE lines (not pure-comment lines). This way
    a stale [self-healed] comment won't block the fix.

    Adds a # [self-healed] comment on the line above the fix.
    If there's already a [self-healed] comment for this selector, it's removed
    to keep the file clean.
    """
    try:
        # Unwrap decorated functions to get the ORIGINAL source file
        # (inspect.getfile on the wrapper returns self_healing_locator.py!)
        original_func = func
        while hasattr(original_func, '__wrapped__'):
            original_func = original_func.__wrapped__
        source_file = inspect.getfile(original_func)
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Strip surrounding quotes for searching
        search = broken_selector.strip("'\"")

        # Find ALL lines containing the selector, split into code vs comment
        code_lines = []      # (line_index, line_text) — actual locator calls
        comment_lines = []   # (line_index, line_text) — #[self-healed] comments
        for i, line in enumerate(lines):
            if search not in line:
                continue
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                comment_lines.append((i, line))
            else:
                code_lines.append((i, line))

        # No code lines found — can't fix
        if not code_lines:
            logger.warning(
                f"  auto_fix: selector `{search}` only found in comment lines "
                f"({len(comment_lines)}), nothing to fix"
            )
            return False

        # Multiple code lines — too risky
        if len(code_lines) > 1:
            logger.warning(
                f"  auto_fix: selector appears in {len(code_lines)} code lines, "
                f"too ambiguous to auto-fix"
            )
            return False

        # Exactly one code line — safe to fix
        target_line, old_line = code_lines[0]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Replace the selector on the target line
        indent = len(old_line) - len(old_line.lstrip())
        new_line = old_line.replace(search, healed_selector)
        lines[target_line] = new_line

        # Remove any existing [self-healed] comments that mention this selector
        # (to avoid stale comments piling up)
        lines_to_delete = set()
        for i, line in comment_lines:
            if '# [self-healed' in line and search in line:
                lines_to_delete.add(i)
                # Also remove the blank line right after if exists
                if i + 1 < len(lines) and lines[i + 1].strip() == '':
                    lines_to_delete.add(i + 1)

        # Insert the new comment above the fix
        heal_comment = (f"{' ' * indent}# [self-healed {timestamp}] "
                        f"`{search}` -> `{healed_selector}`")
        lines.insert(target_line, heal_comment)
        # Shift all later indices up by 1 since we inserted a line

        # Write back, skipping deleted lines
        output_lines = [l for i, l in enumerate(lines) if i not in lines_to_delete]
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))

        logger.info(f"  ✅ auto_fix: `{search}` -> `{healed_selector}` in "
                    f"{Path(source_file).name}:{target_line + 1}")
        return True
    except Exception as e:
        logger.warning(f"  auto_fix failed: {e}")
        return False


def self_heal(description: str, max_retries: int = 1,
              auto_retry: bool = False, auto_fix: bool = False,
              ai_backend: str = "glm",
              enable_cache: bool = True, enable_rules: bool = True):
    """Decorator that auto-heals broken locators in Page Object methods.

    Args:
        description: Human description of what the wrapped method does
        max_retries: Max healing attempts (default 1)
        auto_retry: If True, automatically re-execute the method with the healed
                    locator (monkey-patches page.locator). If False (default),
                    logs the healed selector but re-raises the original error.
        auto_fix: If True AND auto_retry succeeds, permanently update the source
                  file to replace the broken selector with the healed one.
                  (default False, CI-safe)
        ai_backend: AI backend for locator healing — "glm" (default), "claude", or "mcp"
        enable_cache: Use in-memory cache for heal results (default True)
        enable_rules: Try rule-based candidates before calling AI (default True)

    Usage:
        class ARPPage(BasePage):
            # Diagnose only (CI safe) — current behavior
            @self_heal("Click the Add button to open Add dialog")
            def click_add_button(self):
                self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

            # Auto-retry + auto-fix (dev mode) — recover AND update source
            @self_heal("Click the Add button", auto_retry=True, auto_fix=True)
            def click_add_button_v2(self):
                self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

            # Use Claude via Anthropic API instead of GLM
            @self_heal("Click the Cancel button", auto_retry=True, ai_backend="claude")
            def close_dialog(self):
                self.page.locator('.old-cancel-class').click()

            # DEMO: use Claude Code MCP (file-based, no API key needed)
            @self_heal("Click the Cancel button", auto_retry=True, ai_backend="mcp")
            def close_dialog_v2(self):
                self.page.locator('.old-cancel-class').click()

    When the locator fails, the decorator:
    1. Catches the Playwright error
    2. Extracts current page structure
    3. Tries rule-based healing (no API call, covers ~60-70%)
    4. Falls back to AI for complex cases
    5. Retries with the healed locator (if auto_retry=True)
    6. Logs the healing event
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt >= max_retries:
                        raise

                    # Only heal on locator-related errors
                    error_msg = str(e).lower()
                    matched_keywords = [kw for kw in
                               ["locator", "selector", "timeout", "not found",
                                "waiting", "visible", "resolved", "strict mode",
                                "click", "fill", "type"]
                               if kw in error_msg]
                    if not matched_keywords:
                        logger.debug(
                            f"  ⏭️  Skipping self-heal: error not locator-related "
                            f"({type(e).__name__}: {str(e)[:120]})"
                        )
                        raise

                    logger.warning(
                        f"🔧 Self-healing attempt {attempt+1}/{max_retries}: "
                        f"{func.__qualname__} — {description}"
                    )
                    logger.info(
                        f"  ⚡ Triggered by {type(e).__name__} "
                        f"(matched keywords: {matched_keywords}): {str(e)[:150]}"
                    )

                    page = getattr(self, 'page', None)
                    if not page:
                        logger.error("  No 'page' attribute found on self, cannot heal")
                        raise

                    healer = SelfHealingLocator(
                        page,
                        ai_backend=ai_backend,
                        enable_cache=enable_cache,
                        enable_rules=enable_rules,
                    )
                    logger.info(
                        f"  ⚙️  Healing config: rules={'ON' if enable_rules else 'OFF'}, "
                        f"AI={ai_backend}, cache={'ON' if enable_cache else 'OFF'}"
                    )
                    # Try e.message first: Playwright puts the full call log
                    # (e.g. 'waiting for locator(".foo")') in .message, while
                    # str(e) may only be 'Timeout 30000ms exceeded.'
                    error_sources = []
                    msg = getattr(e, 'message', '')
                    if msg:
                        error_sources.append(("e.message", str(msg)))
                    error_sources.append(("repr(e)", repr(e)))
                    error_sources.append(("str(e)", str(e)))
                    broken_selector = None
                    source_used = None
                    for src_name, src_text in error_sources:
                        broken_selector = _extract_selector_from_error(src_text)
                        if broken_selector:
                            source_used = src_name
                            break
                    if not broken_selector:
                        logger.warning(
                            f"  ❌ Could not extract selector from error — "
                            f"tried {[s[0] for s in error_sources]}"
                        )
                        for src_name, src_text in error_sources:
                            logger.debug(f"  [extract] {src_name}: {repr(src_text[:200])}")
                        raise
                    logger.info(f"  🎯 Extracted broken selector `{broken_selector}` (from {source_used})")

                    result = healer.heal(broken_selector, description)

                    if not result["success"]:
                        healer.save_report()
                        logger.warning(
                            f"  ❌ Healing FAILED — "
                            f"`{broken_selector}` could not be healed"
                        )
                        raise

                    # ── Auto-retry: monkey-patch page.locator and re-execute ──
                    if auto_retry and result["success"]:
                        healed_selector = result["healed_selector"]
                        logger.info(
                            f"  🔄 AUTO-RETRY: redirecting "
                            f"`{broken_selector}` -> `{healed_selector}`"
                        )

                        original_locator = page.locator

                        def patched_locator(selector, **locator_kwargs):
                            if selector.strip() == broken_selector.strip():
                                logger.debug(
                                    f"  🔄 [patched] locator redirected: "
                                    f"`{selector}` -> `{healed_selector}`"
                                )
                                return original_locator(healed_selector, **locator_kwargs)
                            return original_locator(selector, **locator_kwargs)

                        # Monkey-patch the locator method
                        page.locator = patched_locator
                        try:
                            result_val = func(self, *args, **kwargs)
                            healer.save_report()
                            logger.info(
                                f"  ✅ Auto-retry SUCCESS — method completed "
                                f"with healed locator"
                            )
                            # ── Auto-fix: permanently update source file ──
                            if auto_fix:
                                _auto_fix_source(
                                    broken_selector, healed_selector, func
                                )
                            return result_val
                        except Exception as retry_err:
                            healer.save_report()
                            logger.warning(
                                f"  ⚠️ Auto-retry failed: {type(retry_err).__name__}: {retry_err}"
                            )
                            # ── AI fallback: if rules gave a wrong selector, force AI ──
                            heal_method = result.get("healing_event", {}).get("method", "")
                            if heal_method == "rule_based":
                                logger.info(
                                    f"  🔄 Rule-based selector failed at runtime, "
                                    f"forcing AI fallback ({ai_backend})..."
                                )
                                ai_healer = SelfHealingLocator(
                                    page,
                                    ai_backend=ai_backend,
                                    enable_cache=False,  # Skip cache: previous cache may contain wrong rule-based result
                                    enable_rules=False,  # Force AI, skip rules
                                )
                                ai_result = ai_healer.heal(broken_selector, description)
                                if ai_result["success"]:
                                    ai_healed = ai_result["healed_selector"]
                                    logger.info(
                                        f"  🔄 AI fallback AUTO-RETRY: "
                                        f"`{broken_selector}` -> `{ai_healed}`"
                                    )
                                    page.locator = original_locator
                                    try:
                                        page.locator = lambda sel, **kw: (
                                            original_locator(ai_healed, **kw)
                                            if sel.strip() == broken_selector.strip()
                                            else original_locator(sel, **kw)
                                        )
                                        result_val = func(self, *args, **kwargs)
                                        ai_healer.save_report()
                                        logger.info(
                                            f"  ✅ AI fallback auto-retry SUCCESS"
                                        )
                                        if auto_fix:
                                            _auto_fix_source(
                                                broken_selector, ai_healed, func
                                            )
                                        # ── Learn from AI: update rules so next time rules alone suffice ──
                                        _try_update_rules(broken_selector, ai_healed)
                                        return result_val
                                    except Exception as ai_retry_err:
                                        ai_healer.save_report()
                                        logger.warning(
                                            f"  ⚠️ AI fallback auto-retry also failed: "
                                            f"{type(ai_retry_err).__name__}: {ai_retry_err}"
                                        )
                                        last_error = ai_retry_err
                                    finally:
                                        page.locator = original_locator
                                else:
                                    logger.warning(
                                        f"  ❌ AI fallback also failed to heal"
                                    )
                            last_error = retry_err
                        finally:
                            page.locator = original_locator
                    else:
                        # Non-auto-retry: log and save report, then re-raise
                        healer.save_report()
                        logger.warning(
                            f"  📝 Healed selector `{result['healed_selector']}` "
                            f"available in report (auto_retry=OFF, update source manually)"
                        )
                        raise

            raise last_error

        return wrapper
    return decorator


def _extract_selector_from_error(error_msg: str) -> Optional[str]:
    """Try to extract the failing selector from a Playwright error message.

    Playwright errors contain the locator string like:
        locator('.sw-tab:has-text("Add")')
        locator(".sw-icon-button__label-cont")

    Uses paren-counting to handle nested quotes and parens correctly.
    """
    # Find "locator(" and extract the argument using paren counting
    for marker in ("locator(", "Locator."):
        start = error_msg.find(marker)
        if start < 0:
            continue
        # Find the opening paren
        paren_start = error_msg.find("(", start)
        if paren_start < 0:
            continue
        # Count parens to find matching closing paren
        # (handles nested parens like :has-text("foo"))
        depth = 1
        i = paren_start + 1
        while i < len(error_msg) and depth > 0:
            if error_msg[i] == "(":
                depth += 1
            elif error_msg[i] == ")":
                depth -= 1
            i += 1
        if depth == 0:
            selector = error_msg[paren_start + 1:i - 1].strip()
            # Strip surrounding quotes (can be single or double)
            if (selector.startswith('"') and selector.endswith('"')) or \
               (selector.startswith("'") and selector.endswith("'")):
                selector = selector[1:-1]
            # Unescape Playwright's error-message escaping: \" -> " , \' -> '
            selector = selector.replace('\\"', '"').replace("\\'", "'")
            if selector and len(selector) > 2:
                return selector

    # Pattern: waiting for selector "..."
    match = re.search(r"selector\s+[\"']([^\"']+)[\"']", error_msg)
    if match:
        return match.group(1)

    # Pattern: strict mode violation — mentions the selector in backticks
    match = re.search(r"strict mode.*?`([^`]+)`", error_msg, re.DOTALL)
    if match:
        return match.group(1)

    return None
