from __future__ import annotations
import unittest
from pydantic import ValidationError
from backend.models import LiveRefreshRequest, SearchItem, SearchRequest

class AgeCheckSemanticsTests(unittest.TestCase):
    def test_search_item_defaults_unknown(self):
        item=SearchItem(id="1",provider="x",title="X",url="https://example.com/x")
        self.assertEqual(item.age_check_status,"unknown")

    def test_search_request_accepts_three_statuses(self):
        for status in ("required","not_required","unknown"):
            self.assertEqual(SearchRequest(age_check=status).age_check,status)

    def test_live_request_accepts_three_statuses(self):
        for status in ("required","not_required","unknown"):
            self.assertEqual(LiveRefreshRequest(q="x",age_check=status).age_check,status)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            SearchRequest(age_check="maybe")

if __name__ == "__main__":
    unittest.main()
