from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from backend.models import SearchItem
from backend.source_policy import (
    TRUSTED_PROVIDER_POLICIES, age_check_for_provider, deployment_region,
    is_searchable_provider, legal_age_assurance_requirement,
    normalize_trusted_live_item, provider_policy_rows,
    searchable_provider_names, trusted_provider_names,
)

class SourcePolicyTests(unittest.TestCase):
    def test_expected_trusted_catalog(self):
        expected={"xvideos","xnxx","xhamster","thumbzilla","hqporner","pornone","youjizz","tube8","eporner","pornhub","spankbang","beeg","tnaflix"}
        self.assertEqual(trusted_provider_names(), expected)

    def test_d054_disabled_set_is_not_searchable(self):
        for name in ("tube8","thumbzilla","xhamster","spankbang"):
            self.assertFalse(is_searchable_provider(name))
        for name in ("beeg","xnxx","youjizz","pornone","hqporner","eporner","tnaflix","xvideos","pornhub"):
            self.assertTrue(is_searchable_provider(name))

    def test_searchable_names_exclude_disabled(self):
        names=searchable_provider_names()
        self.assertNotIn("tube8",names)
        self.assertNotIn("xhamster",names)
        self.assertIn("beeg",names)

    def test_default_age_statuses(self):
        self.assertEqual(age_check_for_provider("beeg"),"not_required")
        self.assertEqual(age_check_for_provider("xvideos"),"required")
        self.assertEqual(age_check_for_provider("eporner"),"required")
        self.assertEqual(age_check_for_provider("tnaflix"),"unknown")

    def test_env_override_is_supported(self):
        with patch.dict(os.environ, {"SEARCH_AGE_CHECK_POLICY_JSON": '{"tnaflix":"required"}'}):
            self.assertEqual(age_check_for_provider("tnaflix"),"required")

    def test_invalid_override_is_ignored(self):
        with patch.dict(os.environ, {"SEARCH_AGE_CHECK_POLICY_JSON": '{"tnaflix":"bogus"}'}):
            self.assertEqual(age_check_for_provider("tnaflix"),"unknown")

    def test_normalizer_rejects_untrusted_host(self):
        item=SearchItem(id="1",provider="beeg",title="X",url="https://evil.example/x",tags=[])
        self.assertIsNone(normalize_trusted_live_item(item))

    def test_normalizer_applies_provider_age_default(self):
        item=SearchItem(id="1",provider="beeg",title="X",url="https://beeg.com/-01",tags=[])
        out=normalize_trusted_live_item(item)
        self.assertIsNotNone(out)
        self.assertEqual(out.age_check_status,"not_required")

    def test_region_legal_requirement_is_separate(self):
        with patch.dict(os.environ, {"SEARCH_REGION":"UK"}):
            self.assertEqual(deployment_region(),"UK")
            self.assertEqual(legal_age_assurance_requirement(),"required")
        self.assertEqual(legal_age_assurance_requirement("DE"),"unknown")

    def test_policy_rows_expose_observed_and_legal_fields(self):
        row=provider_policy_rows({"beeg"})[0]
        self.assertEqual(row["observed_age_check_status"],"not_required")
        self.assertIn("legal_age_assurance_requirement",row)

if __name__ == "__main__":
    unittest.main()
