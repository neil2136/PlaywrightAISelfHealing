# UI Playwright — SonicWall SonicOS 7 自动化测试框架

基于 **Playwright + pytest** 的 SonicWall 防火墙 Web UI (SonicOS 7) 自动化测试框架。核心创新：**AI 驱动的页面探索 → 代码生成 → 自愈定位** 全流水线。

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     bin/run_tests.py                         │
│                    (CLI 入口 / pytest 调度)                   │
├─────────────────────────────────────────────────────────────┤
│  bin/conftest.py           bin/config/                       │
│  (fixtures / hooks)        (settings / 浏览器 / logger / CSV) │
├─────────────────────────────────────────────────────────────┤
│  bin/tests/                bin/pages/                        │
│  (pytest 测试用例)          (Page Object 层)                  │
├─────────────────────────────────────────────────────────────┤
│  bin/tools/                                                  │
│  page_inspector.py  →  generate_tests.py  →  self_healing   │
│  (页面探索)           (AI 代码生成)           (定位器自愈)    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Playwright (`playwright install chromium`)
- 访问目标 SonicWall 防火墙 (默认 `192.168.168.168`)

### 运行测试

```bash
# 运行所有测试
python3 bin/run_tests.py

# 运行指定文件
python3 bin/run_tests.py -t bin/tests/test_6_arp.py

# 有头模式 (调试用)
python3 bin/run_tests.py --headed --slowmo 500

# 指定防火墙 IP 和密码
python3 /pytestbyai/UI_Playwright/bin/run_tests.py -t /pytestbyai/UI_Playwright/bin/tests/test_6_arp.py --fw_ip 10.8.165.173 --password password2

# 按标记筛选
python3 bin/run_tests.py -m auto_login

# 按关键字筛选
python3 bin/run_tests.py -k login

# 更多选项
python3 bin/run_tests.py --retries 2 --timeout 60 --debug --dry_run
```

## ✨ 核心能力

### 1. AI 页面探索 (`page_inspector.py`)

自动登录防火墙 → 导航到目标页面 → 遍历所有 Tab → 点击安全按钮打开弹窗 → 提取完整 DOM 骨架。

```bash
# python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --fw_ip 10.8.165.150 --headed
source /pytestbyai/UI_Playwright/.venv/bin/activate && python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --fw_ip 10.8.105.173 --password password2

# 交互式手动捕获模式
python3 bin/tools/page_inspector.py --feature arp --url /m/mgmt/network/arp --headed --manual
```

**自动提取:** 面包屑 · L1/L2 Tab · 表格(表头/列类型/行数) · 工具栏按钮 · 下拉框 · 模态弹窗(表单字段/HTML快照) · 行悬浮按钮 · 行点击弹窗

### 2. AI 代码生成 (`generate_tests.py`)

将页面骨架 JSON 发送到智谱 GLM API → 自动生成 **4 个交付物**:

| 产出 | 路径 |
|---|---|
| CSV 测试用例 | `bin/test_data/manual_testcases/SonicWall_{FEATURE}_Test_Cases.csv` |
| Page Object | `bin/pages/{subdir}/{feature}.py` |
| 测试文件 | `bin/tests/test_{number}_{feature}.py` |
| fw_pages 注册 | 控制台输出 (手动合并到 `fw_pages.py`) |

```bash
python3 bin/tools/generate_tests.py --feature arp
```

> 覆盖 **25+ 测试模式**: 页面加载、面包屑、Tab 切换、表格校验、添加/删除/导出/刷新、弹窗表单、XSS 注入、跨 Tab 未保存警告 等。

### 3. 定位器自愈 (`self_healing_locator.py`)

当 SonicOS 固件升级导致 UI 类名变更、CSS 选择器失效时，`@self_heal` 装饰器自动拦截 Playwright 异常 → 提取失败的选择器 → 执行三级自愈策略 → 重试执行。

#### 三级自愈管道

```
缓存命中 (0 API 调用)
  ↓ 未命中
规则匹配 (0 API 调用, 覆盖 ~70%)
  ↓ 规则不足/失败
AI 模型 (GLM / Claude / MCP)
  ↓ AI 成功后
自动学习：更新 _CLASS_SUBSTITUTIONS 规则表
```

