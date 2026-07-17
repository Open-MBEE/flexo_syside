import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from flexo_syside_lib.core import (
    _create_json_writer,
    _create_serialization_options,
    convert_sysml_file_textual_to_json,
    convert_sysml_files_textual_to_json,
    convert_sysml_models_textual_to_json,
    convert_sysml_string_textual_to_json,
    expand_minimal_json_to_full_json,
)


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_string_to_json(mock_syside):
    sample_sysml = """
    package TestPackage {
        part def Component {
            attribute name: String;
        }
    }
    """
    sample_json = [
        {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
    ]

    mock_model = Mock()
    mock_diagnostics = Mock()
    mock_diagnostics.contains_errors.return_value = False
    mock_syside.load_model.return_value = (mock_model, mock_diagnostics)
    mock_model.user_docs = [Mock()]
    mock_locked = Mock()
    mock_locked.root_node = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_locked)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_model.user_docs[0].lock.return_value = mock_context_manager

    mock_writer = Mock()
    mock_writer.result = json.dumps(sample_json)
    mock_options = Mock()

    with patch("flexo_syside_lib.serde.create_json_writer", return_value=mock_writer), patch(
        "flexo_syside_lib.serde.create_serialization_options", return_value=mock_options
    ), patch("flexo_syside_lib.serde.syside.serialize"):
        payload, json_string = convert_sysml_string_textual_to_json(sample_sysml)

    assert isinstance(payload, list)
    assert len(payload) > 0
    parsed_json = json.loads(json_string)
    assert isinstance(parsed_json, list)
    assert len(parsed_json) > 0


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_file_to_json(mock_syside):
    sample_sysml = """
    package TestPackage {
        part def Component {
            attribute name: String;
        }
    }
    """
    sample_json = [
        {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
    ]

    mock_model = Mock()
    mock_diagnostics = Mock()
    mock_diagnostics.contains_errors.return_value = False
    mock_syside.try_load_model.return_value = (mock_model, mock_diagnostics)
    mock_model.user_docs = [Mock()]
    mock_locked = Mock()
    mock_locked.root_node = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_locked)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_model.user_docs[0].lock.return_value = mock_context_manager

    mock_writer = Mock()
    mock_writer.result = json.dumps(sample_json)
    mock_options = Mock()

    with patch("flexo_syside_lib.serde.create_json_writer", return_value=mock_writer), patch(
        "flexo_syside_lib.serde.create_serialization_options", return_value=mock_options
    ), patch("flexo_syside_lib.serde.syside.serialize"):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sysml", delete=False) as f:
            f.write(sample_sysml)
            temp_file = f.name

        try:
            payload, json_string = convert_sysml_file_textual_to_json(temp_file)
            parsed_json = json.loads(json_string)
            root_namespaces = [
                element
                for element in parsed_json
                if element["@type"] == "Namespace" and "owningRelationship" not in element
            ]
            assert isinstance(payload, list)
            assert root_namespaces[0]["qualifiedName"] == os.path.basename(temp_file)
        finally:
            os.unlink(temp_file)


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_files_to_json(mock_syside):
    sample_doc_1 = [
        {"@id": "ns1", "@type": "Namespace", "name": "Alpha"},
        {"@id": "pkg1", "@type": "Package", "declaredName": "Alpha"},
    ]
    sample_doc_2 = [
        {"@id": "ns2", "@type": "Namespace", "name": "Beta"},
        {"@id": "pkg2", "@type": "Package", "declaredName": "Beta"},
    ]

    mock_model = Mock()
    mock_diagnostics = Mock()
    mock_diagnostics.contains_errors.return_value = False
    mock_syside.try_load_model.return_value = (mock_model, mock_diagnostics)

    locked_1 = Mock()
    locked_1.root_node = Mock()
    ctx_1 = Mock()
    ctx_1.__enter__ = Mock(return_value=locked_1)
    ctx_1.__exit__ = Mock(return_value=None)
    locked_2 = Mock()
    locked_2.root_node = Mock()
    ctx_2 = Mock()
    ctx_2.__enter__ = Mock(return_value=locked_2)
    ctx_2.__exit__ = Mock(return_value=None)

    doc_1 = Mock()
    doc_1.lock.return_value = ctx_1
    doc_2 = Mock()
    doc_2.lock.return_value = ctx_2
    mock_model.user_docs = [doc_1, doc_2]

    writer_1 = Mock()
    writer_1.result = json.dumps(sample_doc_1)
    writer_2 = Mock()
    writer_2.result = json.dumps(sample_doc_2)
    mock_options = Mock()

    with patch("flexo_syside_lib.serde.create_json_writer", side_effect=[writer_1, writer_2]), patch(
        "flexo_syside_lib.serde.create_serialization_options", return_value=mock_options
    ), patch("flexo_syside_lib.serde.syside.serialize"):
        payload, json_string = convert_sysml_files_textual_to_json(["alpha.sysml", "beta.sysml"])

    parsed_json = json.loads(json_string)
    assert [element["@id"] for element in parsed_json] == ["ns1", "pkg1", "ns2", "pkg2"]
    assert [
        element["qualifiedName"]
        for element in parsed_json
        if element["@type"] == "Namespace" and "owningRelationship" not in element
    ] == ["alpha.sysml", "beta.sysml"]
    assert isinstance(payload, list)
    assert len(payload) == 4


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_models_to_json_uses_environment_models(mock_syside):
    env_model = Mock()
    env_model.to_environment.return_value = "ENV"
    env_diags = Mock()
    env_diags.contains_errors.return_value = False

    main_model = Mock()
    main_diags = Mock()
    main_diags.contains_errors.return_value = False
    main_model.user_docs = [Mock()]
    locked = Mock()
    locked.root_node = Mock()
    context_manager = Mock()
    context_manager.__enter__ = Mock(return_value=locked)
    context_manager.__exit__ = Mock(return_value=None)
    main_model.user_docs[0].lock.return_value = context_manager

    mock_syside.try_load_model.side_effect = [
        (env_model, env_diags),
        (main_model, main_diags),
    ]

    writer = Mock()
    writer.result = json.dumps(
        [{"@id": "ns1", "@type": "Namespace", "qualifiedName": "alpha.sysml"}]
    )
    options = Mock()

    with patch("flexo_syside_lib.serde.create_json_writer", return_value=writer), patch(
        "flexo_syside_lib.serde.create_serialization_options", return_value=options
    ), patch("flexo_syside_lib.serde.syside.serialize"):
        payload, json_string = convert_sysml_models_textual_to_json(
            [("alpha.sysml", "package Alpha;")],
            environment_models=[("lib.sysml", "library package Lib; end;")],
        )

    assert isinstance(payload, list)
    assert json.loads(json_string)[0]["qualifiedName"] == "alpha.sysml"
    assert mock_syside.try_load_model.call_count == 2
    assert mock_syside.try_load_model.call_args_list[1].kwargs["environment"] == "ENV"


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_models_to_json_allows_duplicate_basenames_in_environment(mock_syside):
    env_model = Mock()
    env_model.to_environment.return_value = "ENV"
    env_diags = Mock()
    env_diags.contains_errors.return_value = False

    main_model = Mock()
    main_diags = Mock()
    main_diags.contains_errors.return_value = False
    main_model.user_docs = [Mock()]
    locked = Mock()
    locked.root_node = Mock()
    context_manager = Mock()
    context_manager.__enter__ = Mock(return_value=locked)
    context_manager.__exit__ = Mock(return_value=None)
    main_model.user_docs[0].lock.return_value = context_manager

    mock_syside.try_load_model.side_effect = [
        (env_model, env_diags),
        (main_model, main_diags),
    ]

    writer = Mock()
    writer.result = json.dumps(
        [{"@id": "ns1", "@type": "Namespace", "qualifiedName": "alpha.sysml"}]
    )
    options = Mock()

    with patch("flexo_syside_lib.serde.create_json_writer", return_value=writer), patch(
        "flexo_syside_lib.serde.create_serialization_options", return_value=options
    ), patch("flexo_syside_lib.serde.syside.serialize"):
        payload, json_string = convert_sysml_models_textual_to_json(
            [("workspace/alpha.sysml", "package Alpha;")],
            environment_models=[
                ("LibA/root/package.sysml", "library package LibA; end;"),
                ("LibB/root/package.sysml", "library package LibB; end;"),
            ],
        )

    assert isinstance(payload, list)
    assert json.loads(json_string)[0]["qualifiedName"] == "alpha.sysml"
    env_call_paths = mock_syside.try_load_model.call_args_list[0].args[0]
    assert len(env_call_paths) == 2
    assert env_call_paths[0] != env_call_paths[1]
    assert env_call_paths[0].endswith("LibA\\root\\package.sysml") or env_call_paths[0].endswith("LibA/root/package.sysml")
    assert env_call_paths[1].endswith("LibB\\root\\package.sysml") or env_call_paths[1].endswith("LibB/root/package.sysml")


