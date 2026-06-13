"""
Rich-based terminal output.

Handles:
  - Streaming LLM output with live markdown rendering
  - Command display with syntax highlighting
  - Status messages, errors, warnings
  - Confirmation prompts

Inspired by shell_gpt's Printer classes + tAI's Rich panels.
"""

from typing import Generator, Optional
import random

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.rule import Rule

from ai_cli.ui.theme import (
    ARROW_RIGHT, BULLET, CHECK, CROSS, WARN, INFO,
    PROMPT_CHAR, SEPARATOR, VERTICAL, CORNER_TL, CORNER_BL,
    COLORS, STYLES, APP_NAME,
)

console = Console()


LOADING_PHRASES = [
    "brewing response",
    "consulting the matrix",
    "scanning mainframe",
    "quantum calculating",
    "parsing instructions",
    "decrypting thoughts",
    "synthesizing answer",
    "assembling electrons",
    "consulting the oracle",
    "bending space-time",
]

from rich.spinner import SPINNERS

# Register custom cyberpunk ASCII spinners
SPINNERS["cyber_bracket"] = {
    "interval": 80,
    "frames": ["(    )", "(=   )", "(==  )", "(=== )", "(====)", "( ===)", "(  ==)", "(   =)"]
}
SPINNERS["cyber_bars"] = {
    "interval": 100,
    "frames": ["[-   ]", "[--  ]", "[--- ]", "[----]", "[ ---]", "[  --]", "[   -]"]
}
SPINNERS["bouncing_bullet"] = {
    "interval": 80,
    "frames": ["(o   )", "( o  )", "(  o )", "(   o)", "(  o )", "( o  )"]
}
SPINNERS["classic_slash"] = {
    "interval": 50,
    "frames": ["\\", "|", "/", "-"]
}
SPINNERS["pulse"] = {
    "interval": 120,
    "frames": [".  ", ".. ", "...", " ..", "  .", "   "]
}
SPINNERS["progress_bar"] = {
    "interval": 150,
    "frames": ["[    ]", "[=   ]", "[==  ]", "[=== ]", "[====]"]
}
SPINNERS["cyber_scanner"] = {
    "interval": 50,
    "frames": [
        "[=         ]",
        "[==        ]",
        "[===       ]",
        "[ ===      ]",
        "[  ===     ]",
        "[   ===    ]",
        "[    ===   ]",
        "[     ===  ]",
        "[      === ]",
        "[       ===]",
        "[        ==]",
        "[         =]",
        "[          ]",
        "[         =]",
        "[        ==]",
        "[       ===]",
        "[      === ]",
        "[     ===  ]",
        "[    ===   ]",
        "[   ===    ]",
        "[  ===     ]",
        "[ ===      ]",
        "[==        ]",
        "[=         ]"
    ]
}
SPINNERS["arrow_bounce"] = {
    "interval": 80,
    "frames": [
        "[>    ]",
        "[->   ]",
        "[-->  ]",
        "[---> ]",
        "[---->]",
        "[ --->]",
        "[  -->]",
        "[   ->]",
        "[    >]",
        "[   <-]",
        "[  <--]",
        "[ <-- ]",
        "[<--- ]",
        "[<    ]"
    ]
}

SPINNER_STYLES = [
    # (spinner_name, spinner_style_color, text_style)
    # Custom ASCII spinners
    ("cyber_bracket", "cyan", "bold white"),
    ("cyber_bars", "green", "bold green"),
    ("bouncing_bullet", "magenta", "bold magenta"),
    ("classic_slash", "yellow", "bold yellow"),
    ("pulse", "white", "bold white"),
    ("progress_bar", "cyan", "bold cyan"),
    ("cyber_scanner", "cyan", "bold white"),
    ("arrow_bounce", "green", "bold green"),
    # Classic/traditional built-in spinners
    ("aesthetic", "cyan", "bold white"),
    ("pipe", "green", "bold green"),
    ("clock", "magenta", "bold magenta"),
    ("growVertical", "yellow", "bold yellow"),
    ("bouncingBar", "cyan", "bold cyan"),
    ("moon", "blue", "bold white"),
    ("arc", "red", "bold red"),
    ("flip", "white", "bold white"),
    ("dots12", "magenta", "bold magenta"),
]


def get_random_loader(message: Optional[str] = None):
    """Return a Rich status context manager with a randomly selected ASCII spinner, color, and message."""
    phrase = message if message else random.choice(LOADING_PHRASES)  # nosec B311
    spinner_name, spinner_color, text_style = random.choice(SPINNER_STYLES)  # nosec B311
    return console.status(
        f"  [{text_style}]{phrase}[/]...",
        spinner=spinner_name,
        spinner_style=spinner_color,
    )


# ──────────────────────────────────────────────
# Streaming output
# ──────────────────────────────────────────────

def stream_markdown(chunks: Generator[str, None, None], code_theme: str = "dracula") -> str:
    """
    Stream LLM response with live markdown rendering.
    Shows a spinner until the first token arrives, then switches to live rendering.
    Returns the full response text.
    """
    full_text = ""
    first_chunk = True

    # Show spinner while waiting for first token
    with get_random_loader():
        for chunk in chunks:
            full_text += chunk
            if first_chunk:
                first_chunk = False
                break  # got first token, exit status context to start Live

    if not full_text:
        console.print(f"  [{COLORS['muted']}]no response[/]")
        return ""

    # Now stream the rest with live markdown rendering
    with Live(console=console, refresh_per_second=12) as live:
        md = Markdown(full_text, code_theme=code_theme)
        live.update(md)
        for chunk in chunks:
            full_text += chunk
            md = Markdown(full_text, code_theme=code_theme)
            live.update(md)

    return full_text


