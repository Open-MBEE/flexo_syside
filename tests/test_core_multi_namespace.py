import json
from unittest.mock import Mock, patch

import pytest

from flexo_syside_lib.core_multi_namespace import (
    convert_json_to_sysml_textual_multi_namespace,
    find_root_namespaces,
    get_root_namespace_names,
    make_root_namespace_first,
    _split_root_namespace_documents,
)


def test_find_root_namespaces_returns_all_roots():
    data = [
        {"@id": "ns-1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@id": "el-1", "@type": "PartDefinition"},
        {"@id": "ns-2", "@type": "Namespace", "name": "Second"},
    ]

    roots = find_root_namespaces(data)

    assert [index for index, _ in roots] == [0, 2]
    assert [root["@id"] for _, root in roots] == ["ns-1", "ns-2"]


def test_get_root_namespace_names_uses_fallbacks():
    data = [
        {
            "@id": "ns-1",
            "@type": "Namespace",
            "name": "Alpha",
            "qualifiedName": "alpha.sysml",
        },
        {"@id": "ns-2", "@type": "Namespace", "qualifiedName": "2021-01-01T00:00:00Z"},
        {"@id": "ns-3", "@type": "Namespace"},
    ]

    assert get_root_namespace_names(data) == [
        "alpha.sysml",
        "2021-01-01T00:00:00Z",
        "ns-3",
    ]


def test_make_root_namespace_first_moves_requested_root():
    data = [
        {"@id": "ns-1", "@type": "Namespace", "name": "Alpha"},
        {"@id": "el-1", "@type": "PartDefinition"},
        {"@id": "ns-2", "@type": "Namespace", "name": "Beta"},
    ]

    reordered = json.loads(make_root_namespace_first(data, 2))

    assert reordered[0]["@id"] == "ns-2"
    assert reordered[1]["@id"] == "ns-1"


def test_split_root_namespace_documents_preserves_document_chunks():
    data = [
        {"@id": "ns-1", "@type": "Namespace", "qualifiedName": "alpha.sysml"},
        {"@id": "pkg-1", "@type": "Package", "declaredName": "Alpha"},
        {"@id": "ns-2", "@type": "Namespace", "qualifiedName": "beta.sysml"},
        {"@id": "pkg-2", "@type": "Package", "declaredName": "Beta"},
    ]

    documents = _split_root_namespace_documents(data)

    assert [name for name, _ in documents] == ["alpha.sysml", "beta.sysml"]
    assert [element["@id"] for element in json.loads(documents[0][1])] == ["ns-1", "pkg-1"]
    assert [element["@id"] for element in json.loads(documents[1][1])] == ["ns-2", "pkg-2"]


@patch("flexo_syside_lib.core_multi_namespace.syside")
def test_convert_json_to_sysml_textual_multi_namespace_returns_tuple_per_root(mock_syside):
    data = [
        {"@id": "ns-1", "@type": "Namespace", "name": "Alpha", "qualifiedName": "alpha.sysml"},
        {"@id": "el-1", "@type": "PartDefinition"},
        {"@id": "ns-2", "@type": "Namespace", "name": "Beta", "qualifiedName": "beta.sysml"},
    ]

    mock_env = Mock()
    mock_dep_ctx = Mock()
    mock_dep = Mock()
    mock_dep_ctx.__enter__ = Mock(return_value=mock_dep)
    mock_dep_ctx.__exit__ = Mock(return_value=None)
    mock_mutex = Mock()
    mock_mutex.lock.return_value = mock_dep_ctx
    mock_env.documents = [mock_mutex]
    mock_syside.Environment.get_default.return_value = mock_env
    mock_syside.IdMap.return_value = Mock()
    mock_syside.PrinterConfig.return_value = Mock()
    mock_syside.ModelPrinter.sysml.return_value = Mock()

    def fake_loads(json_import, *_args, **_kwargs):
        if isinstance(json_import, list):
            results = []
            for _url, src in json_import:
                first = json.loads(src)[0]
                model = Mock()
                model.document.root_node = first
                results.append((model, Mock()))
            return Mock(), results

        first = json.loads(json_import)[0]
        model = Mock()
        model.link.return_value = (Mock(), True)
        model.document.root_node = first
        return model, Mock()

    mock_syside.json.loads.side_effect = fake_loads
    mock_syside.pprint.side_effect = lambda root, *_args: f"sysml::{root['name']}"

    results, warnings = convert_json_to_sysml_textual_multi_namespace(data)

    assert results == [
        ("alpha.sysml", "sysml::Alpha"),
        ("beta.sysml", "sysml::Beta"),
    ]
    assert warnings == []
    assert mock_syside.json.loads.call_count == 1


def test_find_root_namespaces_rejects_missing_root():
    with pytest.raises(ValueError, match="No root namespace found"):
        find_root_namespaces([{"@type": "PartDefinition"}])
