from __future__ import annotations

import json
from pathlib import Path

from flexo_syside_lib.core_multi_namespace import convert_json_to_sysml_textual_multi_namespace


TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
MULTI_NAMESPACE_DIR = FIXTURES_DIR / "multi_namespace"


def fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


def normalize_roundtrip_sysml_text(sysml_text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in sysml_text.strip().splitlines())
    return normalized.replace("Actions::Action::start", "start")


def canonical_namespace_models(json_text: str) -> dict[str, str]:
    namespace_models, _warnings = convert_json_to_sysml_textual_multi_namespace(json_text)
    return {
        namespace_name: normalize_roundtrip_sysml_text(sysml_text)
        for namespace_name, sysml_text in namespace_models
    }


def canonicalize_json_value(value):
    if isinstance(value, dict):
        return {
            key: canonicalize_json_value(val)
            for key, val in sorted(value.items())
        }
    if isinstance(value, list):
        canonical_items = [canonicalize_json_value(item) for item in value]
        if all(isinstance(item, dict) and "@id" in item for item in canonical_items):
            return sorted(canonical_items, key=lambda item: item["@id"])
        return canonical_items
    return value


def canonicalize_json_elements(json_text: str) -> list[dict]:
    elements = json.loads(json_text)
    canonical_elements = [canonicalize_json_value(element) for element in elements]
    return sorted(canonical_elements, key=lambda element: element.get("@id", ""))
