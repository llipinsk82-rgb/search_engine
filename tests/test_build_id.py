from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import backend.settings as settings

class BuildIdTests(unittest.TestCase):
    def test_explicit_env_wins(self):
        with patch.dict(os.environ, {"SEARCH_BUILD_ID": "abc123"}, clear=False):
            self.assertEqual(settings.get_build_id(), "abc123")

    def test_marker_is_used_without_env(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / ".build-id"
            marker.write_text("marker123\n")
            with patch.dict(os.environ, {}, clear=True), patch.object(settings, "ROOT", Path(d)):
                self.assertEqual(settings.get_build_id(), "marker123")

    def test_missing_marker_returns_dev(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {}, clear=True), patch.object(settings, "ROOT", Path(d)):
                self.assertEqual(settings.get_build_id(), "dev")

if __name__ == "__main__":
    unittest.main()