| 级别 | 机制 | API 调用 | 说明 |
|---|---|---|---|
| **cache** | 内存缓存 (相同选择器+URL 直接命中) | 0 | 同一用例重复失败时跳过分析 |
| **rule-based** | 静态类名替换 + 页面元素匹配 + 意图匹配 | 0 | `_CLASS_SUBSTITUTIONS` 表自动扩充 |
| **AI (glm/claude/mcp)** | 发送页面 DOM 骨架到 AI 模型生成候选 | 1 | 规则失败或返回错误候选时降级触发 |

#### AI 后端选择

```python
@self_heal(description='...', ai_backend='glm')    # 智谱 GLM-4-Flash (默认)
@self_heal(description='...', ai_backend='claude') # Anthropic Claude
@self_heal(description='...', ai_backend='mcp')    # Claude Code MCP (双终端 demo)
```

API Key 配置: 环境变量 `ZHIPU_API_KEY` / `ANTHROPIC_API_KEY` 或 `bin/config/api_keys.json`。

#### 自动重试 & 自动修复

```python
class MyPage(BasePage):
    # 仅诊断 — 记录报告但不重试 (CI 安全)
    @self_heal(description='点击 Add 按钮')
    def click_add_button(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

    # 自动重试 — 愈合后立即用新选择器重新执行
    @self_heal(description='点击 Add 按钮', auto_retry=True)
    def click_add_button_v2(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

    # 自动修复 — 重试成功后直接更新 Page Object 源码
    @self_heal(description='点击 Cancel 按钮', auto_retry=True, auto_fix=True)
    def close_dialog(self):
        self.page.locator('.static-entry-modal__modal-footer-cancel').click()
```

#### 规则自动学习（v2.1 新增）

当 AI 模式成功愈合后，框架自动分析 broken/healed 选择器的 CSS 类差异，将新的类名映射追加到 `_CLASS_SUBSTITUTIONS`：

```
📋 HEALED via rule-based -> `text="Add"`           ← 规则猜错
⚠️ Auto-retry failed: TimeoutError
🔄 Rule-based selector failed, forcing AI fallback (glm)
📋 HEALED via AI (glm) -> `.modal-footer-cancel`   ← AI 正确
✅ AI fallback auto-retry SUCCESS
📐 Rules updated: added 1 class substitution       ← 学习规则写入源码
```

下次相同问题直接用规则命中，零 API 调用：
```
📋 HEALED via rule-based -> `.modal-footer-cancel` ← 第二次直接命中
```

源码中自动添加注释：
```python
_CLASS_SUBSTITUTIONS = [
    # ...existing rules...
    # [rule-update 2026-06-16 02:29] AI healed `static-entry-modal__modal-footer-cancel-old` → `static-entry-modal__modal-footer-cancel`
    ("static-entry-modal__modal-footer-cancel-old", "static-entry-modal__modal-footer-cancel"),
]
```

#### 日志排障指南

通过 `📋 HEALED via {mode}` 关键字快速定位愈合路径：

```
⚙️  Healing config: rules=ON, AI=glm, cache=ON      ← 配置摘要
⚡ Triggered by TimeoutError (keywords: timeout)       ← 触发原因
🎯 Extracted broken selector `...` (from e.message)   ← 选择器来源
📋 HEALED via cache -> `...`                          ← 最终愈合方式
📋 HEALED via rule-based -> `...`
📋 HEALED via AI (glm) -> `...`
❌ Healing FAILED — `...` could not be healed         ← 全部失败
```

```bash
# 调试模式 (显示详细日志)
python3 bin/run_tests.py -t bin/tests/test_6_arp.py --debug

# 过滤自愈相关日志
... 2>&1 | grep -E "(HEALED|AI fallback|Rules updated|🔧|📋|📐|🎯)"
```

#### 降级策略

