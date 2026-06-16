#!/usr/bin/env python3
"""
Generate test cases by calling the Zhipu (智谱) GLM API.

Usage:
    # Step 1: Extract page structure
    python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp

    # Step 2: Generate test files
    python3 bin/tools/generate_tests.py --feature arp --api-key YOUR_KEY

    # Or provide key via environment variable
    export ZHIPU_API_KEY=your_key_here
    python3 bin/tools/generate_tests.py --feature arp

    # Dry run (print response without writing files)
    python3 bin/tools/generate_tests.py --feature arp --dry-run

Output files:
    - bin/test_data/manual_testcases/SonicWall_{FEATURE}_Test_Cases.csv
    - bin/pages/{subdir}/{feature}.py
    - bin/tests/test_{number}_{feature}.py
    - bin/pages/fw_pages.py  (updated with new page object registration)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Make bin/ and bin/tools/ importable (must precede local imports)
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from zhipuai import ZhipuAI as ZhipuAiClient
from config.logger import get_logger

logger = get_logger("generate_tests")

DEFAULT_MODEL = "glm-5.1"
def _load_api_key(name: str) -> str:
    env_val = os.environ.get(name, "")
    if env_val:
        return env_val
    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get(name.lower(), "") or ""
        except (json.JSONDecodeError, OSError):
            pass
    return ""

ZHIPU_API_KEY = _load_api_key("ZHIPU_API_KEY")

SYSTEM_PROMPT = """你是一个代码生成器，只输出文件，不输出任何解释、分析或问候语。

根据用户提供的 SonicOS 7 防火墙页面骨架 JSON，生成完整测试套件。**必须覆盖所有匹配的 pattern，不少于 20 个测试用例。**

## 严格输出格式

每个文件必须用 `===FILE:` 开头和 `===END===` 结尾，代码块用正确的语言标记。不要输出其他任何内容。

===FILE: bin/test_data/manual_testcases/SonicWall_{FEATURE}_Test_Cases.csv===
```csv
...CSV内容...
```
===END===

===FILE: bin/pages/{subdir}/{feature}.py===
```python
...Python内容...
```
===END===

===FILE: bin/tests/test_{number}_{feature}.py===
```python
...Python内容...
```
===END===

===FILE: bin/pages/fw_pages.py UPDATE===
```python
...import和property代码...
```
===END===

## 测试用例生成 — 完整 Pattern 清单

CSV 列: Test ID,Title,Category,Steps,Expected Result,Priority

**Category 分类:**
- 只有 Negative 用例填 `Negative`，其余用例的 Category 列留空（不要填任何值）
- `Negative` — 非法输入校验、空白校验、重复拒绝、脚本注入等

**Title 命名规范（严格遵守）:**
- 所有 Title 必须以 `Verify` 或 `Validate` 动词开头
- `Verify` — 被动观察，确认状态/行为符合预期。用于：页面加载、面包屑、Tab切换、表头、按钮状态、弹窗布局、全选、排序、分页、刷新、导出等
- `Validate` — 主动输入数据，确认约束生效。**用于所有 Negative 用例**：非法IP、非法MAC、必填空白、重复拒绝、脚本注入等
- Title 格式：`Verify/Validate + 一句话描述 (英文)`
- **不要使用 [Prefix] 标签**，动词本身已经表达类型

**Steps 编写规则（极其重要，逐条遵守）:**

每条 Steps 必须从 JSON 信息推导，用 `<br>` 分隔的编号列表。以下是从 JSON 到 Steps 的映射规则：

1. **每个操作必须自包含上下文** — 利用 JSON 中的 `button.tab`、`dialog.tab` 字段：
   - button: {"text": "Add", "tab": "Static ARP Entries"} → Step 必须写 "1. Navigate to the 'Static ARP Entries' tab.<br>2. Click the 'Add' button."
   - 绝不能写 "1. Click the 'Add' button." 因为没说明在哪个 tab

2. **弹窗操作要详细** — 利用 `dialog.title`、`dialog.fields`、`dialog.html`：
   - dialog.title → "The '{title}' dialog opens."
   - dialog.fields 每个字段一个 step，引用 label 和 input_name（从 html 提取）：
     - "Input '192.168.1.100' in the IP Address field."
     - "Select 'X0' from the Interface dropdown."
     - "Toggle 'Publish Entry' to ON."
   - dialog.buttons → "Click 'OK'." 或 "Click 'Cancel'."

