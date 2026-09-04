from __future__ import annotations
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]; DEPLOY=ROOT/'deploy'
class DeployUnitTests(unittest.TestCase):
    def test_sync_and_backfill_share_maintenance_lock(self):
        for name in ('search-engine-sync.service','search-engine-backfill.service'):
            t=(DEPLOY/name).read_text(); self.assertIn('/run/search_engine/maintenance.lock',t); self.assertIn('RuntimeDirectory=search_engine',t); self.assertIn('/opt/search_engine/deploy/run-maintenance.sh',t); self.assertNotIn('ExecStart=/usr/bin/flock',t)
    def test_backfill_service_is_bounded_and_low_priority(self):
        t=(DEPLOY/'search-engine-backfill.service').read_text()
        for x in ('backfill-all','--max-seconds','TimeoutStartSec=6min','Nice=10','CPUWeight=20','IOWeight=20'): self.assertIn(x,t)
    def test_backfill_env_defaults_match_service_defaults(self):
        unit=(DEPLOY/'search-engine-backfill.service').read_text(); env=(DEPLOY/'search-engine.env.example').read_text()
        for name in ('SEARCH_BACKFILL_BATCH_SIZE','SEARCH_BACKFILL_BATCHES_PER_PROVIDER','SEARCH_BACKFILL_MAX_SECONDS'):
            a=re.search(rf'^Environment={name}=([^\n]+)$',unit,re.M); b=re.search(rf'^{name}=([^\n]+)$',env,re.M); self.assertIsNotNone(a); self.assertIsNotNone(b); self.assertEqual(a.group(1),b.group(1))
    def test_backfill_defaults_are_final(self):
        env=(DEPLOY/'search-engine.env.example').read_text()
        for x in ('SEARCH_BACKFILL_BATCH_SIZE=500','SEARCH_BACKFILL_BATCHES_PER_PROVIDER=1','SEARCH_BACKFILL_MAX_SECONDS=180'): self.assertIn(x,env)
if __name__=='__main__': unittest.main()
