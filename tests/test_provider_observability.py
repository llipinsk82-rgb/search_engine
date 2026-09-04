from __future__ import annotations
import unittest
from unittest.mock import patch
import backend.app as app_module

class Named:
    def __init__(self,name): self.name=name

class ProviderObservabilityTests(unittest.TestCase):
    def test_roles_are_reported_separately_and_disabled_not_available(self):
        with patch.object(app_module,"indexed_providers",return_value=["tube8","xvideos"]),              patch.object(app_module,"PROVIDERS",[Named("tube8"),Named("xnxx")]),              patch.object(app_module,"LIVE_ADAPTERS",[Named("beeg"),Named("xnxx")]):
            out=app_module._provider_observability()
        self.assertEqual(out["indexed_providers"],["tube8","xvideos"])
        self.assertEqual(out["configured_index_providers"],["tube8","xnxx"])
        self.assertEqual(out["live_providers"],["beeg","xnxx"])
        self.assertNotIn("tube8",out["available_providers"])
        self.assertIn("beeg",out["available_providers"])

if __name__ == "__main__":
    unittest.main()
