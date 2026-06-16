# 定位器自愈 — 选择器故障自动修复

基于 **Playwright + pytest + 智谱 GLM** 的 SonicWall Web UI 定位器自愈系统。当 SonicOS 固件升级导致 CSS 选择器失效时，`@self_heal` 装饰器自动拦截异常、分析页面 DOM、生成替代选择器、重试执行、修复源码、学习规则——全程无需人工介入。

> 一句话：**一次 AI 调用修复错误，下次零调用直接通过。**

---
<img width="1430" height="980" alt="Image" src="https://github.com/user-attachments/assets/83b9971e-5d90-4908-a8cd-4d6693b3908f" />


## 1. 项目简介

本项目是 SonicWall SonicOS 7 防火墙 Web UI 的自动化测试框架，核心技术栈：

| 层级 | 技术 |
|---|---|
| 浏览器自动化 | Playwright (Chromium) |
| 测试框架 | pytest |
| AI 后端 | 智谱 GLM-4-Flash / Anthropic Claude / MCP |
| 语言 | Python 3.8+ |

核心文件：

| 文件 | 说明 |
|---|---|
| `bin/run_tests.py` | CLI 入口，构建并执行 pytest 命令 |
| `bin/conftest.py` | pytest fixtures / hooks / 自动登录 |
| `bin/tools/self_healing_locator.py` | **自愈引擎全部逻辑** |
| `bin/pages/` | Page Object 层 |
| `bin/tests/` | pytest 测试用例 |
| `bin/config/api_keys.json` | AI API Key 配置 |

---

## 2. Pytest 执行方式

### 基本命令

```bash
# 激活虚拟环境并运行测试
source /pytestbyai/UI_Playwright/.venv/bin/activate

# 运行指定测试文件
python3 bin/run_tests.py -t bin/tests/test_6_arp.py

# 指定防火墙 IP 和密码
python3 bin/run_tests.py -t bin/tests/test_6_arp.py \
    --fw_ip 10.8.105.173 --password password2

# 调试模式（显示详细日志，包括自愈过程）
python3 bin/run_tests.py -t bin/tests/test_6_arp.py \
    --fw_ip 10.8.105.173 --password password2 --debug

# 有头模式（可视化调试）
python3 bin/run_tests.py --headed --slowmo 500

# 按标记筛选（auto_login 自动处理登录流程）
python3 bin/run_tests.py -m auto_login

# 按关键字筛选
python3 bin/run_tests.py -k login

# demo cmd：
 source /pytestbyai/UI_Playwright/.venv/bin/activate && python3 /pytestbyai/UI_Playwright/bin/run_tests.py -t /pytestbyai/UI_Playwright/bin/tests/test_6_arp.py --fw_ip 10.8.105.173 --password password2
```

### 常用选项

| 选项 | 说明 |
|---|---|
| `-t <path>` | 指定测试文件路径 |
| `--fw_ip <ip>` | 防火墙 IP 地址 |
| `--password <pwd>` | 登录密码 |
| `--debug` | 启用 DEBUG 日志（含自愈详细过程） |
| `--headed` | 有头模式（显示浏览器窗口） |
| `--slowmo <ms>` | 操作延迟（调试用） |
| `--retries <n>` | 失败重试次数 |
| `--timeout <s>` | 单用例超时时间 |
| `-k <keyword>` | 按用例名称筛选 |

### 自愈日志过滤

```bash
# 只查看自愈相关日志
python3 bin/run_tests.py ... 2>&1 | grep -E "(HEALED|AI fallback|Rules updated|🔧|📋|📐|🎯)"
```

---

## 3. 选择器自愈机制

### 3.1 三级自愈管道

```
缓存命中 (0 API 调用)
  ↓ 未命中
规则匹配 (0 API 调用, 覆盖 ~70%)
  ↓ 规则不足/失败
AI 模型 (GLM / Claude / MCP)
  ↓ AI 成功后
自动学习：更新 _CLASS_SUBSTITUTIONS 规则表
```

