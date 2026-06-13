"""
First-run onboarding wizard.

Interactive setup that lets the user pick:
  1. Provider (Anthropic, OpenAI, Google, OpenRouter, Custom)
  2. Model (suggested list or custom input)
  3. API key
  4. Custom base URL (for custom/OpenRouter)

Inspired by tAI's config wizard but with better Rich UI.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

from ai_cli.core.config import cfg, set_api_key
from ai_cli.llm.factory import PROVIDER_MODELS, PROVIDER_BASE_URLS
from ai_cli.ui.theme import (
    BULLET, CHECK, ARROW_RIGHT, COLORS, STYLES, APP_NAME, SEPARATOR, WARN,
)

console = Console()

# Provider display info
PROVIDERS = [
    ("anthropic", "Anthropic", "Claude models — fast, smart, great for code"),
    ("openai", "OpenAI", "GPT models — versatile, widely supported"),
    ("google", "Google", "Gemini models — multimodal, competitive pricing"),
    ("openrouter", "OpenRouter", "Multi-provider gateway — access any model"),
    ("custom", "Custom", "Any OpenAI-compatible endpoint (Ollama, LM Studio, vLLM)"),
]


def run_onboarding() -> bool:
    """
    Run the interactive setup wizard.
    Returns True if setup completed successfully.
    """
    console.print()
    console.print(Panel(
        f"[{STYLES['title']}]Welcome to {APP_NAME}[/]\n"
        f"[{COLORS['muted']}]Let's get you set up in under a minute.[/]",
        border_style=COLORS["primary"],
        padding=(1, 2),
    ))
    console.print()

    # ── Step 1: Pick provider ──
    provider = _pick_provider()
    if not provider:
        return False

    # ── Step 2: Custom base URL (if needed) ──
    base_url = ""
    if provider == "custom":
        base_url = _get_base_url()
    elif provider == "openrouter":
        base_url = PROVIDER_BASE_URLS["openrouter"]

    # ── Step 3: Pick model ──
    model = _pick_model(provider)
    if not model:
        return False

    # ── Step 4: API key & Validation ──
    api_key = _get_api_key(provider, model, base_url)
    if not api_key:
        return False

    # ── Save config ──
    cfg.set_many({
        "provider": provider,
        "model": model,
        "api_base_url": base_url,
    })
    set_api_key(provider, api_key)

    provider_name = dict((k, n) for k, n, _ in PROVIDERS).get(provider, provider)
    console.print()
    console.print(Panel(
        f"[{COLORS['success']}]{CHECK} Setup complete![/]\n\n"
        f"  Provider  {ARROW_RIGHT}  [{COLORS['highlight']}]{provider_name}[/]\n"
        f"  Model     {ARROW_RIGHT}  [{COLORS['highlight']}]{model}[/]\n"
        f"  API Key   {ARROW_RIGHT}  [{COLORS['muted']}]{api_key[:8]}{'*' * 20}[/]\n"
        + (f"  Endpoint  {ARROW_RIGHT}  [{COLORS['muted']}]{base_url}[/]\n" if base_url else "")
        + f"\n[{COLORS['muted']}]Config saved to ~/.config/ai-cli/[/]",
        border_style=COLORS["success"],
        padding=(1, 2),
    ))
    console.print()

    return True


def _pick_provider() -> str:
    """Interactive provider selection using keyboard arrows."""
    from rich.live import Live
    from rich.text import Text
    from ai_cli.app import _read_key

    console.print(f"  [{STYLES['label']}]Select your AI provider (Use Up/Down arrows & Enter):[/]")
    console.print()

    idx = 0

    def make_renderable(selected_idx: int):
        text = Text()
        for i, (key, name, desc) in enumerate(PROVIDERS):
            if i == selected_idx:
                text.append(f"  ❯ {name:<14}  ", style="bold reverse cyan")
                text.append(f"{desc}\n", style="bold cyan")
            else:
                text.append(f"    {name:<14}  ", style="dim white")
                text.append(f"{desc}\n", style="dim white")
        return text

    with Live(make_renderable(idx), console=console, auto_refresh=False) as live:
        try:
            while True:
                key = _read_key()
                if key in ("up", "left"):
                    idx = (idx - 1) % len(PROVIDERS)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key in ("down", "right"):
                    idx = (idx + 1) % len(PROVIDERS)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key == "enter":
                    break
                elif key == "ctrl_c":
                    raise KeyboardInterrupt()
        except KeyboardInterrupt:
            console.print()
            raise SystemExit()

    provider_key = PROVIDERS[idx][0]
    console.print(f"  [{COLORS['success']}]{CHECK}[/] Selected Provider: [bold green]{PROVIDERS[idx][1]}[/]")
    console.print()
    return provider_key


def _pick_model(provider: str) -> str:
    """Interactive model selection using keyboard arrows."""
    from rich.live import Live
    from rich.text import Text
    from ai_cli.app import _read_key

    models = PROVIDER_MODELS.get(provider, [])

    if not models:
        # Custom provider — ask for model name directly
        model = Prompt.ask(f"  [{COLORS['primary']}]{ARROW_RIGHT}[/] Enter model name")
        return model.strip()

    options = list(models) + ["custom (type your own)"]
    idx = 0

    console.print(f"  [{STYLES['label']}]Select a model (Use Up/Down arrows & Enter):[/]")
    console.print()

    def make_renderable(selected_idx: int):
        text = Text()
        for i, opt in enumerate(options):
            if i == selected_idx:
                text.append(f"  ❯ {opt}\n", style="bold reverse cyan")
            else:
                text.append(f"    {opt}\n", style="dim white")
        return text

    with Live(make_renderable(idx), console=console, auto_refresh=False) as live:
        try:
            while True:
                key = _read_key()
                if key in ("up", "left"):
                    idx = (idx - 1) % len(options)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key in ("down", "right"):
                    idx = (idx + 1) % len(options)
                    live.update(make_renderable(idx))
                    live.refresh()
                elif key == "enter":
                    break
                elif key == "ctrl_c":
                    raise KeyboardInterrupt()
        except KeyboardInterrupt:
            console.print()
            raise SystemExit()

    if idx == len(models):
        model = Prompt.ask(f"  [{COLORS['primary']}]{ARROW_RIGHT}[/] Enter model name")
        return model.strip()

    selected = models[idx]
    console.print(f"  [{COLORS['success']}]{CHECK}[/] Selected Model: [bold green]{selected}[/]")
    console.print()
    return selected


def _get_api_key(provider: str, model: str, base_url: str) -> str:
    """Prompt for API key with masked feedback and validation."""
    from prompt_toolkit import prompt as pt_prompt

    provider_name = dict((k, n) for k, n, _ in PROVIDERS).get(provider, provider)
    console.print(f"  [{STYLES['label']}]Enter your {provider_name} API key:[/]")
    console.print(f"  [{COLORS['muted']}]Characters will show as {BULLET} for security[/]")

    while True:
        # prompt_toolkit shows * per character so you can see something is typed
        api_key = pt_prompt("  API Key: ", is_password=True).strip()

        if not api_key:
            console.print(f"  [{COLORS['error']}]{CROSS}[/] No key entered. Try again.")
            continue

        # Show a masked preview so they know it was captured
        masked = api_key[:4] + BULLET * min(len(api_key) - 8, 20) + api_key[-4:]
        if len(api_key) <= 8:
            masked = BULLET * len(api_key)
        console.print(f"  [{COLORS['muted']}]Received: {masked}[/] ({len(api_key)} chars)")

        # Quick validation using the collected model and custom base_url
        console.print(f"  [{COLORS['primary']}]Validating key...[/]", end="")
        if _validate_api_key(provider, api_key, model, base_url):
            console.print(f" [{COLORS['success']}]{CHECK} valid[/]")
        else:
            console.print(f" [{COLORS['warning']}]{WARN} could not verify (might still work or URL might be offline)[/]")

        console.print()
        return api_key


def _validate_api_key(provider: str, api_key: str, model: str, base_url: str) -> bool:
    """Quick test to check if an API key works."""
    try:
        from ai_cli.llm.factory import get_provider
        p = get_provider(
            provider_name=provider,
            model=model,
            api_key=api_key,
            base_url=base_url or None,
        )
        return p.validate()
    except Exception:
        return False


def _get_default_model_for_validation(provider: str) -> str:
    """Get a cheap model for key validation."""
    defaults = {
        "anthropic": "claude-haiku-4-5-20241022",
        "openai": "gpt-4.1-nano",
        "google": "gemini-2.0-flash",
        "openrouter": "openai/gpt-4o-mini",
        "custom": "gpt-3.5-turbo",
    }
    return defaults.get(provider, "gpt-3.5-turbo")


def _get_base_url() -> str:
    """Prompt for custom API base URL."""
    console.print(f"  [{STYLES['label']}]Enter your API endpoint URL:[/]")
    console.print(f"  [{COLORS['muted']}]e.g. http://localhost:11434/v1 for Ollama[/]")

    url = Prompt.ask(
        f"  [{COLORS['primary']}]{ARROW_RIGHT}[/] Base URL",
        default="http://localhost:11434/v1",
    )
    console.print(f"  [{COLORS['success']}]{CHECK}[/] {url}")
    console.print()
    return url.strip()
