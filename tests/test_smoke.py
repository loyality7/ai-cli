import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 1. Config
from ai_cli.core.config import cfg, detect_os, detect_shell
print(f"[config] OS={detect_os()}, Shell={detect_shell()}, Configured={cfg.is_configured}")

# 2. LLM factory
from ai_cli.llm.factory import PROVIDER_MAP, PROVIDER_MODELS
print(f"[llm] Providers: {list(PROVIDER_MAP.keys())}")

# 3. Planner
from ai_cli.executor.planner import extract_commands
text = """Try this:
```bash
ls -la
```

And be careful with:
```bash
rm -rf /tmp/test
```
"""
cmds = extract_commands(text)
for c in cmds:
    print(f"[planner] cmd='{c.command}' risk={c.risk.value}")

# 4. Context
from ai_cli.core.context import build_context
ctx = build_context()
lines = ctx.splitlines()
print(f"[context] {len(lines)} lines of context captured")

# 5. Printer (just import check)
from ai_cli.ui.printer import console, stream_markdown, print_command
print("[printer] OK")

# 6. Theme
from ai_cli.ui.theme import CHECK, CROSS, ARROW_RIGHT, APP_NAME
print(f"[theme] {CHECK} {APP_NAME} glyphs working")

# 7. Onboard (import check)
from ai_cli.ui.onboard import run_onboarding
print("[onboard] OK")

# 8. History
from ai_cli.core.history import Session
s = Session(session_id="test")
s.add("user", "hello")
s.add("assistant", "hi there")
print(f"[history] {len(s.entries)} entries, messages={len(s.messages)}")

print("\nAll modules OK!")
