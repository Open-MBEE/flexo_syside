from __future__ import annotations

from typing import Any


ELEMENT_TYPE_KEY = "@type"


def replace_none_with_empty(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: replace_none_with_empty(value) if value is not None else ""
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [replace_none_with_empty(value) for value in obj]
    return obj


def remove_uri_fields(obj: Any) -> Any:
    """Recursively remove all @uri fields from a nested JSON-like structure."""
    if isinstance(obj, dict):
        return {
            key: remove_uri_fields(value)
            for key, value in obj.items()
            if key != "@uri"
        }
    if isinstance(obj, list):
        return [remove_uri_fields(item) for item in obj]
    return obj


def wrap_elements_as_payload(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Transform elements into the target format:
    - Wrap each element in 'payload'
    - Add 'identity' with '@id'
    - Replace None values with empty strings
    """
    transformed: list[dict[str, Any]] = []

    for element in data:
        clean_element = replace_none_with_empty(element)
        identity = {"@id": clean_element.get("@id")} if "@id" in clean_element else {}
        transformed.append({
            "payload": clean_element,
            "identity": identity,
        })

    return transformed


def apply_root_namespace_name(
    full_json_elements: list[dict[str, Any]],
    root_name: str | None,
) -> list[dict[str, Any]]:
    if root_name is None:
        return full_json_elements

    for element in full_json_elements:
        if (
            element.get(ELEMENT_TYPE_KEY) == "Namespace"
            and "owningRelationship" not in element
        ):
            element["qualifiedName"] = root_name
            break
    return full_json_elements
