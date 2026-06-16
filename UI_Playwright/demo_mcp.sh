#!/bin/bash
# ============================================================
# Claude Code + MCP Playwright — 一键启动脚本
#
# 用途：绕过 VSCode 插件的 API Key 限制，直接在终端里使用
#       MCP Playwright 工具登录 SonicWall 防火墙并生成测试
#
# 启动后输入：
#   gen-tests-mcp web_proxy, url: /m/mgmt/network/web-proxy
#
# 按 Ctrl+D 或输入 /exit 退出
# ============================================================

set -e

# ── 路径配置 ──
CLAUDE_BIN="/root/.vscode-server/extensions/anthropic.claude-code-2.1.156-linux-x64/resources/native-binary/claude"
PROJECT_DIR="/home/UI_Playwright_Local/UI_Playwright"
MCP_SERVER="${PROJECT_DIR}/bin/tools/mcp_playwright_server.py"

# ── 检查环境 ──
if [ ! -f "$CLAUDE_BIN" ]; then
    echo "❌ Claude CLI 未找到: $CLAUDE_BIN"
    exit 1
fi

if [ ! -f "$MCP_SERVER" ]; then
    echo "❌ MCP Server 未找到: $MCP_SERVER"
    exit 1
fi

# 自动加载凭据（VSCode 终端可能不继承插件环境变量）
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    if [ -f /tmp/claude_creds.sh ]; then
        source /tmp/claude_creds.sh
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    echo "❌ 未找到认证凭据"
    echo "   请在 VSCode 中运行此脚本，或: source /tmp/claude_creds.sh"
    exit 1
fi

# ── 生成 MCP 配置 ──
MCP_CONFIG=$(mktemp /tmp/mcp_config.XXXXXX.json)
cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "playwright": {
      "command": "/usr/bin/python3",
      "args": ["${MCP_SERVER}"],
      "cwd": "${PROJECT_DIR}"
    }
  }
}
EOF

# ── 清理函数 ──
cleanup() {
    rm -f "$MCP_CONFIG"
    echo ""
    echo "👋 已退出，MCP 临时配置已清理"
}
trap cleanup EXIT

# ── 启动 ──
# ── 检查 skill 文件 ──
SKILL_FILE="${PROJECT_DIR}/.claude/skills/gen-tests-mcp.md"
SKILL_FLAG=""
if [ -f "$SKILL_FILE" ]; then
    SKILL_FLAG="--append-system-prompt-file"
    echo "✅ 已加载 gen-tests-mcp skill"
else
    echo "⚠️  gen-tests-mcp skill 未找到，将使用默认模式"
fi

echo "╔══════════════════════════════════════════════════════╗"
echo "║   Claude Code + MCP Playwright                     ║"
echo "║   已加载 MCP 工具：                                 ║"
echo "║     • browser_login    登录防火墙                   ║"
echo "║     • browser_navigate 导航页面                     ║"
echo "║     • browser_snapshot 提取页面结构                  ║"
echo "║     • browser_click    点击元素                     ║"
echo "║     • browser_evaluate 验证选择器                   ║"
echo "║     • browser_type     输入文本                     ║"
echo "║     • browser_close    关闭浏览器                   ║"
echo "║                                                    ║"
echo "║   Demo 开场白：                                     ║"
echo "║     gen-tests-mcp web_proxy,                        ║"
echo "║       url: /m/mgmt/network/web-proxy,               ║"
echo "║       fw: 10.8.165.150                             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_DIR"
if [ -n "$SKILL_FLAG" ]; then
    "$CLAUDE_BIN" --mcp-config "$MCP_CONFIG" --append-system-prompt-file "$SKILL_FILE" "$@"
else
    "$CLAUDE_BIN" --mcp-config "$MCP_CONFIG" "$@"
fi
