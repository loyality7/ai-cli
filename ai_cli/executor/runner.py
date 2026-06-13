"""
Cross-platform command runner.

Detects the current shell and executes commands properly on
Windows (PowerShell/cmd) and Unix (bash/zsh/sh).
"""

import os
import platform
import subprocess
import shlex
from dataclasses import dataclass
from typing import Optional

from ai_cli.core.config import detect_shell


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined output (stdout + stderr)."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n".join(parts)


def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 120,
    capture: bool = True,
) -> CommandResult:
    """
    Execute a shell command on the current platform.

    Args:
        command:  The command string to run.
        cwd:     Working directory (defaults to current).
        timeout: Max seconds to wait.
        capture: If True, capture stdout/stderr. If False, let it flow to terminal.

    Returns:
        CommandResult with exit code and output.
    """
    cwd = cwd or os.getcwd()
    shell_name = detect_shell()

    if platform.system() == "Windows":
        if shell_name == "powershell":
            full_cmd = ["powershell.exe", "-NoProfile", "-Command", command]
        else:
            full_cmd = ["cmd.exe", "/c", command]
        use_shell = False
    else:
        shell_path = os.environ.get("SHELL", "/bin/sh")
        full_cmd = [shell_path, "-c", command]
        use_shell = False

    try:
        if capture:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )
            return CommandResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        else:
            # Stream to terminal directly (interactive mode)
            result = subprocess.run(
                full_cmd,
                cwd=cwd,
                timeout=timeout,
            )
            return CommandResult(
                command=command,
                exit_code=result.returncode,
                stdout="",
                stderr="",
            )
    except subprocess.TimeoutExpired:
        return CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
        )
    except KeyboardInterrupt:
        return CommandResult(
            command=command,
            exit_code=130,
            stdout="",
            stderr="Command interrupted by user (Ctrl+C)",
        )
    except Exception as e:
        return CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=str(e),
        )


def run_interactive(command: str, cwd: Optional[str] = None) -> int:
    """
    Run a command interactively (output goes straight to terminal).
    Returns the exit code.
    """
    result = run_command(command, cwd=cwd, capture=False)
    return result.exit_code
