"""
Tests for Flexo API merge expansion helpers.
"""

import copy
import json

from flexo_syside_lib.api_expand import (
    merge_expanded_elements_for_api,
    syside_element_to_flexo_api,
)


def _backend_subsetting():
    return {
        "@id": "existing-1",
        "@type": "Subsetting",
        "elementId": "existing-1",
        "general": {"@id": "g1"},
        "owningRelatedElement": {"@id": "o1"},
        "specific": {"@id": "s1"},
        "subsettedFeature": {"@id": "sf1"},
        "subsettingFeature": {"@id": "ssf1"},
    }


def test_merge_preserves_backend_objects_verbatim():
    backend = [_backend_subsetting()]
    backend_copy = copy.deepcopy(backend)
    expanded = [
        dict(backend[0]),
        {
            "@id": "new-1",
            "@type": "Subsetting",
            "elementId": "new-1",
            "general": {"@id": "g2"},
            "owningRelatedElement": {"@id": "o2"},
            "specific": {"@id": "s2"},
            "subsettedFeature": {"@id": "sf2"},
            "subsettingFeature": {"@id": "ssf2"},
            "qualifiedName": "should-be-stripped",
            "source": [{"@id": "x"}],
        },
    ]

    merged = merge_expanded_elements_for_api(backend, expanded)

    assert merged[0] == backend_copy[0]
    assert merged[0] is backend[0]
    assert len(merged) == 2
    assert merged[1]["@id"] == "new-1"
    assert "qualifiedName" not in merged[1]
    assert "source" not in merged[1]


def test_syside_element_projects_to_backend_key_template():
    templates = {"Subsetting": set(_backend_subsetting().keys())}
    projected = syside_element_to_flexo_api(
        {
            "@id": "new-2",
            "@type": "Subsetting",
            "elementId": "new-2",
            "general": {"@id": "g3"},
            "owningRelatedElement": {"@id": "o3"},
            "specific": {"@id": "s3"},
            "subsettedFeature": {"@id": "sf3"},
            "subsettingFeature": {"@id": "ssf3"},
            "qualifiedName": "noise",
            "isImpliedIncluded": True,
        },
        templates,
    )
    assert set(projected.keys()) == set(_backend_subsetting().keys())
