from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit, urlunsplit

RuleKind = Literal["linked_attribute","page_json","custom","live_search_exact"]

@dataclass(frozen=True)
class PreviewRule:
    provider: str
    kind: RuleKind
    preview_host_suffixes: tuple[str,...]
    target_attribute: str|None=None
    preview_attribute: str|None=None
    json_identity_field: str|None=None
    json_preview_field: str|None=None

_RULE_FILE=Path(__file__).resolve().parents[1]/"deploy"/"search-engine-preview-rules.json"
def _load_rules():
    rows=json.loads(_RULE_FILE.read_text())
    return {r["provider"]:PreviewRule(
        provider=r["provider"], kind=r["rule_kind"],
        preview_host_suffixes=tuple(r.get("policy_host_suffixes",[])),
        target_attribute=r.get("target_attribute"), preview_attribute=r.get("preview_attribute"),
        json_identity_field=r.get("json_identity_field"), json_preview_field=r.get("json_preview_field"),
    ) for r in rows}
PREVIEW_RULES=_load_rules()

def normalize_canonical_url(value:str, base_url:str|None=None)->str|None:
    raw=str(value or "").strip()
    if not raw:return None
    p=urlsplit(urljoin(base_url or raw,raw) if base_url else raw)
    if p.scheme.lower()!="https" or not p.hostname:return None
    path=p.path or "/"
    if path!="/":path=path.rstrip("/")
    host=p.hostname.lower()+(f":{p.port}" if p.port else "")
    return urlunsplit(("https",host,path,p.query,""))

def _get(item:Any,key:str):
    v=item.get(key) if isinstance(item,dict) else getattr(item,key,None)
    return None if v is None else str(v)

def select_exact_live_preview(items:list[Any],canonical_url:str)->str|None:
    want=normalize_canonical_url(canonical_url)
    for item in items:
        if normalize_canonical_url(_get(item,"url") or "")!=want:continue
        preview=_get(item,"preview_url")
        if preview and normalize_canonical_url(preview):return preview
    return None

def _attrs(tag:str)->dict[str,str]:
    return {m.group(1).lower():m.group(3) for m in re.finditer(r"""([\w:-]+)\s*=\s*(['"])(.*?)\2""",tag,re.S)}

def _json_objs(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from _json_objs(x)
    elif isinstance(v,list):
        for x in v:yield from _json_objs(x)

def extract_preview_url(rule:PreviewRule,html_source:str,page_url:str)->str|None:
    if rule.kind=="linked_attribute":
        ta=(rule.target_attribute or "").lower(); pa=(rule.preview_attribute or "").lower()
        if not ta or not pa:return None
        for tag in re.findall(r"<[^>]+>",html_source,re.S):
            a=_attrs(tag)
            if ta not in a or pa not in a:continue
            if normalize_canonical_url(a[ta],page_url)!=normalize_canonical_url(page_url):continue
            preview=urljoin(page_url,a[pa])
            return preview if normalize_canonical_url(preview) else None
        return None
    if rule.kind=="page_json":
        ident=rule.json_identity_field; pf=rule.json_preview_field
        if not ident or not pf:return None
        for raw in re.findall(r"""<script[^>]*type=['"]application/ld\+json['"][^>]*>(.*?)</script>""",html_source,re.I|re.S):
            try:payload=json.loads(raw)
            except json.JSONDecodeError:continue
            for obj in _json_objs(payload):
                if not isinstance(obj.get(ident),str) or not isinstance(obj.get(pf),str):continue
                if normalize_canonical_url(obj[ident],page_url)!=normalize_canonical_url(page_url):continue
                preview=urljoin(page_url,obj[pf])
                return preview if normalize_canonical_url(preview) else None
        return None
    return None
