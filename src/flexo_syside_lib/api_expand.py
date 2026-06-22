"""
Merge SysIDE-expanded elements into Flexo sysmlv2-service API responses.

Flexo GET /elements returns a backend-specific JSON projection. Re-serializing
the whole model through SysIDE changes field names and breaks TS/sysmlviz.
This module preserves every backend element verbatim and appends only net-new
implied elements, projected to the same key shape Flexo uses per @type.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# SysIDE JSON keys that do not appear on Flexo GET /elements responses.
_SYSIDE_ONLY_KEYS = frozenset(
    {
        "isImpliedIncluded",
        "isLibraryElement",
        "owningFeature",
        "owningNamespace",
        "owningType",
        "qualifiedName",
        "relatedElement",
        "source",
        "target",
        "owningFeatureOfType",
        "member",
        "membership",
        "ownedElement",
        "ownedMember",
        "ownedMemberElement",
        "ownedMemberFeature",
        "ownedMemberElementId",
        "referencingFeature",
    }
)

# Default Flexo-like keys for implied types that may not exist in the backend yet.
_DEFAULT_TYPE_KEYS: dict[str, frozenset[str]] = {
    "Subsetting": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "specific",
            "subsettedFeature",
            "subsettingFeature",
        }
    ),
    "Redefinition": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "redefinedFeature",
            "redefiningFeature",
            "specific",
            "subsettedFeature",
            "subsettingFeature",
        }
    ),
    "FeatureTyping": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "specific",
            "type",
            "typedFeature",
        }
    ),
    "ReferenceSubsetting": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "referencedFeature",
            "specific",
            "subsettedFeature",
            "subsettingFeature",
        }
    ),
    "FeatureMembership": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "memberElement",
            "ownedRelatedElement",
            "owningRelatedElement",
        }
    ),
    "OwningMembership": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "memberElement",
            "ownedRelatedElement",
            "owningRelatedElement",
        }
    ),
    "TypeFeaturing": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "featureOfType",
            "featuringType",
            "owningFeatureOfType",
            "owningRelatedElement",
        }
    ),
    "Specialization": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "specific",
        }
    ),
    "Subclassification": frozenset(
        {
            "@id",
            "@type",
            "elementId",
            "general",
            "owningRelatedElement",
            "specific",
            "subclassifier",
        }
    ),
}


def _build_type_key_templates(backend_elements: list[dict[str, Any]]) -> dict[str, set[str]]:
    templates: dict[str, set[str]] = defaultdict(set)
    for element in backend_elements:
        element_type = element.get("@type")
        if element_type:
            templates[element_type].update(element.keys())
    return templates


def syside_element_to_flexo_api(
    element: dict[str, Any],
    type_templates: dict[str, set[str]],
) -> dict[str, Any]:
    """Project one SysIDE element onto Flexo GET /elements field names."""
    element_type = element.get("@type")
    if not element_type:
        return dict(element)

    allowed = type_templates.get(element_type) or _DEFAULT_TYPE_KEYS.get(element_type)
    if allowed:
        projected = {key: element[key] for key in allowed if key in element}
        if "@id" in element:
            projected.setdefault("@id", element["@id"])
        if "@type" in element:
            projected.setdefault("@type", element["@type"])
        return projected

    return {
        key: value
        for key, value in element.items()
        if key in ("@id", "@type") or key not in _SYSIDE_ONLY_KEYS
    }


def merge_expanded_elements_for_api(
    backend_elements: list[dict[str, Any]],
    expanded_elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Preserve backend Flexo JSON exactly and append only net-new implied elements.

    Order:
      1. All backend elements in original order (unchanged object contents)
      2. New implied elements from expansion, projected to Flexo API shape
    """
    if not backend_elements:
        return list(expanded_elements)
    if not expanded_elements:
        return list(backend_elements)

    backend_ids = {element["@id"] for element in backend_elements if element.get("@id")}
    type_templates = _build_type_key_templates(backend_elements)
    merged = list(backend_elements)

    for element in expanded_elements:
        element_id = element.get("@id")
        if not element_id or element_id in backend_ids:
            continue
        merged.append(syside_element_to_flexo_api(element, type_templates))
        backend_ids.add(element_id)

    return merged
