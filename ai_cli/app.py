"""
Main application — REPL loop and CLI entry point.

Usage:
    ai                    → opens persistent REPL session
    ai "fix this"         → one-shot mode
    ai --setup            → re-run onboarding
    ai --shell "list files" → shell-command-only mode
"""

import sys
import time
import uuid

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from ai_cli import __version__
from ai_cli.core.config import cfg, HISTORY_DIR
from ai_cli.core.context import build_context
from ai_cli.core.history import Session
from ai_cli.executor.planner import (
    RiskLevel,
    extract_commands,
)
from ai_cli.executor.runner import run_command, run_interactive
from ai_cli.llm import get_provider
from ai_cli.llm.base import LLMMessage
from ai_cli.prompts.system import get_system_prompt, get_shell_prompt
from ai_cli.ui import printer
from ai_cli.ui.onboard import run_onboarding
from ai_cli.ui.theme import (
    ARROW_RIGHT, BULLET, CHECK, CROSS, WARN,
    PROMPT_CHAR, COLORS, STYLES, APP_NAME,
)

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=False)


def _ensure_configured() -> bool:
    """Make sure the app is configured. Run onboarding if not."""
    if not cfg.is_configured:
        return run_onboarding()
    return True


def _read_key() -> str:
    """Read a single key from standard input in a cross-platform way."""
    import sys
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            ch2 = msvcrt.getch()
            if ch2 == b'K': return "left"
            if ch2 == b'M': return "right"
            if ch2 == b'H': return "up"
            if ch2 == b'P': return "down"
        if ch in (b'\r', b'\n'):
            return "enter"
        if ch == b'\x03':
            return "ctrl_c"
        try:
            return ch.decode("utf-8").lower()
        except UnicodeDecodeError:
            return ""
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                # Read next characters for escape sequence
                ch2 = sys.stdin.read(2)
                if ch2 == '[D': return "left"
                if ch2 == '[C': return "right"
                if ch2 == '[A': return "up"
                if ch2 == '[B': return "down"
            if ch in ('\n', '\r'):
                return "enter"
            if ch == '\x03':
                return "ctrl_c"
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _handle_command_execution(commands, session: Session) -> bool:
    """
    Handle extracted commands.
    Auto-executes safe (READ) commands.
    Prompts with an interactive arrow-key selector for MODIFY or DANGER commands.
    """
    from prompt_toolkit import prompt as pt_prompt
    from ai_cli.core import db
    executed = False

    for cmd_info in commands:
        # 1. Auto-execute Safe (READ) commands
        if cmd_info.risk == RiskLevel.READ:
            printer.print_command(cmd_info.command, cmd_info.language)
            console.print(f"  [{COLORS['success']}]{CHECK} Safe command: auto-executing...[/]")
            console.print(f"  [{COLORS['muted']}]running...[/]")
            result = run_command(cmd_info.command)
            printer.print_command_result(result.output, result.success)
            db.log_executed_command(
                session_id=session.session_id,
                command=cmd_info.command,
                risk_level=cmd_info.risk.name,
                status="executed",
                output=result.output
            )
            session.add(
                role="user",
                content=f"[command output]\nCommand: {cmd_info.command}\nOutput:\n{result.output}",
                command=cmd_info.command,
                output=result.output,
            )
            executed = True
            continue

        # 2. Risk-based confirmation for MODIFY or DANGER
        if cmd_info.risk == RiskLevel.DANGER:
            options = ["execute", "modify", "abort"]
            default_idx = 2  # default to abort
        else:
            # MODIFY risk
            options = ["execute", "modify", "abort"]
            default_idx = 0  # default to execute

        # Ask with interactive arrow key selector in a unified card panel
        choice = _ask_action(options=options, default_idx=default_idx, command_info=cmd_info)

        if choice == "execute":
            console.print(f"  [{COLORS['muted']}]running...[/]")
            result = run_command(cmd_info.command)
            printer.print_command_result(result.output, result.success)
            db.log_executed_command(
                session_id=session.session_id,
                command=cmd_info.command,
                risk_level=cmd_info.risk.name,
                status="executed",
                output=result.output
            )
            session.add(
                role="user",
                content=f"[command output]\nCommand: {cmd_info.command}\nOutput:\n{result.output}",
                command=cmd_info.command,
                output=result.output,
            )
            executed = True
        elif choice == "modify":
            edited = pt_prompt("  edit> ", default=cmd_info.command)
            if edited.strip():
                console.print(f"  [{COLORS['muted']}]running...[/]")
                result = run_command(edited.strip())
                printer.print_command_result(result.output, result.success)
                db.log_executed_command(
                    session_id=session.session_id,
                    command=edited.strip(),
                    risk_level=cmd_info.risk.name,
                    status="executed_modified",
                    output=result.output
                )
                session.add(
                    role="user",
                    content=f"[command output]\nCommand: {edited.strip()}\nOutput:\n{result.output}",
                    command=edited.strip(),
                    output=result.output,
                )
                executed = True
        else:
            db.log_executed_command(
                session_id=session.session_id,
                command=cmd_info.command,
                risk_level=cmd_info.risk.name,
                status="aborted"
            )
            printer.print_info("Skipped.")

    return executed


