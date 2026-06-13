"""
Session history — tracks commands and conversations within a session.

Stores to ~/.config/ai-cli/history/ as JSON files.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from ai_cli.core.config import HISTORY_DIR


@dataclass
class HistoryEntry:
    """Single history entry."""
    timestamp: float
    role: str          # "user" | "assistant" | "system"
    content: str
    command: Optional[str] = None    # executed command, if any
    output: Optional[str] = None     # command output, if any


@dataclass
class Session:
    """A conversation session with history."""
    session_id: str
    entries: list[HistoryEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add(self, role: str, content: str, command: Optional[str] = None, output: Optional[str] = None) -> None:
        """Add an entry to the session."""
        self.entries.append(HistoryEntry(
            timestamp=time.time(),
            role=role,
            content=content,
            command=command,
            output=output,
        ))

    @property
    def messages(self) -> list[dict[str, str]]:
        """Convert to LLM message format."""
        return [
            {"role": e.role, "content": e.content}
            for e in self.entries
            if e.role in ("user", "assistant")
        ]

    @property
    def last_output(self) -> Optional[str]:
        """Get the last command output."""
        for entry in reversed(self.entries):
            if entry.output:
                return entry.output
        return None

    @property
    def command_history(self) -> list[str]:
        """Get list of commands executed this session."""
        return [e.command for e in self.entries if e.command]

    def save(self) -> None:
        """Persist session to disk."""
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        path = HISTORY_DIR / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, session_id: str) -> Optional["Session"]:
        """Load a session from disk."""
        path = HISTORY_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session = cls(session_id=data["session_id"], created_at=data["created_at"])
            for e in data["entries"]:
                session.entries.append(HistoryEntry(**e))
            return session
        except Exception:
            return None

    @classmethod
    def list_sessions(cls) -> list[str]:
        """List all saved session IDs."""
        if not HISTORY_DIR.exists():
            return []
        return [p.stem for p in sorted(HISTORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