3. **Expected Result 与 Steps 一一对应** — 每个 Step 编号对应一个 Expected Result 编号

4. **Negative 测试要列出具体的非法值** — 不要写 "Input invalid IP"，要写 "Input '999.999.999.999' in the IP Address field.<br>5. Click 'OK'.<br>6. Observe the field highlights in red with error 'Invalid IP Address'."

**具体示例（从 JSON 到 CSV 的完整映射）:**

```json
// JSON:
{"buttons": [{"text": "Add", "tab": "Static ARP Entries", "safe_to_click": true}],
 "dialogs": [{"trigger": "Add", "tab": "Static ARP Entries", "title": "Add Static Entry",
   "fields": [{"label": "IP Address", "type": "text", "input_name": "IPAddress"},
              {"label": "MAC Address", "type": "text", "input_name": "macAddress"},
              {"label": "Interface", "type": "dropdown", "input_name": "interface"}]}]}
```

生成的 CSV (Title 示例):
```
Verify ARP page loads with all key zones visible
Verify breadcrumb displays correct path
Verify tab switching between ARP Cache and Static ARP Entries
Verify Add Static Entry dialog contains all expected fields
Validate invalid IP address is rejected with error message
Validate duplicate entry is blocked with error message
```

生成的 CSV Steps (弹窗布局):
```
"1. Navigate to Network > System > ARP.<br>2. Switch to the 'Static ARP Entries' tab.<br>3. Click the 'Add' button in the toolbar.<br>4. Observe the 'Add Static Entry' dialog opens.<br>5. Observe the dialog contains fields: IP Address (text input), MAC Address (text input), Interface (dropdown).<br>6. Observe the dialog has OK and Cancel buttons."
```

生成的 Negative CSV Steps (IP/MAC 校验, Category=Negative):
```
"1. Navigate to Network > System > ARP.<br>2. Switch to the 'Static ARP Entries' tab.<br>3. Click the 'Add' button.<br>4. Input '999.999.999.999' in the IP Address field.<br>5. Input '00:11:22:33:44:55' in the MAC Address field.<br>6. Click 'OK'.<br>7. Observe the IP Address field highlights in red.<br>8. Observe error message 'Invalid IP Address' appears.<br>9. Observe the dialog remains open.<br>10. Repeat steps 4-9 with: 'abc.def.1.1', '224.0.0.1' (multicast), '127.0.0.1' (loopback), '255.255.255.255' (broadcast)."
```

Test ID: SOSAIOT-TC-{FEATURE_UPPER}-{序号04d}（4位数字）
Title: "Verify/Validate {英文描述}" — 严格遵守上面的 Title 命名规范

必须按以下规则逐一匹配，**每条匹配的规则生成至少一个测试用例**:

### 一、页面与导航 (Page & Navigation) — Priority: High/Medium

1. **页面加载** — Title: "Verify {Page} page loads with all key zones visible"。任何页面都必须有。Steps: "1. Log in to the firewall dashboard.<br>2. Navigate to {导航路径}.<br>3. Observe the page loads with no UI errors.<br>4. Observe key zones (Tabs, Table, Operation Bar) are visible."
2. **面包屑** — Title: "Verify breadcrumb displays correct navigation path"。breadcrumb 非空时生成。验证面包屑路径匹配预期。
3. **Tab 切换** — Title: "Verify tab switching between X and Y"。tabs 非空时生成。Steps 中每个 tab 单独一个步骤, 格式: "1. Click on the 'XXX' tab.<br>2. Observe the 'XXX' tab becomes active (orange underline).<br>3. Click on the 'YYY' tab.<br>4. Observe the 'YYY' tab becomes active.<br>..."。如果有 L2 tab 也要覆盖。

### 二、表格 (Table) — Priority: High/Medium

4. **表头** — Title: "Verify {tab} table headers match expected columns"。tables 中每个 table 都生成一个。
5. **空状态** — Title: "Verify 'No Data' message is displayed when table is empty"。如果 table.row_count == 0 时生成。
6. **行数统计** — Title: "Verify footer row count matches actual table rows"。table.has_footer_counter == true 时生成。
7. **全选 Checkbox** — Title: "Verify master checkbox selects and deselects all rows"。表格有 checkbox 列时生成。
8. **排序** — Title: "Verify column sorting toggles between ascending and descending"。表格有可排序列时生成。

