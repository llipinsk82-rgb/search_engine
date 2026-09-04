from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import backend.index as idx

class InitializeLockSafetyTests(unittest.TestCase):
    def test_initialize_is_cached_per_path(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"x.db"
            idx._initialized_paths.discard(str(db.resolve()))
            idx.initialize(db)
            with patch.object(idx, "_connect", wraps=idx._connect) as connect:
                idx.initialize(db)
                connect.assert_not_called()

    def test_read_after_initialize_does_not_reinitialize_schema(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"x.db"
            idx._initialized_paths.discard(str(db.resolve()))
            idx.initialize(db)
            with patch.object(idx, "initialize", wraps=idx.initialize) as init:
                idx.count_items(db)
                init.assert_called_once_with(db)

if __name__ == "__main__":
    unittest.main()
