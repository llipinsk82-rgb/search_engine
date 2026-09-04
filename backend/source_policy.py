from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Literal
from urllib.parse import urlparse

from backend.models import SearchItem

AgeCheckStatus = Literal["required", "not_required", "unknown"]
_ALLOWED_AGE_CHECK = {"required", "not_required", "unknown"}
_DEFAULT_REGION = "UK"


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    name: str
    display_name: str
    allowed_video_hosts: frozenset[str]
    trusted: bool = True
    default_age_check: AgeCheckStatus = "unknown"


TRUSTED_PROVIDER_POLICIES: dict[str, ProviderPolicy] = {
    "xvideos": ProviderPolicy("xvideos", "XVideos", frozenset({"xvideos.com", "www.xvideos.com"}), default_age_check="required"),
    "xnxx": ProviderPolicy("xnxx", "XNXX", frozenset({"xnxx.com", "www.xnxx.com"}), default_age_check="required"),
    "xhamster": ProviderPolicy("xhamster", "XHamster", frozenset({"xhamster.com", "www.xhamster.com"})),
    "thumbzilla": ProviderPolicy("thumbzilla", "Thumbzilla", frozenset({"thumbzilla.com", "www.thumbzilla.com"})),
    "hqporner": ProviderPolicy("hqporner", "HQPorner", frozenset({"hqporner.com", "www.hqporner.com"})),
    "pornone": ProviderPolicy("pornone", "PornOne", frozenset({"pornone.com", "www.pornone.com"})),
    "youjizz": ProviderPolicy("youjizz", "YouJizz", frozenset({"youjizz.com", "www.youjizz.com"})),
    "tube8": ProviderPolicy("tube8", "Tube8", frozenset({"tube8.com", "www.tube8.com"}), default_age_check="required"),
    "eporner": ProviderPolicy("eporner", "Eporner", frozenset({"eporner.com", "www.eporner.com"}), default_age_check="required"),
    "pornhub": ProviderPolicy("pornhub", "Pornhub", frozenset({"pornhub.com", "www.pornhub.com"}), default_age_check="required"),
    "spankbang": ProviderPolicy("spankbang", "SpankBang", frozenset({"spankbang.com", "www.spankbang.com"})),
    "beeg": ProviderPolicy("beeg", "Beeg", frozenset({"beeg.com", "www.beeg.com"}), default_age_check="not_required"),
    "tnaflix": ProviderPolicy("tnaflix", "TNAFlix", frozenset({"tnaflix.com", "www.tnaflix.com"})),
    "sunporno": ProviderPolicy("sunporno", "SunPorno", frozenset({"sunporno.com", "www.sunporno.com"})),
    "xgroovy": ProviderPolicy("xgroovy", "XGroovy", frozenset({"xgroovy.com", "www.xgroovy.com"})),
    "txxx": ProviderPolicy("txxx", "TXXX", frozenset({"txxx.com", "www.txxx.com"})),
}


def trusted_provider_names() -> set[str]:
    return {name for name, policy in TRUSTED_PROVIDER_POLICIES.items() if policy.trusted}


# Recovery baseline matches production d054dd7. These are search-state flags only.
# Provider suitability will be re-audited after recovery under the owner's
# clarified "aggressive redirect/tab storm only" policy.
_SEARCH_DISABLED_PROVIDERS: set[str] = set()


def is_searchable_provider(name: str) -> bool:
    return name in TRUSTED_PROVIDER_POLICIES and name not in _SEARCH_DISABLED_PROVIDERS


def searchable_provider_names() -> set[str]:
    return {name for name in trusted_provider_names() if is_searchable_provider(name)}


def _configured_age_checks() -> dict[str, AgeCheckStatus]:
    raw = os.environ.get("SEARCH_AGE_CHECK_POLICY_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, AgeCheckStatus] = {}
    for name, value in payload.items():
        status = str(value).strip().lower()
        if name in TRUSTED_PROVIDER_POLICIES and status in _ALLOWED_AGE_CHECK:
            result[str(name)] = status  # type: ignore[assignment]
    return result


def age_check_for_provider(provider: str) -> AgeCheckStatus:
    policy = TRUSTED_PROVIDER_POLICIES.get(provider)
    if policy is None:
        return "unknown"
    return _configured_age_checks().get(provider) or policy.default_age_check


def normalize_trusted_live_item(item: SearchItem) -> SearchItem | None:
    policy = TRUSTED_PROVIDER_POLICIES.get(item.provider)
    if policy is None or not policy.trusted:
        return None
    parsed = urlparse(str(item.url))
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in policy.allowed_video_hosts:
        return None
    status = item.age_check_status
    if status == "unknown":
        status = age_check_for_provider(item.provider)
    return item if status == item.age_check_status else item.model_copy(update={"age_check_status": status})


def deployment_region() -> str:
    return os.environ.get("SEARCH_REGION", _DEFAULT_REGION).strip().upper() or _DEFAULT_REGION


def legal_age_assurance_requirement(region: str | None = None) -> str:
    selected = (region or deployment_region()).strip().upper()
    return "required" if selected in {"UK", "GB", "GBR"} else "unknown"


def provider_policy_rows(names: set[str] | None = None) -> list[dict[str, object]]:
    selected = names if names is not None else trusted_provider_names()
    rows: list[dict[str, object]] = []
    for name in sorted(selected):
        policy = TRUSTED_PROVIDER_POLICIES.get(name)
        if policy is None or not policy.trusted:
            continue
        observed = age_check_for_provider(name)
        rows.append({
            "name": policy.name,
            "display_name": policy.display_name,
            "trusted": True,
            "age_check_status": observed,
            "observed_age_check_status": observed,
            "observed_behavior_scope": "deployment observation/provider behavior",
            "region": deployment_region(),
            "legal_age_assurance_requirement": legal_age_assurance_requirement(),
            "legal_requirement_scope": "UK Online Safety Act where the service has links to the UK",
        })
    return rows