### 三、按钮与控件 (Buttons & Controls) — Priority: High/Medium/Low

9. **Add 按钮** — Title: "Verify Add button opens {Dialog} dialog"。buttons 中有 Add 类按钮时生成。验证按钮可点击，弹窗标题正确，字段/下拉/按钮齐全。
10. **Delete 按钮状态** — Title: "Verify Delete button is disabled without row selection"。buttons 中有 Delete 时生成。未选中行时灰色(disabled)，选中行后激活。
11. **Delete 确认流程** — Title: "Verify delete confirmation flow removes entry from table"。选中行→点 Delete→确认弹窗→确认删除→行消失、总数减1。
12. **Refresh 按钮** — Title: "Verify Refresh button triggers data reload"。buttons 中有 Refresh 时生成。
13. **Export 按钮** — Title: "Verify Export button triggers download mechanism"。buttons 中有 Export 时生成。
14. **Statistics 按钮** — Title: "Verify Statistics button opens statistics panel"。buttons 中有 Statistics 时生成。
15. **Limit 分页下拉** — Title: "Verify pagination limit dropdown changes visible row count"。buttons 中有 Limit 类按钮时生成。
16. **Settings/Update 流程** — Title: "Verify Settings update flow with dirty-check on Update button"。tabs 中有 Settings 类 tab 时生成。打开 Settings tab → Update 初始灰色 → 修改字段后激活 → 点击 Update 执行更新。
17. **Search/Filter 搜索框** — Title: "Verify search filter filters table rows by keyword"。骨架中有搜索框时生成。
18. **Flush/Clear 类按钮** — Title: "Verify Flush confirmation dialog without data loss on cancel"。buttons 中有 Flush/Clear 时生成。点击→确认弹窗→点 Cancel→数据不变。

### 四、弹窗表单 (Dialog) — 按弹窗聚合，不拆分

*dialogs 中每个 dialog 合并成 2-4 个 CSV 行:*

19. **弹窗布局** — Title: "Verify {Dialog} dialog contains all expected fields"。一个 case 覆盖: 点击触发按钮 → 验证弹窗标题 → 逐一列出所有字段（label + type）→ 验证按钮（OK/Cancel）。用 `<br>` 将多个检查点串成一个 Steps。

20. **字段校验 (Negative)** — Title: "Validate invalid {field types} are rejected with error in {Dialog}"。Category 填 `Negative`。一个 case 包含所有校验场景:<br>
   "1. Click '+ Add'.<br>2. Leave IP Address blank and click OK → observe 'Field required'.<br>3. Input '999.999.999.999' in IP and click OK → observe 'Invalid IP Address'.<br>4. Input 'abc.def.1.1' in IP and click OK → observe red error.<br>5. Input '00:11:22:GG:HH:II' in MAC and click OK → observe 'Invalid MAC Address'.<br>..."。按 fields 实际情况动态组合, IP/MAC/number 等有专门校验的字段排前面，必填空白排后面。

21. **有效数据创建** — Title: "Verify new {entry} can be created with valid data"。一个 case: 用合法值填写所有字段 → 点 OK → 弹窗关闭 → 新条目出现在表格中。

22. **重复条目拒绝 (Negative)** — Title: "Validate duplicate {entry} is rejected with error message"。Category 填 `Negative`。填入已存在的数据 → 保存 → 后端报 "Entry already exists"。

23. **弹窗遮罩保护** — Title: "Verify dialog stays open when clicking background mask"。dialog type 为 modal 时生成。

24. **行级 Edit 弹窗** — **重要：参数化识别**。当 dialog 标题包含具体实例名（如 "Edit Interface - X0"），LLM 必须识别为参数化模板：
   - 从标题中提取 `title_pattern`: "Edit Interface - {interface_name}"
   - 从 `row_identifiers` 中选取有代表性的行（如第一条和最后一条）
   - Steps 中写明 "1. Hover over the '{X0}' row in the table.<br>2. Click the 'Edit' button.<br>3. Observe the 'Edit Interface - X0' dialog opens..."
   - 同时生成验证不同 interface 的 Steps 变体

### 五、多 Tab 交互 (Cross-Tab) — Priority: Medium

24. **未保存变更警告** — Title: "Verify unsaved changes warning when switching tabs"。tabs >1 且有 Settings 类 tab 时生成。修改 Settings 值→不保存→切换 tab→弹出确认框。

### 六、安全测试 (Security) — Priority: Medium

