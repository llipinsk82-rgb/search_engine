from __future__ import annotations
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEPLOY=ROOT/'deploy'
def _service_port():
    m=re.search(r'--port\s+(\d+)', (DEPLOY/'search-engine.service').read_text()); assert m; return int(m.group(1))
def _nginx_port():
    m=re.search(r'proxy_pass\s+http://127\.0\.0\.1:(\d+);', (DEPLOY/'nginx-search-engine.conf').read_text()); assert m; return int(m.group(1))
def test_api_port_is_consistent_across_deploy_assets(): assert _service_port()==_nginx_port()==8775
def test_maintenance_units_target_same_install_and_database():
    for name in ('search-engine.service','search-engine-sync.service','search-engine-backfill.service'):
        t=(DEPLOY/name).read_text(); assert 'WorkingDirectory=/opt/search_engine' in t; assert 'Environment=SEARCH_DB_PATH=/var/lib/search_engine/search.db' in t
def test_csp_allows_external_motion_preview():
    assert "media-src 'self' https:" in (DEPLOY/'nginx-search-engine.conf').read_text()
