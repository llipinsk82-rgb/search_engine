from __future__ import annotations

from backend.content_class import ContentClass, classify_content
from backend.models import SearchItem


def classify_live_item(item: SearchItem) -> SearchItem:
    if item.content_class != "unknown":
        return item
    content_class = classify_content(provider=item.provider, tags=item.tags, studio=item.studio)
    if content_class == item.content_class:
        return item
    return item.model_copy(update={"content_class": content_class})


def filter_live_items(
    items: list[SearchItem], content_class: ContentClass | None
) -> list[SearchItem]:
    normalized = [classify_live_item(item) for item in items]
    if content_class is None:
        return normalized
    return [item for item in normalized if item.content_class == content_class]