25. **脚本注入防御** — Title: "Validate XSS injection is sanitized in search box"。Category 填 `Negative`。输入 `<script>alert(1)</script>` → 不执行。

## Page Object 模板

参考 `bin/pages/Network/System/interface.py` 的代码风格。生成的 page object 必须包含：

1. **文件头注释** — `# pages/{subdir}/{feature}.py, Page Methods for {FeatureTitle} Page`
2. **类型提示** — 所有方法参数和返回值必须有类型提示（`: str`, `-> bool`, `-> Optional[Locator]` 等）
3. **try/except 错误处理** — 每个方法用 try/except 包裹，except 中用 `logger.error()` 记录并返回安全默认值
4. **docstring** — 每个方法用三引号字符串简要说明用途
5. **使用 base_page 辅助方法** — 优先用 `self.get_table_row_locator()`、`self.set_toggle_by_locator()` 等封装好的方法

```python
# pages/{subdir}/{feature}.py, Page Methods for {FeatureTitle} Page
from pages.base_page import *

logger = get_logger('{feature_name}')


class {ClassName}(BasePage):
    # Table container CSS class constants — from JSON table.container
    {CONTAINER_1} = '{container_class_1}'
    {CONTAINER_2} = '{container_class_2}'

    def __init__(self, page):
        super().__init__(page)
        self.url = Settings.BASE_URL + '{url}'

    def navigate_to_{feature}(self):
        '''Navigate to {FeatureTitle} page'''
        self.navigate_to_url(self.url)
```

### 根据骨架生成功能方法

**规则：分析骨架中的 table.column_types，为每个 icon_toggle 列生成 enable/disable 方法：**

如果 column_types 中有 `icon_toggle` 类型（如 ARP LOCK、ARP WATCH、ENFORCED 等），为每个 toggle 列生成：
```python
    def get_{feature}_{toggle_name}_status(self, interface_name: str) -> str:
        '''Get {ToggleLabel} status for specified interface. Returns enabled/disabled/unknown.'''
        status = 'unknown'
        try:
            logger.info(f'Getting {toggle_name} status for: {{interface_name}}')
            row = self.get_table_row_locator(self.{CONTAINER_NAME}, interface_name)
            if row.count() == 0:
                logger.error(f'Interface {{interface_name}} not found')
                return status
            # locate the toggle in the row
            toggle = row.locator(".sw-toggle")
            if toggle.count() > 0:
                toggle_class = toggle.first.get_attribute('class') or ''
                status = 'enabled' if 'checked' in toggle_class or 'on' in toggle_class else 'disabled'
            return status
        except Exception as e:
            logger.error(f'Error getting {toggle_name} status for {{interface_name}}: {{e}}')
            return status

    def enable_{feature}_{toggle_name}(self, interface_name: str) -> bool:
        '''Enable {ToggleLabel} for specified interface.'''
        try:
            row = self.get_table_row_locator(self.{CONTAINER_NAME}, interface_name)
            if row.count() == 0:
                logger.error(f'Interface {{interface_name}} not found')
                return False
            return self.set_toggle_by_locator(row, enable=True)
        except Exception as e:
            logger.error(f'Error enabling {toggle_name} for {{interface_name}}: {{e}}')
            return False

    def disable_{feature}_{toggle_name}(self, interface_name: str) -> bool:
        '''Disable {ToggleLabel} for specified interface.'''
        try:
            row = self.get_table_row_locator(self.{CONTAINER_NAME}, interface_name)
            if row.count() == 0:
                logger.error(f'Interface {{interface_name}} not found')
                return False
            return self.set_toggle_by_locator(row, enable=False)
        except Exception as e:
            logger.error(f'Error disabling {toggle_name} for {{interface_name}}: {{e}}')
            return False
```

**规则：如果骨架中有 row_hover_button（如 Edit），生成 hover + click 方法：**
```python
    def hover_{feature}_row(self, interface_name: str, wait_time: int = 300) -> Optional[Locator]:
        '''Hover over a table row and return the row locator.'''
        row = self.get_table_row_locator(self.{CONTAINER_NAME}, interface_name)
        if row.count() == 0:
            logger.error(f'Row not found: {{interface_name}}')
            return None
        row.first.hover()
        self.page.wait_for_timeout(wait_time)
        return row

    def click_row_edit(self, interface_name: str) -> bool:
        '''Click the Edit button on a hovered row to open the edit dialog.'''
        row = self.hover_{feature}_row(interface_name)
        if not row:
            return False
        edit_btn = row.locator('[class*="icon-edit"], [class*="icon-pencil"]')
        if edit_btn.count() == 0:
            logger.error(f'Edit button not found for: {{interface_name}}')
            return False
        edit_btn.first.click()
        self.page.wait_for_timeout(2000)
        return True
```