def stream_plain(chunks: Generator[str, None, None], color: str = "cyan") -> str:
    """
    Stream LLM response as plain colored text.
    Shows a spinner until the first token arrives.
    Returns the full response text.
    """
    full_text = ""
    first_chunk = True

    # Show spinner while waiting for first token
    with get_random_loader():
        for chunk in chunks:
            full_text += chunk
            if first_chunk:
                first_chunk = False
                break

    if not full_text:
        console.print(f"  [{COLORS['muted']}]no response[/]")
        return ""

    # Print first chunk and continue
    console.print(full_text, style=color, end="")
    for chunk in chunks:
        full_text += chunk
        console.print(chunk, style=color, end="")
    console.print()  # newline at end
    return full_text


def print_response(text: str, markdown: bool = True, code_theme: str = "dracula") -> None:
    """Print a complete (non-streamed) response."""
    if markdown:
        console.print(Markdown(text, code_theme=code_theme))
    else:
        console.print(text, style=COLORS["primary"])


# ──────────────────────────────────────────────
# Command display
# ──────────────────────────────────────────────

def print_command(command: str, language: str = "bash", title: str = "Command") -> None:
    """Display a command in a highlighted panel."""
    syntax = Syntax(command, language, theme="dracula", line_numbers=False)
    console.print(Panel(
        syntax,
        title=f"[{STYLES['title']}]{title}[/]",
        border_style=COLORS["success"],
        padding=(0, 1),
    ))


def print_command_result(output: str, success: bool = True) -> None:
    """Display command execution result."""
    if not output.strip():
        return

    style = COLORS["success"] if success else COLORS["error"]
    marker = CHECK if success else CROSS
    console.print(f"  [{style}]{marker}[/] Output:", style=STYLES["label"])
    for line in output.strip().splitlines():
        console.print(f"  {VERTICAL} {line}", style=COLORS["muted"])


# ──────────────────────────────────────────────
# Status messages
# ──────────────────────────────────────────────

def print_info(message: str) -> None:
    """Info message."""
    console.print(f"  [{COLORS['primary']}]{INFO}[/] {message}")


def print_success(message: str) -> None:
    """Success message."""
    console.print(f"  [{COLORS['success']}]{CHECK}[/] {message}")


def print_warning(message: str) -> None:
    """Warning message."""
    console.print(f"  [{COLORS['warning']}]{WARN}[/] {message}")


def print_error(message: str) -> None:
    """Error message."""
    console.print(f"  [{COLORS['error']}]{CROSS}[/] {message}")


def print_danger(message: str) -> None:
    """Danger warning — for destructive operations."""
    console.print(Panel(
        f"[{COLORS['danger']}]{WARN} DANGER: {message}[/]",
        border_style=COLORS["error"],
        padding=(0, 1),
    ))


# ──────────────────────────────────────────────
# Separators and headers
# ──────────────────────────────────────────────

def print_separator(title: Optional[str] = None) -> None:
    """Print a visual separator."""
    if title:
        console.print(Rule(title, style=STYLES["separator"]))
    else:
        console.print(Rule(style=STYLES["separator"]))


def print_header() -> None:
    """Print the app header for REPL mode."""
    import random

    logo1 = (
        "  [bold cyan]████████████[/][bold magenta]█████████████████[/]\n"
        "  [bold cyan]██▀▄─██▄─▄██[/][bold magenta]█─▄▄▄─█▄─▄███▄─▄█[/]\n"
        "  [bold cyan]██─▀─███─███[/][bold magenta]█─███▀██─██▀██─██[/]\n"
        "  [bold cyan]▀▄▄▀▄▄▀▄▄▄▀▀[/][bold magenta]▀▄▄▄▄▄▀▄▄▄▄▄▀▄▄▄▀[/]"
    )

    logo2 = (
        "  [bold cyan]▞▚ █ [/]  [bold magenta]❰ ▙▄ █ [/]"
    )

    logo3 = (
        "  [bold cyan]░█▀▀█ ░▀░ [/]  [bold magenta]▒█▀▀█ █░░ ░▀░[/]\n"
        "  [bold cyan]▒█▄▄█ ▀█▀ [/]  [bold magenta]▒█░░░ █░░ ▀█▀[/]\n"
        "  [bold cyan]▒█░▒█ ▀▀▀ [/]  [bold magenta]▒█▄▄█ ▀▀▀ ▀▀▀[/]"
    )

    logo4 = (
        "  [bold cyan]▄▀█ █ [/]  [bold magenta]█▀▀ █░░ █[/]\n"
        "  [bold cyan]█▀█ █ [/]  [bold magenta]█▄▄ █▄▄ █[/]"
    )

    selected_logo = random.choice([logo1, logo2, logo3, logo4])  # nosec B311

    console.print()
    console.print(selected_logo)
    console.print(f"  [{COLORS['muted']}]type naturally {BULLET} ctrl+c to exit[/]")
    console.print()


# ──────────────────────────────────────────────
# Loading / status
# ──────────────────────────────────────────────

def get_status(message: str = "Thinking"):
    """Return a Rich status context manager."""
    return get_random_loader(message)
