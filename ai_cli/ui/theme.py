"""
Theme constants and styling for the terminal UI.

Uses unicode box-drawing characters for clean, professional output.
No emojis — just clean glyphs.
"""

# ──────────────────────────────────────────────
# Unicode glyphs
# ──────────────────────────────────────────────
ARROW_RIGHT = "▶"
ARROW_DOWN = "▼"
BULLET = "●"
BULLET_HOLLOW = "○"
CHECK = "✓"
CROSS = "✗"
WARN = "⚠"
INFO = "ℹ"
PROMPT_CHAR = "❯"
ELLIPSIS = "…"
SEPARATOR = "─"
CORNER_TL = "╭"
CORNER_TR = "╮"
CORNER_BL = "╰"
CORNER_BR = "╯"
VERTICAL = "│"
HORIZONTAL = "─"
DOT = "·"

# ──────────────────────────────────────────────
# Color palette
# ──────────────────────────────────────────────
COLORS = {
    "primary": "cyan",
    "secondary": "blue",
    "accent": "magenta",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "muted": "dim white",
    "highlight": "bold white",
    "command": "bold cyan",
    "danger": "bold red",
}

# ──────────────────────────────────────────────
# Style strings for Rich markup
# ──────────────────────────────────────────────
STYLES = {
    "title": "bold cyan",
    "subtitle": "dim cyan",
    "label": "bold white",
    "value": "white",
    "separator": "dim white",
    "prompt": "bold cyan",
    "input": "white",
    "ai_response": "white",
    "command_block": "bold green",
    "risk_read": "green",
    "risk_modify": "yellow",
    "risk_danger": "bold red",
}

# ──────────────────────────────────────────────
# Branding
# ──────────────────────────────────────────────
APP_NAME = "ai-cli"
APP_TAGLINE = "your terminal ai partner"
VERSION_LINE = f"{APP_NAME} {DOT} fast {DOT} no bloat {DOT} just works"