**规则：如果骨架中有 dialog（modal 类型），生成表单操作方法：**
```python
    def open_add_dialog(self) -> bool:
        '''Open the Add dialog by clicking the Add toolbar button.'''
        try:
            self.click_icon_button('Add')
            self.page.wait_for_timeout(2000)
            return self.verify_text_exists('{dialog_title}', timeout=3000)
        except Exception as e:
            logger.error(f'Error opening Add dialog: {{e}}')
            return False

    def fill_and_submit_form(self, **kwargs) -> bool:
        '''Fill the dialog form with provided values and click OK.'''
        try:
            for label, value in kwargs.items():
                self.fill_input_by_label_name(label, value)
            self.click_button('OK')
            self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f'Error filling form: {{e}}')
            return False
```

## 测试文件规范

```python
import pytest
from config.settings import Settings
from config.logger import get_logger


logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="{feature}", username='admin', password='S0nic@uto')
```

- 每个 class 必须有 uuid 类属性，与 CSV Test ID 一致
- Tab 切换 pattern 用 `test_all()` 合并多个子步骤（check_active_tab + switch_to_*）
- 其他 pattern 用 `test_01_` 前缀方法
- 切换 tab 后加 `fw_page.page.wait_for_timeout(5000)`
- 容器 class 用字符串（如 `fw_page.get_table_header("interface-settings-ipv4")`）或 page object 常量均可
- url 必须在 `__init__` 中求值，禁止类体级别

## 关键规则
- **不要输出任何解释文字，只输出文件**
- **Title 必须以 Verify 或 Validate 动词开头**，Validate 只用于 Negative 用例
- **Category 只有 Negative 用例填 `Negative`**，其余一律留空
- **page object 必须参考 interface.py 的完整风格** — 类型提示、try/except、docstring、base_page 辅助方法
- **为骨架中每个 icon_toggle 列生成 enable/disable/get_status 方法**
- **为骨架中每个 modal dialog 生成 open_add_dialog / fill_and_submit_form 方法**
- **为骨架中的 row_hover_button 生成 hover + click 方法**
- **对话框相关测试必须按弹窗聚合**（每个 dialog 2-4行），禁止每个字段校验拆一个独立 case
- **独立操作用例每个按钮/功能一行即可**（Navigation/Breadcrumb/Refresh/Export/Delete 状态/Delete确认 各一行）
- **15-22 个 CSV 行**是比较合适的范围（页面导航 2-3行 + 表格 3-5行 + 按钮控件 5-7行 + 弹窗聚合 3-5行 + 跨Tab 1-2行）
- subdir 从 url 推导: /m/mgmt/network/arp → Network/System/
"""


def build_user_message(feature: str, structure: dict) -> str:
    """Build the user message containing the page structure JSON."""
    # Strip verbose HTML from the structure to keep token usage reasonable,
    # but preserve a reference to it
    structure_for_prompt = {}
    for k, v in structure.items():
        if k == "dialogs":
            structure_for_prompt[k] = []
            for d in v:
                d_copy = dict(d)
                html = d_copy.pop("html", "")
                d_copy["_html_lines"] = len(html.split("\\n")) if html else 0
                structure_for_prompt[k].append(d_copy)
        else:
            structure_for_prompt[k] = v

    return f"""页面: {feature}
URL: {structure.get('url', '')}
Breadcrumb: {structure.get('breadcrumb', '')}
Tabs: L1={structure.get('tabs', {}).get('l1', [])}, L2={structure.get('tabs', {}).get('l2', [])}
Tables: {len(structure.get('tables', []))} 个
Buttons: {[b['text'] for b in structure.get('buttons', [])]}
Dialogs: {len(structure.get('dialogs', []))} 个

完整的骨架 JSON（含弹窗字段结构）:

```json
{json.dumps(structure_for_prompt, indent=2, ensure_ascii=False)}
```

{dialog_html_section(structure)}

## 任务

