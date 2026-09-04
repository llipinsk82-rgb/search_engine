from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from backend.index import count_search_items, search_items, upsert_items
from backend.models import SearchItem

def item(i,status):
    return SearchItem(id=i,provider="sample",title="Step sample",url=f"https://example.com/{i}",age_check_status=status,tags=[])

class AgeCheckFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"db.sqlite"
        upsert_items([item("r","required"),item("n","not_required"),item("u","unknown")],self.db)
    def tearDown(self): self.tmp.cleanup()

    def test_required_filter(self):
        rows=search_items("Step",age_check="required",path=self.db)
        self.assertEqual([r.id for r in rows],["r"])
        self.assertEqual(count_search_items("Step",age_check="required",path=self.db),1)

    def test_not_required_filter(self):
        self.assertEqual([r.id for r in search_items("Step",age_check="not_required",path=self.db)],["n"])

    def test_unknown_filter(self):
        self.assertEqual([r.id for r in search_items("Step",age_check="unknown",path=self.db)],["u"])

    def test_no_filter_returns_all(self):
        self.assertEqual({r.id for r in search_items("Step",path=self.db)},{"r","n","u"})

if __name__ == "__main__":
    unittest.main()
