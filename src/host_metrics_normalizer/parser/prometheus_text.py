from __future__ import annotations

from prometheus_client.parser import text_string_to_metric_families


def parse_metric_families(raw_text: str):
    return tuple(text_string_to_metric_families(raw_text))


def family_map(raw_text: str) -> dict[str, object]:
    families = parse_metric_families(raw_text)
    return {family.name: family for family in families}
