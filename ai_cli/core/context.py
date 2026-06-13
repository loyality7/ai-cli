"""
Context snapshot — gathers environment info for LLM calls.

Keeps it small and focused per the plan:
- cwd path
- directory listing (top-level only)
- git status + last 3 commits (if git repo)
- last terminal output (last 50 lines)
- runtime versions (python, node, docker)
- package.json scripts / pyproject.toml (if present)
- last 10 commands from session history
"""

import os
import platform
import subprocess  # nosec B404
from pathlib import Path
from typing import Optional


def _run_quiet(cmd: list[str], cwd: Optional[str] = None, timeout: int = 5) -> str:
    """Run a command quietly, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            shell=(platform.system() == "Windows"),  # nosec B602
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _get_dir_listing(cwd: str) -> str:
    """Top-level directory listing."""
    try:
        entries = sorted(os.listdir(cwd))
        dirs = [e + "/" for e in entries if os.path.isdir(os.path.join(cwd, e)) and not e.startswith(".")]
        files = [e for e in entries if os.path.isfile(os.path.join(cwd, e)) and not e.startswith(".")]
        return "\n".join(dirs + files)
    except Exception:
        return ""


def _get_git_info(cwd: str) -> Optional[str]:
    """Git status + last 3 commits if in a git repo."""
    # Check if git repo
    if not _run_quiet(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd):
        return None

    status = _run_quiet(["git", "status", "--short"], cwd=cwd)
    branch = _run_quiet(["git", "branch", "--show-current"], cwd=cwd)
    log = _run_quiet(
        ["git", "log", "--oneline", "-3", "--no-decorate"],
        cwd=cwd,
    )

    parts = [f"Branch: {branch}"]
    if status:
        parts.append(f"Changes:\n{status}")
    if log:
        parts.append(f"Recent commits:\n{log}")
    return "\n".join(parts)


_cached_runtime_versions = None


def _get_runtime_versions() -> str:
    """Detect installed runtimes (cached per session)."""
    global _cached_runtime_versions
    if _cached_runtime_versions is not None:
        return _cached_runtime_versions

    versions = []
    for cmd, label in [
        (["python", "--version"], "Python"),
        (["node", "--version"], "Node"),
        (["docker", "--version"], "Docker"),
    ]:
        v = _run_quiet(cmd)
        if v:
            versions.append(f"{label}: {v}")
            
    _cached_runtime_versions = "\n".join(versions)
    return _cached_runtime_versions


def _get_project_info(cwd: str) -> Optional[str]:
    """Read project metadata if present."""
    # package.json
    pkg_json = Path(cwd) / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", "unknown")
            scripts = data.get("scripts", {})
            script_list = ", ".join(scripts.keys()) if scripts else "none"
            return f"Node project: {name}\nScripts: {script_list}"
        except Exception:  # nosec B110
            pass

    # pyproject.toml
    pyproject = Path(cwd) / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            name = data.get("project", {}).get("name", "unknown")
            scripts = data.get("project", {}).get("scripts", {})
            script_list = ", ".join(scripts.keys()) if scripts else "none"
            return f"Python project: {name}\nEntry points: {script_list}"
        except Exception:  # nosec B110
            pass

    return None


def build_context(
    cwd: Optional[str] = None,
    last_output: Optional[str] = None,
    session_history: Optional[list[str]] = None,
) -> str:
    """
    Build a compact context snapshot for the LLM.
    Returns a formatted string to inject into the user message.
    """
    cwd = cwd or os.getcwd()
    sections: list[str] = []

    # CWD
    sections.append(f"[cwd] {cwd}")

    # Directory listing
    listing = _get_dir_listing(cwd)
    if listing:
        sections.append(f"[files]\n{listing}")

    # Git info
    git = _get_git_info(cwd)
    if git:
        sections.append(f"[git]\n{git}")

    # Runtimes
    runtimes = _get_runtime_versions()
    if runtimes:
        sections.append(f"[runtimes]\n{runtimes}")

    # Project info
    project = _get_project_info(cwd)
    if project:
        sections.append(f"[project]\n{project}")

    # Last terminal output (capped at 50 lines)
    if last_output:
        lines = last_output.strip().splitlines()[-50:]
        sections.append("[last output]\n" + "\n".join(lines))

    # Session history (last 10)
    if not session_history:
        try:
            from ai_cli.core.history import Session
            recent = []
            for s_id in Session.list_sessions():
                s = Session.load(s_id)
                if s:
                    for cmd in reversed(s.command_history):
                        if cmd and cmd not in recent:
                            recent.insert(0, cmd)
                        if len(recent) >= 10:
                            break
                if len(recent) >= 10:
                    break
            session_history = recent
        except Exception:  # nosec B110
            pass

    if session_history:
        recent = session_history[-10:]
        sections.append("[recent commands]\n" + "\n".join(recent))

    return "\n\n".join(sections)