@patch("flexo_syside_lib.serde.syside")
def test_convert_sysml_models_to_json_surfaces_diagnostics_in_assertion(mock_syside):
    env_model = Mock()
    env_model.to_environment.return_value = "ENV"
    env_diags = Mock()
    env_diags.contains_errors.return_value = False

    failure_diag = Mock()
    failure_diag.message = "Couldn't resolve import Demo::Library"
    failure_diag.severity = "error"
    failure_diag.file = "/tmp/0000_workspace/test.sysml"
    failure_diag.line = 7
    failure_diag.col = 3

    main_diags = Mock()
    main_diags.contains_errors.return_value = True
    main_diags.all = [failure_diag]

    mock_syside.try_load_model.side_effect = [
        (env_model, env_diags),
        (Mock(), main_diags),
    ]

    with pytest.raises(AssertionError) as excinfo:
        convert_sysml_models_textual_to_json(
            [("workspace/test.sysml", "package Test;")],
            environment_models=[("Demo/root/library.sysml", "library package Demo; end;")],
        )

    message = str(excinfo.value)
    assert "textual models load failed" in message
    assert "Couldn't resolve import Demo::Library" in message
    assert "workspace/test.sysml" in message
    assert "0000_workspace" in message
    assert "flexo_syside_lib" in message


