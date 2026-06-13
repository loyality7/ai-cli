import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_cli.core import db

def test_db():
    print("Initializing Database...")
    db.init_db()
    
    print(f"Database Path: {db.DB_PATH}")
    print(f"File Exists: {db.DB_PATH.exists()}")
    
    print("\nInserting mock session action...")
    db.log_session_action("verify-session-999", "verification_test", {"status": "ok"})
    
    print("Inserting mock command execution...")
    db.log_executed_command(
        session_id="verify-session-999",
        command="echo hello",
        risk_level="READ",
        status="executed",
        output="hello"
    )
    
    print("Inserting mock doctor report...")
    db.log_doctor_report(
        session_id="verify-session-999",
        check_name="Verify SQLite Integration",
        status="passed",
        message="SQLite is functioning correctly"
    )
    
    print("\nRetrieving database stats:")
    stats = db.get_db_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
        
    print("\nRetrieving recent session actions:")
    actions = db.get_recent_actions(limit=2)
    for a in actions:
        print(f"  {a['timestamp']} - Session: {a['session_id']} - Action: {a['action']} - Details: {a['details']}")

    print("\nRetrieving recent commands:")
    cmds = db.get_recent_commands(limit=2)
    for c in cmds:
        print(f"  {c['timestamp']} - Command: '{c['command']}' - Risk: {c['risk_level']} - Status: {c['status']}")
        
    print("\nRetrieving latest doctor report:")
    reports = db.get_latest_doctor_reports()
    for r in reports:
        print(f"  {r['timestamp']} - Check: '{r['check_name']}' - Status: {r['status']} - Msg: {r['message']}")

if __name__ == "__main__":
    test_db()
