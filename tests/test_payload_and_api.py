import json

import pytest

from flexo_syside_lib.core import (
    _make_root_namespace_first,
    _remove_uri_fields,
    _replace_none_with_empty,
    _wrap_elements_as_payload,
)


def test_replace_none_with_empty():
    data = {"a": None, "b": [1, None, {"c": None}]}
    out = _replace_none_with_empty(data)
    assert out == {"a": "", "b": [1, None, {"c": ""}]}


def test_remove_uri_fields():
    data = {"@uri": "x", "a": {"@uri": "y", "b": 1}, "c": [{"@uri": "z"}, {"d": 2}]}
    out = _remove_uri_fields(data)
    assert out == {"a": {"b": 1}, "c": [{}, {"d": 2}]}


def test_wrap_elements_as_payload():
    elements = [
        {"@id": "ID1", "@uri": "ignore", "name": None},
        {"name": "X", "props": [None, 1]},
    ]
    wrapped = _wrap_elements_as_payload(elements)
    assert wrapped[0]["identity"] == {"@id": "ID1"}
    assert wrapped[0]["payload"]["name"] == ""
    assert wrapped[1]["payload"]["props"][0] is None


def test_make_root_namespace_first():
    items = [
        {"@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@type": "Element"},
        {"@type": "Namespace"},
    ]
    out = _make_root_namespace_first(json.dumps(items))
    arr = json.loads(out)
    assert arr[0]["@type"] == "Namespace"
    assert "qualifiedName" not in arr[0]


def test_make_root_namespace_first_with_timestamp():
    items = [
        {"@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@type": "Element"},
        {"@type": "Namespace", "qualifiedName": "2021-01-01T00:00:00Z"},
    ]
    out = _make_root_namespace_first(json.dumps(items))
    arr = json.loads(out)
    assert arr[0]["qualifiedName"] == "2021-01-01T00:00:00Z"


def test_make_root_namespace_first_no_namespace():
    with pytest.raises(ValueError, match="No root namespace found"):
        _make_root_namespace_first(json.dumps([{"@type": "Element"}, {"@type": "Block"}]))


def test_package_root_exports_conversion_helpers():
    import flexo_syside_lib

    assert callable(flexo_syside_lib.convert_sysml_file_textual_to_json)
    assert callable(flexo_syside_lib.convert_sysml_string_textual_to_json)
    assert callable(flexo_syside_lib.convert_json_to_sysml_textual)
    assert callable(flexo_syside_lib.expand_minimal_json_to_full_json)
    assert flexo_syside_lib.__version__ == "0.4.1"


def test_convert_json_to_sysml_textual_invalid_input():
    from flexo_syside_lib.core import convert_json_to_sysml_textual

    with pytest.raises(TypeError, match="json_flexo must be dict/list/str"):
        convert_json_to_sysml_textual(123)


def test_expand_minimal_json_to_full_json_rejects_invalid_input():
    from flexo_syside_lib.core import expand_minimal_json_to_full_json

    with pytest.raises(TypeError, match="minimal_json must be dict/list/str"):
        expand_minimal_json_to_full_json(123)
