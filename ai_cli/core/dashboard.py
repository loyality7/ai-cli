from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.layout import Layout
from ai_cli.core import db
from ai_cli.ui.theme import COLORS, CHECK, CROSS, WARN

console = Console()

def run_dashboard() -> None:
    """Render a terminal dashboard showing usage statistics and system health from SQLite."""
    stats = db.get_db_stats()
    doctor_checks = db.get_latest_doctor_reports()
    recent_cmds = db.get_recent_commands(limit=6)
    
    console.print()
    console.print(Panel(
        "[bold magenta]AI-CLI Operations Control Dashboard[/]\n"
        "[dim]Visualizing local command history, usage telemetry, and diagnostic health[/]",
        border_style="magenta"
    ))
    
    # 1. Statistics Cards
    stats_table = Table.grid(expand=True, padding=1)
    stats_table.add_column(ratio=1)
    stats_table.add_column(ratio=1)
    stats_table.add_column(ratio=1)
    
    sessions_panel = Panel(
        f"[bold cyan]{stats['total_actions']}[/]\n[dim]Logged actions & triggers[/]",
        title="Session Activity",
        border_style="cyan"
    )
    commands_panel = Panel(
        f"[bold green]{stats['total_commands']}[/]\n[dim]Shell commands run[/]",
        title="Command Telemetry",
        border_style="green"
    )
    
    doctor_status_str = "[dim]No scan history[/]"
    doctor_border = "dim"
    if doctor_checks:
        if stats["failed_checks"] > 0:
            doctor_status_str = f"[bold red]{stats['failed_checks']} Failures[/]\n[yellow]{stats['passed_checks']} Checks passed[/]"
            doctor_border = "red"
        else:
            doctor_status_str = f"[bold green]{stats['passed_checks']} passed[/]\n[dim]Healthy system[/]"
            doctor_border = "green"
            
    doctor_panel = Panel(
        doctor_status_str,
        title="System Diagnostics",
        border_style=doctor_border
    )
    
    stats_table.add_row(sessions_panel, commands_panel, doctor_panel)
    console.print(stats_table)
    
    # 2. Main content panes: Doctor Reports (Left) and Recent Commands (Right)
    doc_table = Table(title="Last Diagnostic Run", expand=True)
    doc_table.add_column("Check Name", style="cyan")
    doc_table.add_column("Status", justify="center")
    
    for check in doctor_checks:
        stat_lbl = f"[green]{CHECK}[/]" if check["status"] == "passed" else (f"[yellow]{WARN}[/]" if check["status"] == "warning" else f"[red]{CROSS}[/]")
        doc_table.add_row(check["check_name"], stat_lbl)
        
    if not doctor_checks:
        doc_table.add_row("[dim]No diagnostic data logged. Run 'ai doctor' to scan.[/]", "")
        
    cmd_table = Table(title="Recent Command Executions", expand=True)
    cmd_table.add_column("Command", style="white")
    cmd_table.add_column("Risk", justify="center")
    cmd_table.add_column("Status", justify="center")
    
    for cmd in recent_cmds:
        risk_style = "green" if cmd["risk_level"] == "READ" else ("yellow" if cmd["risk_level"] == "MODIFY" else "red")
        risk_lbl = f"[{risk_style}]{cmd['risk_level']}[/]"
        
        status_style = "green" if cmd["status"] == "executed" else ("yellow" if cmd["status"] == "executed_modified" else "red")
        status_lbl = f"[{status_style}]{cmd['status']}[/]"
        
        cmd_table.add_row(
            cmd["command"][:40] + ("..." if len(cmd["command"]) > 40 else ""),
            risk_lbl,
            status_lbl
        )
        
    if not recent_cmds:
        cmd_table.add_row("[dim]No shell executions logged yet.[/]", "", "")
        
    # Render two-column grid
    grid = Table.grid(expand=True, padding=2)
    grid.add_column(ratio=1)
    grid.add_column(ratio=2)
    grid.add_row(doc_table, cmd_table)
    
    console.print(grid)
    console.print()