```
规则引擎成功 → 使用规则结果重试
  ↓ 重试失败
触发 AI 降级 (enable_cache=False, enable_rules=False)
  ↓ AI 愈合 + 重试成功
  自动修复源码 + 更新规则表
  ↓ AI 愈合失败或重试失败
  抛出原始异常 → 测试失败
```

### 4. Claude Code Skills 系统

通过 `.claude/skills/` 中的 Markdown 技能文件，让 Claude Code 直接驱动浏览器执行 UI 自动化：

| 技能 | 触发词 | 功能 |
|---|---|---|
| `gen-basic-tests` | "generate basic cases" | 从 CSV 生成 Page Object + 测试文件 |
| `create-suite` | "create suite for" | 创建 CI/CD 遗留套件 (8 文件目录树) |

> 即将推出: `ui-explore` (语义页面探索) · `ui-execute-test` (AI 执行测试) · `ui-self-heal` (实时自愈)

## 📁 项目结构

```
UI_Playwright/
├── bin/                              # 🎯 框架根目录 (所有工作在此)
│   ├── run_tests.py                  # CLI 入口, 构建并执行 pytest 命令
│   ├── conftest.py                   # Pytest fixtures / hooks / 自定义选项
│   ├── pytest.ini                    # Pytest 配置 (标记 / 发现规则)
│   ├── config/
│   │   ├── settings.py               # Settings 全局配置 (路径/IP/密码/浏览器)
│   │   ├── playwright_manager.py     # Playwright 浏览器生命周期管理
│   │   ├── csv_reporter.py           # 测试结果 CSV 报告
│   │   └── logger.py                 # 彩色控制台 + 文件日志
│   ├── pages/                        # Page Object 层
│   │   ├── base_page.py              # 基础页面类 (~1500 行, 60+ 交互方法)
│   │   ├── login_page.py             # 登录页 (自动处理 Config/启动屏/警告)
│   │   ├── fw_pages.py               # FWPage 门面 (懒加载子页面缓存)
│   │   ├── Network/System/           # 网络 → 系统 子页面
│   │   ├── Policy/DPI_SSL/           # 策略 → DPI SSL 子页面
│   │   └── Object/Match_Objects/     # 对象 → 匹配对象 子页面
│   ├── tests/                        # Pytest 测试文件 (test_*.py)
│   │   ├── test_6_arp.py
│   │   ├── test_112_Network_Interfaces.py
│   │   ├── test_client_ssl.py
│   │   └── ...
│   ├── tools/                        # 自动化工具集
│   │   ├── page_inspector.py         # 页面骨架提取器
│   │   ├── generate_tests.py         # AI 代码生成器 (智谱 GLM API)
│   │   ├── self_healing_locator.py   # 定位器自愈引擎
│   │   ├── self_healing_demo.py      # 自愈演示脚本
│   │   └── check_connectivity.py     # API 连通性诊断
│   ├── test_data/
│   │   ├── manual_testcases/         # CSV 测试用例文件
│   │   ├── page_structure/           # 页面骨架 JSON 文件
│   │   └── healing_reports/          # 自愈报告 JSON
│   └── prompts/                      # AI 角色定义 (人设)
│       ├── gen-testcases.md          # 完整 25+ 模式映射规则
│       ├── gen-basic-tests.md        # 6 类基础测试模式
│       └── create-suite.md           # 测试套件架构师
├── .claude/
│   └── skills/                       # Claude Code 技能定义
│       ├── gen-basic-tests.md        # 从 CSV 生成测试代码
│       └── create-suite.md           # 创建遗留 CI/CD 套件
├── 6_ARP/                            # 遗留套件示例 (CI/CD 集成)
├── 112_Network_Interfaces/
├── 128_DPI_SSL_CLIENT_SSL/
├── CLAUDE.md                         # Claude Code 项目指南
└── README.md                         # 本文件
```

## 🔧 BasePage 核心 API

`bin/pages/base_page.py` 提供 **60+ 可复用交互方法**，所有 Page Object 继承自它：

