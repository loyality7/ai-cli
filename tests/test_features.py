import os
import sys
import unittest
import tempfile
from pathlib import Path

# Set up project root in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_cli.core import db
from ai_cli.core.doctor import run_doctor
from ai_cli.core.dashboard import run_dashboard

class TestAiCliFeatures(unittest.TestCase):
    def setUp(self):
        # Redirect config dir to a temp directory for clean testing
        self.temp_dir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.temp_dir.name) / "ai_cli_test.db"
        db.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_logging(self):
        session_id = "test-session-123"
        db.log_session_action(session_id, "test_action", {"meta": "data"})
        
        recent_actions = db.get_recent_actions(limit=5)
        self.assertTrue(len(recent_actions) >= 1)
        self.assertEqual(recent_actions[0]["session_id"], session_id)
        self.assertEqual(recent_actions[0]["action"], "test_action")

        db.log_executed_command(
            session_id=session_id,
            command="git status",
            risk_level="READ",
            status="executed",
            output="On branch main"
        )
        
        recent_cmds = db.get_recent_commands(limit=5)
        self.assertTrue(len(recent_cmds) >= 1)
        self.assertEqual(recent_cmds[0]["command"], "git status")
        self.assertEqual(recent_cmds[0]["risk_level"], "READ")

        db.log_doctor_report(
            session_id=session_id,
            check_name="Bandit Security Scan",
            status="passed",
            message="No security issues identified"
        )
        
        reports = db.get_latest_doctor_reports()
        self.assertTrue(len(reports) >= 1)
        self.assertEqual(reports[0]["check_name"], "Bandit Security Scan")

        stats = db.get_db_stats()
        self.assertEqual(stats["total_actions"], 1)
        self.assertEqual(stats["total_commands"], 1)

    def test_doctor_scan(self):
        success = run_doctor()
        self.assertIn(success, [True, False])

        reports = db.get_latest_doctor_reports()
        self.assertTrue(len(reports) > 0)
        check_names = [r["check_name"] for r in reports]
        self.assertIn("API Key Configuration", check_names)
        self.assertIn("Workspace Manifests", check_names)
        self.assertIn("Bandit Security Scan", check_names)

        # Test skip_llm flag
        success_skipped = run_doctor(skip_llm=True)
        self.assertTrue(success_skipped)

    def test_dashboard_rendering(self):
        session_id = "test-dashboard-session"
        db.log_session_action(session_id, "start_repl")
        db.log_executed_command(session_id, "pip list", "READ", "executed", "mock_output")
        db.log_doctor_report(session_id, "Dummy Check", "passed", "Details")
        
        try:
            run_dashboard()
            run_ok = True
        except Exception as e:
            print(f"Dashboard failed with error: {e}", file=sys.stderr)
            run_ok = False
            
        self.assertTrue(run_ok)

if __name__ == "__main__":
    unittest.main()
