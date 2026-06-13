"""
Planner — extracts actionable commands from LLM responses.

Parses markdown code blocks and identifies shell commands
the user might want to execute.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """How dangerous is this action?"""
    READ = "read"          # safe to auto-execute (ls, cat, git status)
    MODIFY = "modify"      # needs y/n confirmation (install, write files)
    DANGER = "danger"      # explicit warning + confirmation (rm -rf, format, DROP)


@dataclass
class ExtractedCommand:
    """A command extracted from LLM output."""
    command: str
    language: str        # "bash", "powershell", "cmd", "sh", etc.
    risk: RiskLevel
    description: str = ""


def assess_risk(command: str) -> RiskLevel:
    """
    Assess the risk level of a command locally.
    Acts as a fallback if the AI didn't tag the block-level risk metadata.
    Designed with a strong focus on Windows (PowerShell & cmd.exe) and cross-platform tools.
    """
    cmd_lower = command.strip().lower()
    
    # Destructive Windows & cross-platform commands/keywords
    destructive_keywords = [
        # Linux/macOS recursive deletes
        "rm -rf", "rm -r",
        # Windows cmd / PowerShell deletes
        "rmdir /s", "del /s", "del /f", "erase /s", "rd /s",
        "remove-item -recurse", "remove-item -force",
        # Disk / system modifications
        "format ", "mkfs", "diskpart",
        # Process killers (destructive/interruptive)
        "stop-process", "kill -force", "taskkill /f",
        # Git destructive operations
        "git reset --hard",
        # Uninstallers / package removals (must confirm)
        "uninstall", "remove-package", "uninstall-package", "remove-appxpackage"
    ]
    if any(k in cmd_lower for k in destructive_keywords):
        return RiskLevel.DANGER
        
    if "git" in cmd_lower and ("--force" in cmd_lower or " -f" in cmd_lower or " -d" in cmd_lower):
        return RiskLevel.DANGER
        
    # Read-only starting commands (cmd.exe, PowerShell, and Git/networking)
    read_starts = (
        # Basic Navigation/Directory Info
        "ls", "dir", "tree", "pwd", "cd ", "chdir", "get-location", "gl", "get-childitem", "gci",
        # File viewing/inspection
        "cat", "type", "more", "less", "head", "tail", "get-content", "gc", "jq", "bat",
        # System status/process/environment info
        "whoami", "hostname", "systeminfo", "ver", "vol", "uname", 
        "get-process", "gps", "ps", "get-service", "gsv", "get-command", "gcm", "get-help",
        # Safe outputs/displays
        "echo", "write-host", "write-output",
        # Networking tools (safe info/testing)
        "ping", "test-connection", "ipconfig", "nslookup", "dig", "curl", "wget", "netstat",
        # Git read-only
        "git status", "git log", "git diff", "git show", "git branch", "git remote", "git tag"
    )
    
    # Redirection checks
    has_redirect = (
        ">" in command or 
        "|" in command or 
        "out-file" in cmd_lower or 
        "set-content" in cmd_lower or 
        "add-content" in cmd_lower or
        "export-csv" in cmd_lower
    )
    
    if cmd_lower.startswith(read_starts) and not has_redirect:
        return RiskLevel.READ
        
    return RiskLevel.MODIFY


def extract_commands(text: str) -> list[ExtractedCommand]:
    """
    Extract shell commands from markdown code blocks in LLM output.

    Looks for block-level risk tags in the form of comments:
        # risk: read
        # risk: modify
        # risk: danger
    """
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    commands = []
    shell_langs = {"bash", "sh", "zsh", "powershell", "cmd", "shell", "console", "terminal", ""}

    for lang, content in matches:
        lang = lang.strip().lower()
        if lang not in shell_langs:
            continue

        # Check for block-level risk tag comment
        block_risk = None
        for line in content.strip().splitlines():
            line_strip = line.strip()
            match = re.match(r"^(?:#|//|::)\s*is_dangerous:\s*(true|false)", line_strip, re.IGNORECASE)
            if match:
                is_danger = match.group(1).lower() == "true"
                block_risk = RiskLevel.DANGER if is_danger else RiskLevel.READ
                break

        # Extract commands from lines
        for line in content.strip().splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith("//") or line.startswith("::"):
                continue
            # Skip prompt prefixes
            if line.startswith("$ "):
                line = line[2:]
            elif line.startswith("> "):
                line = line[2:]

            local_risk = assess_risk(line)
            # Local safety rule escalation takes priority over LLM metadata tags
            def _get_risk_score(lvl):
                if lvl == RiskLevel.DANGER: return 2
                if lvl == RiskLevel.MODIFY: return 1
                return 0

            if block_risk is not None:
                risk = local_risk if _get_risk_score(local_risk) > _get_risk_score(block_risk) else block_risk
            else:
                risk = local_risk

            commands.append(ExtractedCommand(
                command=line,
                language=lang or "shell",
                risk=risk,
            ))

    return commands


def extract_first_command(text: str) -> Optional[ExtractedCommand]:
    """Extract just the first shell command from LLM output."""
    commands = extract_commands(text)
    return commands[0] if commands else None
