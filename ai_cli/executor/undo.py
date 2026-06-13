"""
Undo / snapshot manager.

Before risky operations:
  - Files → copy to ~/.config/ai-cli/snapshots/
  - Git   → git stash
  - npm   → snapshot package.json + lockfile

All actions logged to ~/.config/ai-cli/history/actions.json
"""

import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from ai_cli.core.config import SNAPSHOTS_DIR


@dataclass
class Snapshot:
    """A file snapshot for undo."""
    timestamp: float
    original_path: str
    snapshot_path: str
    action: str            # what was done ("modified", "deleted", "created")


@dataclass
class UndoLog:
    """Log of all snapshots for undo functionality."""
    entries: list[Snapshot] = field(default_factory=list)

    @property
    def _log_path(self) -> Path:
        return SNAPSHOTS_DIR / "undo_log.json"

    def snapshot_file(self, file_path: str, action: str = "modified") -> None:
        """Create a backup of a file before modifying it."""
        src = Path(file_path)
        if not src.exists():
            return

        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        # Create snapshot with timestamp in name
        ts = int(time.time() * 1000)
        snapshot_name = f"{ts}_{src.name}"
        dest = SNAPSHOTS_DIR / snapshot_name

        shutil.copy2(str(src), str(dest))

        entry = Snapshot(
            timestamp=time.time(),
            original_path=str(src.resolve()),
            snapshot_path=str(dest),
            action=action,
        )
        self.entries.append(entry)
        self._save()

    def undo_last(self) -> Optional[Snapshot]:
        """Restore the most recent snapshot."""
        self._load()
        if not self.entries:
            return None

        entry = self.entries.pop()
        snapshot = Path(entry.snapshot_path)
        original = Path(entry.original_path)

        if snapshot.exists():
            if entry.action == "created":
                # If the file was created, undo means delete it
                original.unlink(missing_ok=True)
            else:
                # Restore the backup
                shutil.copy2(str(snapshot), str(original))
            snapshot.unlink()

        self._save()
        return entry

    def _save(self) -> None:
        """Persist undo log."""
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self.entries[-100:]]  # keep last 100
        self._log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Load undo log from disk."""
        if self._log_path.exists():
            try:
                data = json.loads(self._log_path.read_text(encoding="utf-8"))
                self.entries = [Snapshot(**e) for e in data]
            except Exception:
                self.entries = []


# Singleton
undo_log = UndoLog()