@patch("flexo_syside_lib.serde.syside")
def test_create_json_writer(mock_syside):
    mock_writer_class = Mock()
    mock_writer_instance = Mock()
    mock_writer_class.return_value = mock_writer_instance
    mock_syside.JsonStringWriter = mock_writer_class
    mock_syside.JsonStringOptions = Mock()
    writer = _create_json_writer()
    assert writer is not None
    mock_writer_class.assert_called_once()


@patch("flexo_syside_lib.serde.syside")
def test_create_serialization_options(mock_syside):
    mock_options = Mock()
    mock_syside.SerializationOptions.return_value.minimal.return_value.with_options.return_value = (
        mock_options
    )
    mock_syside.FailAction = Mock()
    mock_syside.FailAction.Ignore = "ignore"
    options = _create_serialization_options()
    assert options is not None
    mock_syside.SerializationOptions.assert_called_once()


@patch("flexo_syside_lib.expansion.syside")
def test_expand_minimal_json_to_full_json_from_raw_list(mock_syside):
    del mock_syside
    sample_minimal_json = [{"@id": "ns1", "@type": "Namespace", "qualifiedName": "alpha.sysml"}]
    sample_full_json = [
        {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
    ]

    with patch(
        "flexo_syside_lib.expansion.convert_json_to_sysml_textual",
        return_value=(("package Alpha {}", Mock()), []),
    ) as mock_to_text, patch(
        "flexo_syside_lib.expansion.convert_sysml_string_textual_to_json",
        return_value=([], json.dumps(sample_full_json)),
    ) as mock_to_full:
        payload, json_string = expand_minimal_json_to_full_json(sample_minimal_json)

    parsed_json = json.loads(json_string)
    assert isinstance(payload, list)
    assert parsed_json[0]["qualifiedName"] == "alpha.sysml"
    mock_to_text.assert_called_once()
    mock_to_full.assert_called_once()
