from __future__ import annotations
import json, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DeployArtifactTests(unittest.TestCase):
    def test_deploy_scripts_have_valid_bash_syntax(self):
        for name in ('acceptance.sh','post-deploy-warmup.sh','run-maintenance.sh','deploy-production.sh'): subprocess.run(['bash','-n',str(ROOT/'deploy'/name)],check=True)
    def test_production_deploy_has_backup_and_rollback_guards(self):
        t=(ROOT/'deploy'/'deploy-production.sh').read_text()
        for x in ('SEARCH_DEPLOY_ROLLBACK=START','SEARCH_DEPLOY=PASS','maintenance.lock','nginx -t','SEARCH_EXPECT_BUILD','requirements.txt changed','NGINX_SITE'): self.assertIn(x,t)
        self.assertIn("required = {'xvideos', 'xnxx', 'sunporno', 'xgroovy', 'txxx'}", t)
    def test_maintenance_lock_precedes_active_configuration_writes(self):
        t=(ROOT/'deploy'/'deploy-production.sh').read_text(); lock=t.index('flock -w 30 9')
        for x in ('install -m 0644 "$SOURCE/deploy/search-engine-providers.example.json"','install -m 0600 "$SOURCE/deploy/search-engine.env.example"','install -m 0644 "$SOURCE/deploy/$unit"','SEARCH_PROVIDER_CONFIG_FILE=/etc/search_engine-providers.json'): self.assertLess(lock,t.index(x))
    def test_shipped_provider_catalog_is_four_source_incremental(self):
        rows=json.loads((ROOT/'deploy'/'search-engine-providers.example.json').read_text()); self.assertEqual({r['name'] for r in rows},{'xvideos','xnxx','sunporno','xgroovy','txxx'}); self.assertTrue(all(r['sync_mode']=='incremental' for r in rows))
    def test_service_and_acceptance_use_production_port(self):
        self.assertIn('--port 8775',(ROOT/'deploy'/'search-engine.service').read_text()); self.assertIn('127.0.0.1:8775',(ROOT/'deploy'/'acceptance.sh').read_text())
    def test_post_deploy_warmup_is_bounded_and_non_destructive(self):
        t=(ROOT/'deploy'/'post-deploy-warmup.sh').read_text(); self.assertIn('search-engine-sync.service',t); self.assertIn('search-engine-backfill.service',t); self.assertIn('items_before=',t); self.assertIn('grown_providers=',t); self.assertNotIn('rm -rf /opt/search_engine',t)
        self.assertLess(t.index('systemctl start "$SYNC_SERVICE"'), t.index('systemctl start "$SERVICE"'))
    def test_warmup_failure_does_not_trigger_release_rollback(self):
        t=(ROOT/'deploy'/'deploy-production.sh').read_text(); a=t.index('post-deploy-warmup.sh'); b=t.rindex('SEARCH_DEPLOY=PASS'); tail=t[a:b]; self.assertNotIn('rollback "warmup',tail); self.assertIn('SEARCH_DEPLOY_WARMUP=DEGRADED',tail)
    def test_nginx_csp_is_rollback_managed(self):
        t=(ROOT/'deploy'/'deploy-production.sh').read_text(); self.assertIn('backup_config "$NGINX_SITE" nginx-search-engine',t); self.assertIn('restore_config "$NGINX_SITE" nginx-search-engine',t); self.assertIn("media-src 'self' https:",t)
if __name__=='__main__': unittest.main()