def _ask_action(options: list[str], default_idx: int = 0, command_info = None) -> str:
    """Prompt user using an interactive inline selection menu navigated via arrow keys."""
    from rich.live import Live
    from rich.text import Text
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.console import Group
    from rich.rule import Rule

    idx = default_idx

    def make_renderable(selected_idx: int):
        if command_info:
            is_danger = command_info.risk == RiskLevel.DANGER
            title = "Destructive Command" if is_danger else "Modify/Write Command"
            border_color = COLORS["error"] if is_danger else COLORS["success"]
            
            syntax = Syntax(command_info.command, command_info.language, theme="dracula", line_numbers=False)
            
            menu_text = Text()
            menu_text.append("  Action: ", style=STYLES["label"])
            for i, opt in enumerate(options):
                if i == selected_idx:
                    menu_text.append(f" ◀ {opt} ▶ ", style="bold reverse cyan")
                else:
                    menu_text.append(f"   {opt}   ", style="dim white")
                    
            if is_danger:
                danger_note = Text(f"  {WARN} DANGER: This command is destructive!", style=COLORS["danger"])
                group = Group(
                    syntax,
                    Rule(style=STYLES["separator"]),
                    danger_note,
                    menu_text
                )
            else:
                group = Group(
                    syntax,
                    Rule(style=STYLES["separator"]),
                    menu_text
                )
                
            return Panel(
                group,
                title=f"[{STYLES['risk_danger'] if is_danger else STYLES['title']}]{title}[/]",
                border_style=border_color,
                padding=(0, 1),
            )
        else:
            text = Text()
            text.append("  ❯ ", style=STYLES["prompt"])
            for i, opt in enumerate(options):
                if i == selected_idx:
                    text.append(f" ◀ {opt} ▶ ", style="bold reverse cyan")
                else:
                    text.append(f"   {opt}   ", style="dim white")
            return text

    # Show interactive menu
    with Live(make_renderable(idx), console=console, auto_refresh=False) as live:
        try:
            while True:
                key = _read_key()
                if key in ("left", "up"):
                    idx = (idx - 1) % len(options)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key in ("right", "down"):
                    idx = (idx + 1) % len(options)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key == "enter":
                    break
                elif key == "ctrl_c":
                    idx = options.index("abort") if "abort" in options else len(options) - 1
                    break
                elif key in ("e", "y"):
                    if "execute" in options:
                        idx = options.index("execute")
                        break
                elif key in ("m", "edit"):
                    if "modify" in options:
                        idx = options.index("modify")
                        break
                elif key in ("a", "n", "q"):
                    if "abort" in options:
                        idx = options.index("abort")
                        break
        except KeyboardInterrupt:
            idx = options.index("abort") if "abort" in options else len(options) - 1

    # Clear the menu line when finished
    console.print()
    return options[idx]


