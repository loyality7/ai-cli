import os
import platform
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from ai_cli.ui.theme import COLORS, CHECK, CROSS, WARN
from ai_cli.core import db
from ai_cli.core.config import cfg, CONFIG_DIR, CONFIG_PATH, KEYS_PATH
from ai_cli.llm import get_provider
from ai_cli.llm.base import LLMMessage

console = Console()

def run_doctor(skip_llm: bool = False) -> bool:
    """Run all system diagnostic checks, log them to SQLite, and print reports."""
    session_id = f"doctor-{int(time.time())}"
    
    console.print()
    console.print(Panel(
        f"[bold cyan]AI-CLI Doctor System Diagnostics[/]\n"
        f"[dim]Checking CLI configuration, workspace integrity, and LLM connectivity[/]",
        border_style="cyan"
    ))
    
    db.log_session_action(session_id, "doctor_run_start")
    
    checks = []
    
    # ─── Check 1: Config Directories and Files ───
    if not CONFIG_DIR.exists():
        status = "failed"
        msg = f"Configuration folder {CONFIG_DIR} does not exist."
    elif not CONFIG_PATH.exists():
        status = "failed"
        msg = f"Configuration file {CONFIG_PATH} is missing."
    else:
        status = "passed"
        msg = f"Config folders and file verified at {CONFIG_PATH}."
    checks.append(("Config File Path", status, msg))
    
    # ─── Check 2: Config Parameters ───
    if status == "passed":
        provider = cfg.get("provider")
        model = cfg.get("model")
        if not provider or not model:
            status = "failed"
            msg = "Provider or Model is not set in config. Run 'ai --setup'."
        else:
            status = "passed"
            msg = f"Configured provider: '{provider}', model: '{model}'."
    else:
        status = "failed"
        msg = "Skipped config validation due to missing file."
    checks.append(("Configuration Parameters", status, msg))
    
    # ─── Check 3: API Key Verification ───
    api_key_set = False
    provider = cfg.get("provider")
    if provider:
        # Check env var or keys file
        env_key_name = f"AI_CLI_{provider.upper()}_API_KEY"
        if os.environ.get(env_key_name):
            api_key_set = True
            msg = f"API Key for {provider} loaded from environment variable: {env_key_name}."
        elif KEYS_PATH.exists():
            from ai_cli.core.config import _load_toml
            keys = _load_toml(KEYS_PATH)
            if keys.get(provider):
                api_key_set = True
                msg = f"API Key for {provider} loaded from keys file: {KEYS_PATH}."
            else:
                msg = f"API Key for {provider} is missing from keys file: {KEYS_PATH}."
        else:
            msg = f"No keys file found at {KEYS_PATH} and no env variables set."
            
        status = "passed" if api_key_set else "failed"
    else:
        status = "failed"
        msg = "Provider not set. Cannot verify API key."
    checks.append(("API Key Configuration", status, msg))
    
    # ─── Check 4: Git Repository Status ───
    is_git = Path(".git").exists()
    status = "passed" if is_git else "warning"
    msg = "Git repository detected." if is_git else "Current workspace is not a Git repository."
    checks.append(("Git Integration", status, msg))
    
    # ─── Check 5: Project Manifest ───
    manifests = ["pyproject.toml", "package.json", "Cargo.toml", "go.mod", "requirements.txt"]
    found_manifests = [m for m in manifests if Path(m).exists()]
    if found_manifests:
        status = "passed"
        msg = f"Project files found: {', '.join(found_manifests)}."
    else:
        status = "warning"
        msg = "No standard project manifests (pyproject.toml, package.json) found in current directory."
    checks.append(("Workspace Manifests", status, msg))
    
    # ─── Check 6: LLM Provider Connectivity ───
    if skip_llm:
        status = "warning"
        msg = "LLM Connectivity diagnostics check was skipped by user request."
    elif api_key_set:
        with console.status("  [bold yellow]Verifying connection to LLM provider...[/]"):
            try:
                # Test connectivity using complete method from base provider
                llm = get_provider()
                res = llm.complete(
                    messages=[LLMMessage(role="user", content="ping")],
                    max_tokens=10,
                )
                if res and res.content:
                    status = "passed"
                    msg = f"Connection verified. Response: '{res.content[:30].strip()}...'"
                else:
                    status = "warning"
                    msg = "Connection returned empty response."
            except Exception as e:
                status = "warning"
                msg = f"Failed to connect to LLM provider: {str(e)}"
    else:
        status = "warning"
        msg = "Skipped connectivity check due to missing API Key."
    checks.append(("LLM Connectivity", status, msg))
    
    # ─── Check 7: Bandit Security Scan ───
    import subprocess  # nosec B404
    import json
    with console.status("  [bold yellow]Running Bandit security scan...[/]"):
        try:
            # Scan the package, silencing standard shell exec warnings (B404, B603) which are core features of this tool
            cmd = [sys.executable, "-m", "bandit", "-r", "ai_cli", "-f", "json", "-s", "B404,B603"]
            proc = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
            if proc.stdout.strip():
                try:
                    data = json.loads(proc.stdout)
                    results = data.get("results", [])
                    if results:
                        status = "warning"
                        msg = f"Detected {len(results)} code issues (e.g. {results[0].get('issue_text')} in {results[0].get('filename')}:{results[0].get('line_number')})."
                    else:
                        status = "passed"
                        msg = "No security issues detected in python code."
                except Exception:
                    status = "warning"
                    msg = "Failed to parse Bandit JSON output."
            else:
                status = "warning"
                msg = f"Bandit scan failed to run: {proc.stderr.strip()}"
        except Exception as e:
            status = "warning"
            msg = f"Skipped: Bandit is not installed or executable failed ({str(e)})."
            
    checks.append(("Bandit Security Scan", status, msg))
    
    # Log all checks to SQLite
    all_passed = True
    for name, stat, message in checks:
        db.log_doctor_report(session_id, name, stat, message)
        if stat == "failed":
            all_passed = False
            
    db.log_session_action(session_id, "doctor_run_complete", {"all_passed": all_passed})
    
    # Render table of checks
    table = Table(expand=True)
    table.add_column("Diagnostic Check", style="cyan", width=30)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Details", style="dim", width=55)
    
    for name, stat, message in checks:
        if stat == "passed":
            stat_lbl = f"[green]{CHECK} PASSED[/]"
        elif stat == "warning":
            stat_lbl = f"[yellow]{WARN} WARNING[/]"
        else:
            stat_lbl = f"[red]{CROSS} FAILED[/]"
            
        table.add_row(name, stat_lbl, message)
        
    console.print()
    console.print(table)
    console.print()
    
    # Print advice panel
    if all_passed:
        console.print(Panel(
            "[bold green]System checks completed successfully![/]\n"
            "All configurations and network endpoints are healthy. Ready to run.",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold red]Doctor detected failures in your system environment[/]\n"
            "Please check the failed points in the table above and resolve them.\n"
            "  - Run [bold cyan]ai --setup[/] to reconfigure your provider keys and models.\n"
            "  - Set up appropriate environment variables if you are utilizing custom local models.",
            border_style="red"
        ))
        
    console.print()
    return all_passed
