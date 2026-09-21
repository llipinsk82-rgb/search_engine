from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "deploy" / "search-engine-content-evidence-rules.json"
_ALLOWED_KINDS = {"jsonld_path", "meta_name", "labelled_text"}
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass(frozen=True)
class ContentEvidenceRule:
    provider: str
    rule_kind: str
    canonical_fixture_url: str
    jsonld_type: str | None = None
    path: tuple[str | int, ...] = ()
    scope_attribute: str | None = None
    scope_value: str | None = None
    target_tag: str | None = None
    target_attribute: str | None = None
    target_value: str | None = None
    value_attribute: str | None = None
    label: str | None = None


class _EvidenceParser(HTMLParser):
    def __init__(self, rule: ContentEvidenceRule) -> None:
        super().__init__(convert_charrefs=True)
        self.rule = rule
        self._script_depth = 0
        self._script_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self.depth = 0
        self.scope_depths: list[int] = []
        self.meta_value: str | None = None
        self.text_parts: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {k.lower(): (v or "") for k, v in attrs}

    @staticmethod
    def _matches(value: str | None, expected: str | None) -> bool:
        return bool(value is not None and expected is not None and value.strip().casefold() == expected.strip().casefold())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        amap = self._attrs(attrs)

        if tag == "script" and amap.get("type", "").split(";", 1)[0].strip().casefold() == "application/ld+json":
            self._script_depth += 1
            self._script_parts = []

        if (
            self.rule.rule_kind == "meta_name"
            and self._matches(amap.get(self.rule.scope_attribute or ""), self.rule.scope_value)
        ):
            self.scope_depths.append(self.depth)

        if (
            self.rule.rule_kind == "meta_name"
            and self.scope_depths
            and tag == (self.rule.target_tag or "").casefold()
            and self._matches(amap.get(self.rule.target_attribute or ""), self.rule.target_value)
        ):
            value = amap.get(self.rule.value_attribute or "", "").strip()
            if value and self.meta_value is None:
                self.meta_value = value

        if tag not in _VOID_TAGS:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._script_depth:
            raw = "".join(self._script_parts).strip()
            if raw:
                self.jsonld_parts.append(raw)
            self._script_depth = 0
            self._script_parts = []

        if tag not in _VOID_TAGS:
            self.depth = max(0, self.depth - 1)
            while self.scope_depths and self.scope_depths[-1] >= self.depth:
                self.scope_depths.pop()

    def handle_data(self, data: str) -> None:
        if self._script_depth:
            self._script_parts.append(data)
        if self.rule.rule_kind == "labelled_text":
            value = " ".join(data.split()).strip()
            if value:
                self.text_parts.append(value)


def _rule_from_row(row: dict[str, Any]) -> ContentEvidenceRule:
    provider = str(row.get("provider", "")).strip().lower()
    kind = str(row.get("rule_kind", "")).strip()
    canonical = str(row.get("canonical_fixture_url", "")).strip()
    if not provider:
        raise ValueError("content evidence rule provider is required")
    if kind not in _ALLOWED_KINDS:
        raise ValueError(f"unsupported content evidence rule kind: {kind!r}")
    if not canonical.startswith("https://"):
        raise ValueError(f"content evidence rule {provider!r} requires https canonical_fixture_url")

    path = tuple(row.get("path", ()))
    if kind == "jsonld_path":
        if not str(row.get("jsonld_type", "")).strip() or not path:
            raise ValueError(f"jsonld_path rule {provider!r} requires jsonld_type and path")
        if not all(isinstance(part, (str, int)) and not isinstance(part, bool) for part in path):
            raise ValueError(f"jsonld_path rule {provider!r} has invalid path")
    elif kind == "meta_name":
        required = (
            "scope_attribute",
            "scope_value",
            "target_tag",
            "target_attribute",
            "target_value",
            "value_attribute",
        )
        if any(not str(row.get(name, "")).strip() for name in required):
            raise ValueError(f"meta_name rule {provider!r} is incomplete")
    elif kind == "labelled_text" and not str(row.get("label", "")).strip():
        raise ValueError(f"labelled_text rule {provider!r} requires label")

    return ContentEvidenceRule(
        provider=provider,
        rule_kind=kind,
        canonical_fixture_url=canonical,
        jsonld_type=(str(row.get("jsonld_type", "")).strip() or None),
        path=path,
        scope_attribute=(str(row.get("scope_attribute", "")).strip() or None),
        scope_value=(str(row.get("scope_value", "")).strip() or None),
        target_tag=(str(row.get("target_tag", "")).strip() or None),
        target_attribute=(str(row.get("target_attribute", "")).strip() or None),
        target_value=(str(row.get("target_value", "")).strip() or None),
        value_attribute=(str(row.get("value_attribute", "")).strip() or None),
        label=(str(row.get("label", "")).strip() or None),
    )


def _load_rules(path: Path = RULES_PATH) -> dict[str, ContentEvidenceRule]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("content evidence rules must be a JSON array")
    rules: dict[str, ContentEvidenceRule] = {}
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("content evidence rule must be a JSON object")
        rule = _rule_from_row(row)
        if rule.provider in rules:
            raise ValueError(f"duplicate content evidence rule provider: {rule.provider}")
        rules[rule.provider] = rule
    return rules


CONTENT_EVIDENCE_RULES = _load_rules()


def has_content_evidence_rule(provider: str) -> bool:
    return provider.strip().lower() in CONTENT_EVIDENCE_RULES


def _type_matches(value: object, expected: str) -> bool:
    if isinstance(value, str):
        return value.casefold() == expected.casefold()
    if isinstance(value, list):
        return any(isinstance(item, str) and item.casefold() == expected.casefold() for item in value)
    return False


def _iter_json_objects(value: object):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _iter_json_objects(graph)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_objects(item)


def _json_path(value: object, path: tuple[str | int, ...]) -> object | None:
    current = value
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list) or part < 0 or part >= len(current):
                return None
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def _clean_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _extract_jsonld(rule: ContentEvidenceRule, parser: _EvidenceParser) -> str | None:
    for raw in parser.jsonld_parts:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in _iter_json_objects(parsed):
            if not _type_matches(obj.get("@type"), rule.jsonld_type or ""):
                continue
            value = _clean_value(_json_path(obj, rule.path))
            if value:
                return value
    return None


def _extract_labelled(rule: ContentEvidenceRule, parser: _EvidenceParser) -> str | None:
    label = (rule.label or "").rstrip(":").strip().casefold()
    for index, part in enumerate(parser.text_parts[:-1]):
        if part.rstrip(":").strip().casefold() == label:
            return _clean_value(parser.text_parts[index + 1])
    return None


def extract_studio_evidence(provider: str, html: str, page_url: str) -> str | None:
    rule = CONTENT_EVIDENCE_RULES.get(provider.strip().lower())
    if rule is None or not isinstance(html, str):
        return None
    parsed_url = urlparse(page_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        return None
    try:
        parser = _EvidenceParser(rule)
        parser.feed(html)
        parser.close()
        if rule.rule_kind == "jsonld_path":
            return _extract_jsonld(rule, parser)
        if rule.rule_kind == "meta_name":
            return _clean_value(parser.meta_value)
        if rule.rule_kind == "labelled_text":
            return _extract_labelled(rule, parser)
    except Exception:
        return None
    return None