def _process_prompt(
    user_input: str,
    session: Session,
    shell_mode: bool = False,
) -> None:
    """
    Process a single user prompt.
    Sends to LLM, handles response, and automatically loops back with command outputs
    if any commands are executed, allowing the LLM to complete its answer.
    """
    first_turn = True
    current_input = user_input

    while True:
        # Build context and add user message (only on the first turn of this prompt)
        if first_turn:
            context = build_context(
                last_output=session.last_output,
                session_history=session.command_history,
            )
            if context:
                full_prompt = f"{current_input}\n\n--- Terminal Context ---\n{context}"
            else:
                full_prompt = current_input
            session.add(role="user", content=full_prompt)
            first_turn = False

        # Get provider
        try:
            provider = get_provider()
        except ValueError as e:
            printer.print_error(str(e))
            return

        system_prompt = get_shell_prompt() if shell_mode else get_system_prompt()

        # Build message list (include conversation history)
        messages = [LLMMessage(role=m["role"], content=m["content"]) for m in session.messages]

        # Stream response
        console.print()
        try:
            use_markdown = cfg.get("markdown", True) and not shell_mode
            code_theme = cfg.get("code_theme", "dracula")

            if cfg.get("streaming", True):
                chunks = provider.stream(
                    messages=messages,
                    system=system_prompt,
                    temperature=float(cfg.get("temperature", 0.0)),
                    max_tokens=int(cfg.get("max_tokens", 4096)),
                )
                if use_markdown:
                    response_text = printer.stream_markdown(chunks, code_theme)
                else:
                    response_text = printer.stream_plain(chunks)
            else:
                with printer.get_status("Thinking"):
                    response = provider.complete(
                        messages=messages,
                        system=system_prompt,
                        temperature=float(cfg.get("temperature", 0.0)),
                        max_tokens=int(cfg.get("max_tokens", 4096)),
                    )
                    response_text = response.content
                printer.print_response(response_text, markdown=use_markdown, code_theme=code_theme)

        except KeyboardInterrupt:
            console.print()
            printer.print_info("Interrupted.")
            return
        except Exception as e:
            printer.print_error(f"LLM error: {e}")
            return

        # Save assistant response
        session.add(role="assistant", content=response_text)

        # Check for background search/fetch tags
        import re
        search_match = re.search(r"\[SEARCH:\s*(.*?)\]", response_text, re.IGNORECASE)
        fetch_match = re.search(r"\[FETCH:\s*(.*?)\]", response_text, re.IGNORECASE)

        if search_match:
            query = search_match.group(1).strip()
            from ai_cli.core.web import search_web
            with printer.get_status(f"Searching the web"):
                results = search_web(query)
            session.add(
                role="user",
                content=f"[Search results for '{query}']:\n{results}"
            )
            continue

        if fetch_match:
            url = fetch_match.group(1).strip()
            from ai_cli.core.web import fetch_url
            with printer.get_status(f"Reading webpage"):
                results = fetch_url(url)
            session.add(
                role="user",
                content=f"[Content fetched from '{url}']:\n{results}"
            )
            continue

        # Extract and offer to execute commands
        commands = extract_commands(response_text)
        if commands:
            console.print()
            executed_any = _handle_command_execution(commands, session)
            if executed_any:
                # Loop back to let the LLM see the output and answer/update
                continue

        break

    console.print()


