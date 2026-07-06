from __future__ import annotations

import json
from typing import Any

import syside

from .payload import ELEMENT_TYPE_KEY, apply_root_namespace_name, wrap_elements_as_payload
from .serde import (
    convert_json_to_sysml_textual,
    convert_sysml_string_textual_to_json,
    create_json_writer,
    create_serialization_options,
)


def _document_source_name(root_name: str) -> str:
    return root_name if root_name.endswith((".sysml", ".kerml")) else f"{root_name}.sysml"


def _load_resolved_project_documents(
    json_in: Any,
) -> tuple[
    list[tuple[str, str]],
    list[tuple[Any, Any]],
]:
    from .core_multi_namespace import _split_root_namespace_documents

    document_chunks = _split_root_namespace_documents(json_in)
    document_sources = [
        (f"memory:///{_document_source_name(root_name)}", chunk_json)
        for root_name, chunk_json in document_chunks
    ]
    _project_model, deserialized_results = syside.json.loads(document_sources)

    env = syside.Environment.get_default()
    id_map = syside.IdMap()
    for mutex in env.documents:
        with mutex.lock() as dep:
            id_map.insert_or_assign(dep)

    documents_to_resolve = []
    for deserialized_model, _report in deserialized_results:
        documents_to_resolve.append(deserialized_model.document)
        with deserialized_model.document.mutex.lock() as locked_document:
            id_map.insert_or_assign(locked_document)

    for deserialized_model, _report in deserialized_results:
        deserialized_model.link(id_map)

    syside.Sema().resolve(
        documents_to_resolve,
        env.index(),
        env.lib,
    )

    return document_chunks, deserialized_results


def expand_minimal_json_to_full_json(minimal_json: Any) -> tuple[list[dict[str, Any]], str]:
    """
    Expand minimal SysML JSON into the repository's current non-minimal JSON form.

    This uses JSON deserialization followed by round-tripping through text when
    possible, with the direct model-expansion path as fallback.
    Returns (change_payload, json_string), matching convert_sysml_*_to_json.
    """
    from .core_multi_namespace import (
        _split_root_namespace_documents,
        get_root_namespace_names,
    )

    def _expand_namespace_model(
        root_name: str,
        sysml_text: str,
        minimal_document_json: Any,
    ) -> list[dict[str, Any]]:
        try:
            _, full_json_string = convert_sysml_string_textual_to_json(
                sysml_model_string=sysml_text,
                minimal=False,
            )
        except Exception:
            _, full_json_string = expand_minimal_json_to_full_json_model(minimal_document_json)

        return apply_root_namespace_name(json.loads(full_json_string), root_name)

    if isinstance(minimal_json, (dict, list)):
        json_in = minimal_json
    elif isinstance(minimal_json, str):
        json_in = json.loads(minimal_json)
    else:
        raise TypeError(
            f"minimal_json must be dict/list/str, got {type(minimal_json).__name__}"
        )

    root_namespace_names = get_root_namespace_names(json_in)

    if len(root_namespace_names) == 1:
        json_single_root_original = json.loads(json.dumps(json_in, ensure_ascii=False))
        json_single_root = json.loads(json.dumps(json_in, ensure_ascii=False))
        if isinstance(json_single_root, dict):
            json_single_root = [json_single_root]
        for element in json_single_root:
            if (
                element.get(ELEMENT_TYPE_KEY) == "Namespace"
                and "owningRelationship" not in element
            ):
                element["qualifiedName"] = None
                break

        (sysml_text, _deserialized_model), captured_warnings = convert_json_to_sysml_textual(
            json_single_root
        )
        del captured_warnings
        expanded_elements = _expand_namespace_model(
            root_namespace_names[0],
            sysml_text,
            json_single_root_original,
        )
    else:
        document_chunks = _split_root_namespace_documents(json_in)
        document_sources = [
            (f"memory:///{_document_source_name(root_name)}", chunk_json)
            for root_name, chunk_json in document_chunks
        ]
        _project_model, deserialized_results = syside.json.loads(document_sources)
        options = create_serialization_options()
        expanded_elements: list[dict[str, Any]] = []
        for (root_name, _chunk_json), (deserialized_model, _report) in zip(
            document_chunks,
            deserialized_results,
        ):
            writer = create_json_writer()
            with deserialized_model.document.mutex.lock() as locked_document:
                syside.serialize(locked_document.root_node, writer, options)
            full_json_elements = apply_root_namespace_name(
                json.loads(writer.result),
                root_name,
            )
            expanded_elements.extend(full_json_elements)

    expanded_json_string = json.dumps(expanded_elements, indent=2)
    return wrap_elements_as_payload(expanded_elements), expanded_json_string


def expand_minimal_json_to_full_json_model(
    minimal_json: Any,
) -> tuple[list[dict[str, Any]], str]:
    """
    Expand minimal SysML JSON into the repository's current non-minimal JSON form.

    This uses JSON deserialization as a multi-document project followed by
    semantic resolution so implied relationships are reconstructed without
    round-tripping through text.
    Returns (change_payload, json_string), matching convert_sysml_*_to_json.
    """
    if isinstance(minimal_json, (dict, list)):
        json_in = minimal_json
    elif isinstance(minimal_json, str):
        json_in = json.loads(minimal_json)
    else:
        raise TypeError(
            f"minimal_json must be dict/list/str, got {type(minimal_json).__name__}"
        )

    document_chunks, deserialized_results = _load_resolved_project_documents(json_in)

    options = create_serialization_options()
    expanded_elements: list[dict[str, Any]] = []
    for (root_name, _chunk_json), (deserialized_model, _report) in zip(
        document_chunks,
        deserialized_results,
    ):
        writer = create_json_writer()
        with deserialized_model.document.mutex.lock() as locked_document:
            syside.serialize(locked_document.root_node, writer, options)
        full_json_elements = apply_root_namespace_name(
            json.loads(writer.result),
            root_name,
        )
        expanded_elements.extend(full_json_elements)

    json_string = json.dumps(expanded_elements, indent=2)
    return wrap_elements_as_payload(expanded_elements), json_string
