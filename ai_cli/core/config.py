"""
Configuration management for AI CLI.

Config:   ~/.config/ai-cli/config.toml
Keys:     ~/.config/ai-cli/keys.toml
History:  ~/.config/ai-cli/history/
Snapshots:~/.config/ai-cli/snapshots/

Env vars (AI_CLI_* prefix) always override file config.
"""

import os
import platform
import tomllib
from os.path import basename
from pathlib import Path
from typing import Any, Optional

import tomli_w

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
CONFIG_DIR = Path(os.path.expanduser("~/.config/ai-cli"))
CONFIG_PATH = CONFIG_DIR / "config.toml"
KEYS_PATH = CONFIG_DIR / "keys.toml"
HISTORY_DIR = CONFIG_DIR / "history"
SNAPSHOTS_DIR = CONFIG_DIR / "snapshots"

# ──────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────
DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "",          # set during onboarding
    "model": "",             # set during onboarding
    "temperature": 0.0,
    "max_tokens": 4096,
    "streaming": True,
    "markdown": True,
    "code_theme": "dracula",
    "color": "cyan",
    "shell_interaction": True,
    "request_timeout": 60,
    # For custom OpenAI-compatible endpoints
    "api_base_url": "",
}


# ──────────────────────────────────────────────
# TOML I/O
# ──────────────────────────────────────────────
def _load_toml(path: Path) -> dict:
    """Load a TOML file. Returns empty dict if missing or corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _save_toml(path: Path, data: dict) -> None:
    """Write dict to TOML file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


# ──────────────────────────────────────────────
# Config class
# ──────────────────────────────────────────────
class Config:
    """
    Layered config: env vars > config file > defaults.

    Access:
        cfg.get("model")           → resolves through layers
        cfg.set("model", "gpt-4o") → persists to file
        cfg.all                    → merged dict
    """

    def __init__(self) -> None:
        self._file: dict[str, Any] = _load_toml(CONFIG_PATH)
        self._defaults = DEFAULT_CONFIG.copy()

        # Auto-migrate new default keys into existing config
        if self._file:
            changed = False
            for key, val in self._defaults.items():
                if key not in self._file:
                    self._file[key] = val
                    changed = True
            if changed:
                self.save()

    def get(self, key: str, fallback: Any = None) -> Any:
        """Get value. Priority: env var > file > default > fallback."""
        env_val = os.getenv(f"AI_CLI_{key.upper()}")
        if env_val is not None:
            return env_val
        if key in self._file:
            return self._file[key]
        if key in self._defaults:
            return self._defaults[key]
        return fallback

    def set(self, key: str, value: Any) -> None:
        """Set a value and persist to disk."""
        self._file[key] = value
        self.save()

    def set_many(self, updates: dict[str, Any]) -> None:
        """Bulk update and persist."""
        self._file.update(updates)
        self.save()

    def save(self) -> None:
        """Write current config to disk."""
        _save_toml(CONFIG_PATH, self._file)

    @property
    def is_configured(self) -> bool:
        """True if provider + model + API key are set."""
        return bool(
            self.get("provider")
            and self.get("model")
            and get_api_key(self.get("provider"))
        )

    @property
    def all(self) -> dict:
        """Full merged config."""
        return {**self._defaults, **self._file}


# ──────────────────────────────────────────────
# API key management
# ──────────────────────────────────────────────
_ENV_KEY_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "custom": "OPENAI_API_KEY",      # custom endpoints use OpenAI-compatible keys
}


def get_api_key(provider: str) -> Optional[str]:
    """
    Resolve API key for a provider.
    Priority: env var > keys.toml
    """
    env_var = _ENV_KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")
    env_val = os.getenv(env_var)
    if env_val:
        return env_val

    keys = _load_toml(KEYS_PATH)
    return keys.get(provider)


def set_api_key(provider: str, key_value: str) -> None:
    """Store API key in keys.toml."""
    keys = _load_toml(KEYS_PATH)
    keys[provider] = key_value
    _save_toml(KEYS_PATH, keys)


# ──────────────────────────────────────────────
# Platform detection
# ──────────────────────────────────────────────
def detect_os() -> str:
    """Detect OS for system prompts."""
    system = platform.system()
    if system == "Linux":
        try:
            from distro import name as distro_name
            return f"Linux/{distro_name(pretty=True)}"
        except ImportError:
            return "Linux"
    if system == "Windows":
        return f"Windows {platform.release()}"
    if system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    return system


def detect_shell() -> str:
    """Detect current shell."""
    if platform.system() in ("Windows", "nt"):
        is_ps = len(os.getenv("PSModulePath", "").split(os.pathsep)) >= 3
        return "powershell" if is_ps else "cmd"
    return basename(os.getenv("SHELL", "/bin/sh"))


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
cfg = Config()