| 级别 | 机制 | API 调用 | 延迟 |
|---|---|---|---|
| **cache** | 内存缓存 | 0 | < 0.1s |
| **rule-based** | 类名替换 + DOM 匹配 | 0 | < 1s |
| **AI** | 发送 DOM 骨架到 LLM | 1 | 3-15s |

### 3.2 装饰器使用

```python
from tools.self_healing_locator import self_heal

class MyPage(BasePage):
    # 仅诊断（CI 安全）
    @self_heal(description='点击 Add 按钮')
    def click_add_button(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

    # 自动重试
    @self_heal(description='点击 Add 按钮', auto_retry=True)
    def click_add_button_v2(self):
        self.page.locator('.sw-icon-button__label-cont:has-text("Add")').click()

    # 自动重试 + 修复源码
    @self_heal(description='点击 Cancel 按钮', auto_retry=True, auto_fix=True)
    def close_dialog(self):
        self.page.locator('.static-entry-modal__modal-footer-cancel').click()
```

### 3.3 装饰器参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `description` | str | (必填) | 方法功能描述，帮助 AI 理解目标 |
| `auto_retry` | bool | False | 自愈成功后自动重试执行 |
| `auto_fix` | bool | False | 重试成功后直接修改源码文件 |
| `ai_backend` | str | `"glm"` | AI 后端：`glm` / `claude` / `mcp` |
| `enable_rules` | bool | True | 启用规则匹配（0 API 调用） |
| `enable_cache` | bool | True | 启用内存缓存 |
| `max_retries` | int | 1 | 最大愈合尝试次数 |

### 3.4 AI 后端

| 后端 | API Key 配置 |
|---|---|
| `glm` | 环境变量 `ZHIPU_API_KEY` 或 `bin/config/api_keys.json` |
| `claude` | 环境变量 `ANTHROPIC_API_KEY` 或 `bin/config/api_keys.json` |
| `mcp` | 无需 Key，通过 Claude Code MCP 工具（双终端模式） |

### 3.5 降级策略

```
规则引擎成功 → 使用规则结果重试
  ↓ 重试失败
触发 AI 降级（跳过缓存，强制调用 AI）
  ↓ AI 愈合 + 重试成功
  自动修复源码 + 更新规则表（下次零调用）
  ↓ AI 愈合失败或重试失败
  抛出原始异常 → 测试失败 + 截图 + 报告
```

### 3.6 规则自动学习

当 AI 成功愈合后，框架自动对比 broken/healed 选择器的 CSS 类差异，将新的 (`old_class`, `new_class`) 映射写入 `_CLASS_SUBSTITUTIONS`：

```python
_CLASS_SUBSTITUTIONS = [
    # ...existing...
    # [rule-update 2026-06-16 02:29] AI healed `cancel-old` → `cancel`
    ("static-entry-modal__modal-footer-cancel-old", "static-entry-modal__modal-footer-cancel"),
]
```

下次相同问题直接用规则命中，**零 API 调用，零 AI 延迟**。

---

## 4. 自愈实例

### 4.1 故障场景

ARP 页面 `close_add_dialog` 方法中的 CSS 选择器因固件升级从 `.static-entry-modal__modal-footer-cancel` 变成了 `.static-entry-modal__modal-footer-cancel-old`（或反之），导致 `page.locator().click()` 执行超时：

```python
@self_heal(' ', auto_retry=True, auto_fix=True, ai_backend="glm", enable_rules=True)
def close_add_dialog(self) -> bool:
    self.page.locator('.static-entry-modal__modal-footer-cancel-old').click()
    self.page.wait_for_timeout(500)
    return True
```

### 4.2 完整自愈日志