| 类别 | 方法 |
|---|---|
| **导航** | `navigate_to_url`, `navigate_to_Top_tab`, `navigate_to_left_level_1_tab`, `navigate_to_main_tab` |
| **元素查找** | `find_element`, `click_element`, `fill_input`, `fill_input_by_label_name` |
| **等待** | `wait_for_selector`, `wait_for_load_state`, `is_element_visible` |
| **表格** | `get_table_header`, `get_table_row_count_by_container`, `extract_table_footer_total_count`, `get_table_row_locator` |
| **Tab** | `switch_tab`, `is_tab_active`, `get_active_tab` |
| **开关/复选框/单选框** | `click_toggle`, `set_toggle_by_locator`, `click_checkbox_by_input_name`, `click_radio_button_by_input_name` |
| **下拉框** | `select_value_in_dropdown_box`, `select_value_in_dropdown_box_use_input_name` |
| **弹窗/对话框** | `get_confirmation_dialog`, `click_dialog_button`, `click_close_icon_by_window_title` |
| **状态/消息** | `compare_status_message`, `accept_alert`, `get_status_info` |
| **颜色验证** | `is_orange_background`, `is_green_background`, `is_red_background` |
| **搜索** | `get_search_box_locator`, `fill_search_box` |

## 📝 添加新功能的标准流程

```bash
# Step 1: 探索页面 → 生成骨架 JSON
python3 bin/tools/page_inspector.py --feature <feature_name> \
  --url /m/mgmt/<path> --fw_ip <ip> --headed

# Step 2: AI 生成 Page Object + 测试 + CSV
python3 bin/tools/generate_tests.py --feature <feature_name>

# Step 3: 检查生成文件
#   - 核对容器 class 名称 (检查实际 HTML)
#   - 核对 Tab 名称和表头
#   - 手动合并 fw_pages.py 更新

# Step 4: 运行生成的测试
python3 bin/run_tests.py -t bin/tests/test_<number>_<feature>.py --headed

# Step 5 (可选): 创建 CI/CD 遗留套件
#   使用 Claude Code: "create suite for <number> <feature>"
```

## 🧪 测试编写约定

```python
import pytest
from config.settings import Settings
from config.logger import get_logger

logger = get_logger(__name__)
pytestmark = pytest.mark.auto_login(cache_key="feature_name")

class Test_01_navigate_to_feature_page:
    uuid = 'SOSAIOT-TC-FEAT-0001'

    def test_01_navigate(self, fw_page):
        fw_page.feature.navigate_to_feature()
        res = fw_page.verify_text_exists("Expected Page Title", timeout=10000)
        assert res, "Page not loaded"

# auto_login 标记自动处理:
#   1. 登录 (用户名/密码)
#   2. "Manual Configure" 启动屏
#   3. "Config" 抢占模式提示
#   4. "Proceed" 警告对话框
#   5. 等待主页面加载
# 相同 cache_key 的测试模块共享登录会话
```

## ⚙️ 配置

| 文件 | 说明 |
|---|---|
| `bin/config/settings.py` | `Settings.FIREWALL_IP` (默认 `192.168.168.168`) · `PASSWORD` · `USERNAME` · 浏览器参数 |
| `bin/config/playwright_manager.py` | 浏览器启动 / Context 管理 / HTTPS 证书忽略 |
| `bin/conftest.py` | `--fw_ip` / `--password` 自定义 pytest 选项 (session, autouse) |

> ⚠️ **重要**: Page Object 中 `self.url` 必须在 `__init__` 中设置 (不能放在类体)。类体在 `import` 时求值，早于 `--fw_ip` fixture 注入，会导致拿到默认 IP。

## 🤖 AI 代理人指南

本项目为 AI 编码助手（Claude Code 等）提供了完整的引导系统：

- **`CLAUDE.md`** — 完整项目文档和开发约定
- **`AGENTS.md`** — AI Agent 快速参考 (GitHub Copilot / 通用)
- **`.claude/skills/`** — 可触发的工作流技能
- **`bin/prompts/`** — 角色定义提示词 (生成测试/套件时使用)

## 📄 许可

Internal use — SonicWall QA automation framework.

---

> 框架版本: SonicOS 7 · Playwright (Chromium) · Pytest · Python 3.8+