def _run_repl() -> None:
    """Main REPL loop."""
    if not _ensure_configured():
        printer.print_error("Setup cancelled. Run 'ai --setup' to configure.")
        raise typer.Exit(1)

    printer.print_header()

    # Session
    session_id = f"repl-{int(time.time())}"
    session = Session(session_id=session_id)
    from ai_cli.core import db
    db.log_session_action(session_id, "start_repl")

    # Prompt toolkit session with persistent history
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_DIR / "prompt_history")),
    )

    ctrl_c_pressed = False
    try:
        while True:
            try:
                user_input = prompt_session.prompt(
                    f" {PROMPT_CHAR} ",
                ).strip()

                # Reset Ctrl+C state on successful input
                ctrl_c_pressed = False

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "exit()", "q"):
                    break

                _process_prompt(user_input, session)

            except KeyboardInterrupt:
                if ctrl_c_pressed:
                    # Second Ctrl+C: exit
                    break
                else:
                    # First Ctrl+C: show warning
                    console.print()
                    console.print(f"  [{COLORS['muted']}]Press Ctrl+C again to exit[/]")
                    ctrl_c_pressed = True
                    continue
            except EOFError:
                break

    finally:
        # Save session on exit
        session.save()
        console.print()
        printer.print_info(f"Session saved [{COLORS['muted']}]{session_id}[/]")


# ──────────────────────────────────────────────
# CLI entry
# ──────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="Shell-command-only mode (no explanations).",
    ),
    setup: bool = typer.Option(
        False,
        "--setup",
        help="Re-run the setup wizard.",
    ),
    search: str = typer.Option(
        None,
        "--search",
        help="Search the web for information.",
    ),
    web: str = typer.Option(
        None,
        "--web",
        help="Fetch content of a URL/GitHub repo.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version.",
    ),
) -> None:
    """AI CLI — your terminal AI partner."""
    if ctx.invoked_subcommand is not None:
        return

    if version:
        console.print(f"{APP_NAME} v{__version__}")
        raise typer.Exit()

    if setup:
        run_onboarding()
        raise typer.Exit()

    if search:
        from ai_cli.core.web import search_web
        print(search_web(search))
        raise typer.Exit()

    if web:
        from ai_cli.core.web import fetch_url
        print(fetch_url(web))
        raise typer.Exit()

    # TTY and piped stdin handling (robust-tty-detection)
    if not sys.stdin.isatty():
        try:
            piped_input = sys.stdin.read().strip()
        except Exception:
            piped_input = ""
            
        if piped_input:
            prompt_str = "[Piped Input]:\n" + piped_input
        else:
            printer.print_error("Standard input is not a TTY. Please provide a prompt or pipe input.")
            raise typer.Exit(1)
            
        if not _ensure_configured():
            raise typer.Exit(1)
            
        session = Session(session_id=f"oneshot-{int(time.time())}")
        from ai_cli.core import db
        db.log_session_action(session.session_id, "start_oneshot_piped", {"prompt": prompt_str})
        _process_prompt(prompt_str, session, shell_mode=shell)
        session.save()
        raise typer.Exit()

    # REPL mode
    _run_repl()


@app.command()
def doctor(
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Skip LLM connectivity diagnostics.",
    )
) -> None:
    """Run system diagnostic checks on the environment and configuration."""
    from ai_cli.core.doctor import run_doctor
    success = run_doctor(skip_llm=skip_llm)
    raise typer.Exit(0 if success else 1)


@app.command()
def dashboard() -> None:
    """Show the usage statistics and system status control dashboard."""
    from ai_cli.core.dashboard import run_dashboard
    run_dashboard()


def entry_point() -> None:
    """Package entry point for `ai` command."""
    import sys
    subcommands = {"doctor", "dashboard"}
    args = sys.argv[1:]

    # If first argument is a prompt (not a subcommand or starts with "-")
    if args and args[0] not in subcommands and not args[0].startswith("-"):
        # Parse potential --shell or -s options from args
        shell_mode = False
        prompt_parts = []
        for arg in args:
            if arg in ("--shell", "-s"):
                shell_mode = True
            else:
                prompt_parts.append(arg)

        prompt_str = " ".join(prompt_parts)
        if prompt_str:
            if not _ensure_configured():
                sys.exit(1)

            import time
            session = Session(session_id=f"oneshot-{int(time.time())}")
            from ai_cli.core import db
            db.log_session_action(session.session_id, "start_oneshot", {"prompt": prompt_str})
            _process_prompt(prompt_str, session, shell_mode=shell_mode)
            session.save()
            sys.exit(0)

    # Otherwise fallback to Typer app
    app()


if __name__ == "__main__":
    entry_point()