```
🔧 Self-healing attempt 1/1: ARP.close_add_dialog        ← 异常被拦截
⚡ Triggered by TimeoutError (keywords: ['timeout'])       ← 触发原因
⚙️  Healing config: rules=ON, AI=glm, cache=ON            ← 配置摘要
🎯 Extracted broken selector from e.message               ← 提取失效选择器

🩺 Self-healing: `.static-entry-modal__modal-footer-cancel-old`
  Extracted 25 elements from page                         ← 提取页面 DOM

📋 HEALED via rule-based -> `text="Add"`                  ← 规则猜错（匹配到 Add 按钮）
🔄 AUTO-RETRY: redirecting → `text="Add"`
⚠️  Auto-retry failed: TimeoutError                        ← 执行失败（弹窗没关闭）

🔄 Rule-based selector failed, forcing AI fallback (glm)  ← 降级到 AI
  Extracted 25 elements from page
  ⏭️  Rules disabled, going straight to AI (glm)
🤖 AI (glm) response received (968 chars)                 ← GLM 返回候选
📋 HEALED via AI (glm) -> `.static-entry-modal__modal-footer-cancel` (score: 110)
🔄 AI fallback AUTO-RETRY
✅ AI fallback auto-retry SUCCESS                          ← 重试成功

✅ auto_fix: arp.py:50 源码已更新                           ← 修复 Page Object
📐 Rules updated: added 1 class substitution               ← 学习到规则表
```

### 4.3 AI 请求与响应

**发送给 GLM 的内容：**

```
You are a Playwright locator healing expert for SonicWall SonicOS 7.

## Broken Selector
`.static-entry-modal__modal-footer-cancel-old`

## Live Page Structure
{
  "url": "https://10.8.105.173/sonicui/7/m/mgmt/network/arp",
  "buttons": [
    {"tag": "button", "text": "Add",    "className": "sw-icon-button"},
    {"tag": "button", "text": "Cancel", "className": "static-entry-modal__modal-footer-cancel"},
    {"tag": "button", "text": "OK",     "className": "static-entry-modal__modal-footer-ok"}
  ],
  ...
}
```

**GLM 响应：**

```json
{
  "candidates": [
    {
      "selector": ".static-entry-modal__modal-footer-cancel",
      "strategy": "css",
      "confidence": "high",
      "reasoning": "The selector omits 'old' suffix and should match the cancel button."
    }
  ]
}
```

**Playwright 实时验证：**

| 候选 | count | visible | 评分 |
|---|---|---|---|
| `.static-entry-modal__modal-footer-cancel` | 1 | true | **110** ← 选中 |
| `button:has-text('Cancel')` | 1 | true | 100 |
| `#static-entry-modal-footer-cancel` | 0 | false | -1 |

### 4.4 修复结果

**Page Object 自动修复：**

```diff
- self.page.locator('.static-entry-modal__modal-footer-cancel-old').click()
+ # [self-healed 2026-06-16 02:29] `.cancel-old` -> `.cancel`
+ self.page.locator('.static-entry-modal__modal-footer-cancel').click()
```

**规则表自动扩充：**

```diff
  _CLASS_SUBSTITUTIONS = [
      ("sw-icon-button__label-cont", "sw-action-button__label-text"),
      ...
+     # [rule-update 2026-06-16 02:29] AI healed `cancel-old` → `cancel`
+     ("static-entry-modal__modal-footer-cancel-old", "static-entry-modal__modal-footer-cancel"),
  ]
```

### 4.5 第二次运行

当另一个测试用例再次遇到 `.static-entry-modal__modal-footer-cancel-old` 时，规则引擎直接命中：

```
📋 HEALED via rule-based -> `.static-entry-modal__modal-footer-cancel`
🔄 AUTO-RETRY: redirecting ...
✅ Auto-retry SUCCESS
```

**零 API 调用，零 AI 延迟，< 1 秒修复。**

---

## 5. API Key 配置

```json
// bin/config/api_keys.json
{
    "zhipu_api_key": "your-glm-api-key",
    "anthropic_api_key": "your-claude-api-key"
}
```

或通过环境变量：

```bash
export ZHIPU_API_KEY="your-glm-api-key"
export ANTHROPIC_API_KEY="your-claude-api-key"
```

---

## 6. 输出物

| 产出 | 路径 |
|---|---|
| 自愈报告 | `bin/test_data/healing_reports/healing_report_*.json` |
| 源码注释 | Page Object 中自动添加 `# [self-healed ...]` |
| 规则注释 | `bin/tools/self_healing_locator.py` 中自动添加 `# [rule-update ...]` |
| 失败截图 | `bin/screenshots/failures/SOSAIOT-TC-*.png` |

---

> 版本: v2.1 · 最后更新: 2026-06-16
