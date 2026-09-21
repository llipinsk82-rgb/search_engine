from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

ThumbnailMode = Literal["direct", "proxy", "refresh"]
PreviewMode = Literal["direct", "proxy", "disabled"]
MediaKind = Literal["thumbnail", "preview"]


@dataclass(frozen=True)
class ProviderMediaPolicy:
    name: str
    thumbnail_mode: ThumbnailMode = "direct"
    preview_mode: PreviewMode = "disabled"
    thumbnail_host_suffixes: tuple[str, ...] = ()
    preview_host_suffixes: tuple[str, ...] = ()
    thumbnail_referer: str | None = None
    preview_referer: str | None = None


_PREVIEW_SUFFIXES: dict[str, tuple[str, ...]] = {
    "beeg": ("vp.externulls.com",),
    "youjizz": (".youjizz.com",),
    "drtuber": (".drtst.com",),
    "pornhat": ("pornhat.one",),
    "porndr": ("porndr.com",),
    "bigfuck": (".bigfuck.tv",),
    "hqporn": (".hqporn.xxx",),
    "anyporn": ("anyporn.com",),
    "tnaflix": (".tnaflix.com",),
    "spankbang": (".sb-cd.com",),
    "thumbzilla": (".ypncdn.com",),
    "xhamster": (".xhcdn.com",),
    "pornhub": (".phncdn.com",),
    "tube8": (".t8cdn.com",),
    "xvideos": (".xvideos-cdn.com",),
    "xnxx": (".xnxx-cdn.com",),
    "mypornhere": ("mypornhere.com",),
    "pussyspace": (".xvideos-cdn.com",),
    "porndig": ("image-cdn.porndig.com",),
    "sexvid": ("pr1.sexvid.xxx",),
    "pornid": ("pr1.pornid.xxx",),
    "zbporn": ("pr1.zbporn.com",),
}


def _build_policies() -> dict[str, ProviderMediaPolicy]:
    policies = {
        name: ProviderMediaPolicy(
            name=name,
            preview_mode="direct",
            preview_host_suffixes=suffixes,
        )
        for name, suffixes in _PREVIEW_SUFFIXES.items()
    }
    policies["thumbzilla"] = ProviderMediaPolicy(
        name="thumbzilla",
        thumbnail_mode="proxy",
        preview_mode="proxy",
        thumbnail_host_suffixes=(".ypncdn.com",),
        preview_host_suffixes=_PREVIEW_SUFFIXES["thumbzilla"],
        thumbnail_referer="https://www.thumbzilla.com/",
        preview_referer="https://www.thumbzilla.com/",
    )
    policies["tube8"] = ProviderMediaPolicy(
        name="tube8",
        thumbnail_mode="refresh",
        preview_mode="direct",
        preview_host_suffixes=_PREVIEW_SUFFIXES["tube8"],
    )
    for name in ("pornhat", "porndr", "anyporn"):
        policies[name] = ProviderMediaPolicy(
            name=name,
            preview_mode="disabled",
            preview_host_suffixes=_PREVIEW_SUFFIXES[name],
        )
    return policies


_PROVIDER_MEDIA_POLICIES = _build_policies()


def provider_media_policy(name: str) -> ProviderMediaPolicy:
    key = name.strip().lower()
    return _PROVIDER_MEDIA_POLICIES.get(key, ProviderMediaPolicy(name=key or name))


def _host_matches(host: str, suffix: str) -> bool:
    normalized = suffix.strip().lower().lstrip(".")
    return bool(normalized) and (host == normalized or host.endswith("." + normalized))


def media_url_allowed(provider: str, kind: str, url: str) -> bool:
    if kind not in {"thumbnail", "preview"}:
        return False
    policy = provider_media_policy(provider)
    if kind == "preview" and policy.preview_mode == "disabled":
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        return False
    suffixes = (
        policy.thumbnail_host_suffixes
        if kind == "thumbnail"
        else policy.preview_host_suffixes
    )
    if not suffixes:
        return kind == "thumbnail" and policy.thumbnail_mode in {"direct", "refresh"}
    return any(_host_matches(host, suffix) for suffix in suffixes)


def media_policy_rows(names: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name in sorted(names):
        policy = provider_media_policy(name)
        rows.append(
            {
                "name": policy.name,
                "thumbnail_mode": policy.thumbnail_mode,
                "preview_mode": policy.preview_mode,
                "thumbnail_host_suffixes": list(policy.thumbnail_host_suffixes),
                "preview_host_suffixes": list(policy.preview_host_suffixes),
            }
        )
    return rows
