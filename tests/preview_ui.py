import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from ai_cli.ui import printer
from ai_cli.ui.printer import SPINNER_STYLES

console = Console()

def test_spinners():
    console.print("\n[bold cyan]=== PREVIEWING ALL SPINNER ANIMATIONS ===[/]")
    for spinner_name, spinner_color, text_style in SPINNER_STYLES:
        phrase = f"Testing spinner: {spinner_name} ({spinner_color}/{text_style})"
        with console.status(
            f"  [{text_style}]{phrase}[/]...",
            spinner=spinner_name,
            spinner_style=spinner_color,
        ):
            time.sleep(0.2)

def test_panels():
    console.print("\n[bold cyan]=== PREVIEWING ALL UI PANELS ===[/]")
    
    printer.print_header()
    
    printer.print_separator("Info Panel")
    printer.print_info("This is an information message.")
    
    printer.print_separator("Success Panel")
    printer.print_success("Operation completed successfully!")
    
    printer.print_separator("Warning Panel")
    printer.print_warning("This is a warning about a potential issue.")
    
    printer.print_separator("Error Panel")
    printer.print_error("Failed to fetch repository information (404 Not Found).")
    
    printer.print_separator("Danger Banner")
    printer.print_danger("This operation is destructive and will erase your configuration.")
    
    printer.print_separator("Highlighted Command")
    printer.print_command("winget install --id Anthropic.ClaudeCode", language="powershell", title="Install Claude Code")
    
    printer.print_separator("Command Execution Output")
    printer.print_command_result("Successfully uninstalled 1 package.\nDone.", success=True)
    printer.print_command_result("Error: package not found.", success=False)
    
    printer.print_separator("End of Preview")

if __name__ == "__main__":
    console.print("[bold yellow]AI CLI UI Component Inspector[/]")
    test_spinners()
    test_panels()