1. 分析所有 tabs / tables / buttons / dialogs，参考弹窗 HTML 写精确的 Steps
2. 按 pattern 匹配规则推断测试用例，生成 CSV（含 Category 列）
3. **生成 Page Object** — 参考 interface.py 风格：
   - 为每个 icon_toggle 列生成 enable/disable/get_status 方法
   - 为 modal dialog 生成 open_dialog / fill_and_submit_form 方法
   - 为 row_hover_button 生成 hover_row / click_edit 方法
   - 所有方法带类型提示、try/except、docstring
4. **生成测试文件** — 用 test_all() 合并 Tab 切换，其余用 test_01_ 方法
5. **生成 fw_pages.py UPDATE** — import + @property

注意：
- Steps 必须包含上下文（哪个 tab → 哪个按钮 → 打开什么弹窗）
- feature 名称: {feature}
- 类名使用 CamelCase: {_to_camel_case(feature)}
- test 文件编号从现有的 tests/ 目录推导，如无则用下一个可用数字
- 所有文件放在正确的子目录下（从 url 路径推导，如 /m/mgmt/network/arp → Network/System/）
"""


def dialog_html_section(structure: dict) -> str:
    """Extract dialog HTML from the structure for inclusion in the prompt."""
    dialogs = structure.get("dialogs", [])
    if not dialogs:
        return ""

    parts = []
    for d in dialogs:
        html = d.get("html", "")
        if not html:
            continue
        title = d.get("title", d.get("trigger", "Dialog"))
        trigger = d.get("trigger", "")
        parts.append(f"### 弹窗 HTML: {title} (触发: {trigger})\n```html\n{html}\n```")

    if parts:
        return "\n## 弹窗 HTML 快照（用于编写精确的 Steps 和字段引用）\n\n" + "\n\n".join(parts)
    return ""


def _to_camel_case(s: str) -> str:
    """arp → ARP, client_ssl → ClientSsl, routing_rules → RoutingRules"""
    words = s.replace("-", "_").split("_")
    # Single short word (like arp, vpn) → all caps
    if len(words) == 1 and len(words[0]) <= 4:
        return words[0].upper()
    return "".join(w.capitalize() for w in words)


def _to_feature_upper(s: str) -> str:
    """arp → ARP, client_ssl → CLIENTSSL"""
    return s.replace("-", "_").upper().replace("_", "")


def call_zhipu_api(api_key: str, feature: str, structure: dict, model: str = DEFAULT_MODEL) -> str:
    """Call the Zhipu GLM API via zai-sdk and return the full response text."""
    client = ZhipuAiClient(api_key=api_key)

    logger.info(f"Calling Zhipu API via zai-sdk: model={model}")
    start = time.time()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(feature, structure)},
        ],
        thinking={"type": "enabled"},
        max_tokens=65536,
        temperature=0.1,
    )

    elapsed = time.time() - start
    content = response.choices[0].message.content
    usage = getattr(response, "usage", {})
    logger.info(f"API response received in {elapsed:.1f}s")
    logger.info(f"Tokens: prompt={getattr(usage, 'prompt_tokens', '?')}, "
                f"completion={getattr(usage, 'completion_tokens', '?')}, "
                f"total={getattr(usage, 'total_tokens', '?')}")

    return content


def parse_response(response_text: str, feature: str = "") -> dict:
    """Parse the LLM response into a dict of {filepath: content}.

    Tries strict ===FILE: markers first, then falls back to heuristics.
    """
    files = {}

    # Primary pattern: ===FILE: path=== ```lang ... ``` ===END===
    pattern = r'===FILE:\s*(.+?)===\s*\n```(?:\w+)?\s*\n(.*?)\n```\s*\n===END==='
    matches = re.findall(pattern, response_text, re.DOTALL)

    for filepath, content in matches:
        filepath = filepath.strip()
        content = content.strip()
        if content:
            files[filepath] = content

    if files:
        logger.info(f"Parsed {len(files)} files from response (strict mode): {list(files.keys())}")
        return files

    # Fallback: find markdown code blocks and guess file paths from context
    logger.info("No ===FILE: markers found, trying fallback parser...")
    code_blocks = re.findall(r'```(\w+)?\s*\n(.*?)\n```', response_text, re.DOTALL)

    for i, (lang, content) in enumerate(code_blocks):
        content = content.strip()
        if not content or len(content) < 20:
            continue

        lang = (lang or "").lower()

        if lang == "csv" or content.startswith("Test ID,"):
            files[f"bin/test_data/manual_testcases/SonicWall_{feature.upper()}_Test_Cases.csv"] = content
        elif lang == "python":
            if "class " in content and "BasePage" in content and "def navigate_to_" in content:
                # looks like a page object
                files[f"bin/pages/{feature}.py"] = content
            elif "fw_pages" in content.lower() or "@property" in content[:200]:
                files["bin/pages/fw_pages.py UPDATE"] = content
            elif "pytest" in content or "fw_page" in content:
                files[f"bin/tests/test_{feature}.py"] = content
            # If can't determine, skip

    if files:
        logger.info(f"Parsed {len(files)} files from response (fallback mode): {list(files.keys())}")
    return files


def write_generated_files(files: dict, feature: str, dry_run: bool = False):
    """Write parsed files to disk."""
    output_root = _project_root

    for filepath, content in files.items():
        if filepath.endswith(" UPDATE"):
            # This is an update instruction, not a full file
            actual_path = filepath.replace(" UPDATE", "")
            logger.info(f"[UPDATE] {actual_path} — needs manual merge, printing diff:")
            print(f"\n{'─' * 60}")
            print(f"MERGE INTO: {actual_path}")
            print(f"{'─' * 60}")
            print(content)
            print(f"{'─' * 60}\n")
            continue

        # Resolve path
        if filepath.startswith("bin/"):
            full_path = _project_root.parent / filepath
        else:
            full_path = output_root / filepath

        if dry_run:
            logger.info(f"[DRY RUN] Would write {full_path} ({len(content)} bytes)")
            continue

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.info(f"[WRITE] {full_path} ({len(content)} bytes)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test files from page structure using Zhipu GLM API"
    )
    parser.add_argument("--feature", required=True, help="Feature name (e.g., arp, client_ssl)")
    parser.add_argument(
        "--structure",
        help="Path to page structure JSON (default: test_data/page_structure/{feature}_structure.json)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Zhipu model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Print generated code without writing files")
    parser.add_argument(
        "--response-file",
        help="Save raw API response to a file for review before parsing",
    )
    args = parser.parse_args()

    # 优先使用代码中配置的 Key，否则手动输入
    api_key = ZHIPU_API_KEY or input("请输入智谱 API Key: ").strip()
    if not api_key:
        logger.error("未输入 API Key，退出。")
        sys.exit(1)

    # Load page structure
    if args.structure:
        structure_path = Path(args.structure)
    else:
        structure_path = _project_root / "test_data" / "page_structure" / f"{args.feature}_structure.json"

    if not structure_path.exists():
        logger.error(f"Page structure file not found: {structure_path}")
        logger.info("Run page_inspector.py first:")
        logger.info(f"  python3 bin/tools/page_inspector.py --feature {args.feature} --url <URL>")
        sys.exit(1)

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    logger.info(f"Loaded page structure: {structure_path}")
    logger.info(f"  Tabs: L1={structure.get('tabs', {}).get('l1', [])}, L2={structure.get('tabs', {}).get('l2', [])}")
    logger.info(f"  Tables: {len(structure.get('tables', []))}")
    logger.info(f"  Buttons: {[b['text'] for b in structure.get('buttons', [])]}")
    logger.info(f"  Dialogs: {len(structure.get('dialogs', []))}")

    # Call API
    response_text = call_zhipu_api(api_key, args.feature, structure, args.model)

    # Optionally save raw response
    if args.response_file:
        Path(args.response_file).write_text(response_text, encoding="utf-8")
        logger.info(f"Raw response saved to: {args.response_file}")

    # Parse and write
    files = parse_response(response_text, args.feature)

    if not files:
        # Auto-save raw response for debugging
        debug_path = _project_root / "test_data" / "page_structure" / f"{args.feature}_raw_response.md"
        debug_path.write_text(response_text, encoding="utf-8")
        logger.error(f"No files found in response. Raw response saved to: {debug_path}")
        logger.error("Raw response preview:")
        print("\n" + response_text[:2000])
        sys.exit(1)

    write_generated_files(files, args.feature, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print(f"GENERATED FILES SUMMARY: {args.feature}")
    print("=" * 60)
    for fpath in files:
        status = "(dry run)" if args.dry_run else ""
        print(f"  {fpath} {status}")
    print("=" * 60)

    if args.dry_run:
        print("\n[Dry run complete. Use without --dry-run to write files.]")


if __name__ == "__main__":
    main()
