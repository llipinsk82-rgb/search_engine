from __future__ import annotations
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNNER=Path(__file__).resolve().parents[1]/"deploy"/"run-maintenance.sh"

class MaintenanceRunnerTests(unittest.TestCase):
    def test_usage_error(self):
        p=subprocess.run([str(RUNNER)],capture_output=True,text=True)
        self.assertEqual(p.returncode,64)

    def test_executes_command_when_lock_free(self):
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/"lock"
            p=subprocess.run([str(RUNNER),str(lock),"0","/bin/sh","-c","printf PASS"],capture_output=True,text=True)
            self.assertEqual(p.returncode,0)
            self.assertIn("SEARCH_MAINTENANCE=LOCKED",p.stdout)
            self.assertTrue(p.stdout.rstrip().endswith("PASS"))

    def test_lock_contention_is_clean_skip(self):
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/"lock"
            holder=subprocess.Popen(["flock","-x",str(lock),"-c","sleep 1"])
            try:
                p=subprocess.run([str(RUNNER),str(lock),"0","/bin/false"],capture_output=True,text=True)
                self.assertEqual(p.returncode,0)
                self.assertIn("SEARCH_MAINTENANCE=SKIPPED",p.stdout)
            finally:
                holder.wait()

if __name__ == "__main__":
    unittest.main()
