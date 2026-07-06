import json
import warnings
from typing import Any, Dict, List, Tuple

import syside

from .payload import ELEMENT_TYPE_KEY
from .utils2 import print_serde_report


def _normalize_json_input(json_flexo: Any) -> List[Dict[str, Any]]:
    if isinstance(json_flexo, str):
        data = json.loads(json_flexo)
    elif isinstance(json_flexo, list):
        data = json_flexo
    elif isinstance(json_flexo, dict):
        data = [json_flexo]
    else:
        raise TypeError(
            f"json_flexo must be dict/list/str, got {type(json_flexo).__name__}"
        )

    def normalize_empty_strings(element: Any) -> Any:
        if isinstance(element, dict):
            return {key: normalize_empty_strings(value) for key, value in element.items()}
        if isinstance(element, list):
            return [normalize_empty_strings(value) for value in element]
        if element == "":
            return None
        return element

    normalized = normalize_empty_strings(data)
    if not isinstance(normalized, list):
        raise TypeError("json_flexo must decode to a top-level list or dict")
    return normalized


def _is_root_namespace(element: Any) -> bool:
    return (
        isinstance(element, dict)
        and element.get(ELEMENT_TYPE_KEY) == "Namespace"
        and "owningRelationship" not in element
    )


def _root_namespace_name(element: Dict[str, Any]) -> str:
    return (
        element.get("qualifiedName")
        or element.get("name")
        or element.get("@id")
        or "<unnamed root namespace>"
    )


def find_root_namespaces(json_flexo: Any) -> List[Tuple[int, Dict[str, Any]]]:
    elements = _normalize_json_input(json_flexo)
    roots = [
        (index, element)
        for index, element in enumerate(elements)
        if _is_root_namespace(element)
    ]
    if not roots:
        raise ValueError("No root namespace found")
    return roots


def get_root_namespace_names(json_flexo: Any) -> List[str]:
    return [_root_namespace_name(element) for _, element in find_root_namespaces(json_flexo)]


def make_root_namespace_first(json_flexo: Any, root_index: int) -> str:
    elements = _normalize_json_input(json_flexo)
    if root_index < 0 or root_index >= len(elements):
        raise IndexError(f"root_index {root_index} out of range")
    if not _is_root_namespace(elements[root_index]):
        raise ValueError(f"Element at index {root_index} is not a root namespace")

    reordered = list(elements)
    reordered.insert(0, reordered.pop(root_index))
    return json.dumps(reordered, ensure_ascii=False)


def _extract_reference_id(value: Any) -> str | None:
    if isinstance(value, dict):
        ref_id = value.get("@id")
        return ref_id if isinstance(ref_id, str) and ref_id else None
    if isinstance(value, str) and value:
        return value
    return None


def _extract_reference_ids(value: Any) -> List[str]:
    if isinstance(value, dict):
        ref_id = _extract_reference_id(value)
        return [ref_id] if ref_id is not None else []
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            result.extend(_extract_reference_ids(item))
        return result
    ref_id = _extract_reference_id(value)
    return [ref_id] if ref_id is not None else []


def _split_root_namespace_documents(
    json_flexo: Any,
) -> List[Tuple[str, str]]:
    elements = _normalize_json_input(json_flexo)
    roots = find_root_namespaces(elements)
    root_indices_by_id = {
        root_element["@id"]: root_index
        for root_index, root_element in roots
        if isinstance(root_element.get("@id"), str)
    }
    root_ids_in_order = [
        element_id
        for _index, root_element in roots
        for element_id in [_extract_reference_id(root_element.get("@id"))]
        if element_id is not None
    ]
    root_names_by_id = {
        root_element["@id"]: _root_namespace_name(root_element)
        for _index, root_element in roots
        if isinstance(root_element.get("@id"), str)
    }
    elements_by_id = {
        element["@id"]: element
        for element in elements
        if isinstance(element, dict) and isinstance(element.get("@id"), str)
    }
    ownership_reference_keys = (
        "owningRelatedElement",
        "ownedRelatedElement",
        "memberElement",
        "feature",
        "ownedMember",
        "ownedMemberElement",
        "ownedMemberFeature",
        "ownedElement",
        "owningNamespace",
        "owningType",
        "featuringType",
        "typedFeature",
    )
    incoming_ownership_refs: Dict[str, List[str]] = {}
    for owner_id, owner_element in elements_by_id.items():
        for key in ownership_reference_keys:
            for referenced_id in _extract_reference_ids(owner_element.get(key)):
                incoming_ownership_refs.setdefault(referenced_id, []).append(owner_id)
    resolved_root_by_id: Dict[str, str | None] = {}

    def resolve_root_id(
        element_id: str,
        active_ids: set[str] | None = None,
    ) -> str | None:
        if element_id in resolved_root_by_id:
            return resolved_root_by_id[element_id]
        if active_ids is None:
            active_ids = set()
        if element_id in active_ids:
            return None
        active_ids = set(active_ids)
        active_ids.add(element_id)

        visited: List[str] = []
        current_id: str | None = element_id
        root_id: str | None = None

        while current_id is not None:
            if current_id in resolved_root_by_id:
                root_id = resolved_root_by_id[current_id]
                break
            if current_id in visited:
                root_id = None
                break
            visited.append(current_id)
            current_element = elements_by_id.get(current_id)
            if current_element is None:
                root_id = None
                break
            if _is_root_namespace(current_element):
                root_id = current_id
                break
            owning_relationship_id = _extract_reference_id(
                current_element.get("owningRelationship")
            )
            if owning_relationship_id is not None:
                current_id = owning_relationship_id
                continue

            candidate_root_ids = {
                candidate_root_id
                for key in ownership_reference_keys
                for referenced_id in _extract_reference_ids(current_element.get(key))
                for candidate_root_id in [resolve_root_id(referenced_id, active_ids)]
                if candidate_root_id is not None
            }
            if len(candidate_root_ids) == 1:
                root_id = next(iter(candidate_root_ids))
            else:
                root_id = None
            break

        for visited_id in visited:
            resolved_root_by_id[visited_id] = root_id
        return root_id

    document_elements_by_root_id: Dict[str, List[Dict[str, Any]]] = {
        root_id: [] for root_id in root_ids_in_order
    }
    unassigned_elements: List[Dict[str, Any]] = []

    for element in elements:
        if not isinstance(element, dict):
            continue
        element_id = _extract_reference_id(element.get("@id"))
        if element_id is None:
            unassigned_elements.append(element)
            continue
        root_id = resolve_root_id(element_id)
        if root_id is None or root_id not in document_elements_by_root_id:
            unassigned_elements.append(element)
            continue
        document_elements_by_root_id[root_id].append(element)

    # Second pass: infer root from incoming ownership-like relationships that point at
    # the element, e.g. membership elements that reference their members.
    changed = True
    while changed and unassigned_elements:
        changed = False
        still_unassigned: List[Dict[str, Any]] = []
        for element in unassigned_elements:
            element_id = _extract_reference_id(element.get("@id"))
            if element_id is None:
                still_unassigned.append(element)
                continue

            candidate_root_ids = {
                candidate_root_id
                for owner_id in incoming_ownership_refs.get(element_id, [])
                for candidate_root_id in [resolve_root_id(owner_id)]
                if candidate_root_id is not None
            }
            if len(candidate_root_ids) != 1:
                still_unassigned.append(element)
                continue

            inferred_root_id = next(iter(candidate_root_ids))
            document_elements_by_root_id[inferred_root_id].append(element)
            resolved_root_by_id[element_id] = inferred_root_id
            changed = True

        unassigned_elements = still_unassigned

    # Last-resort fallback for valid elements that do not expose ownership links directly.
    # Use their original position relative to root namespaces, which matches our own serializer
    # and remains a pragmatic fallback for Flexo server responses with sparse ownership fields.
    still_unassigned: List[Dict[str, Any]] = []
    for element in unassigned_elements:
        try:
            element_index = elements.index(element)
        except ValueError:
            still_unassigned.append(element)
            continue

        fallback_root_id: str | None = None
        for root_id, root_index in sorted(
            root_indices_by_id.items(), key=lambda item: item[1]
        ):
            if root_index <= element_index:
                fallback_root_id = root_id
            else:
                break

        if fallback_root_id is None:
            still_unassigned.append(element)
            continue
        document_elements_by_root_id[fallback_root_id].append(element)

    unassigned_elements = still_unassigned

    documents: List[Tuple[str, str]] = []
    for _root_index, root_namespace in roots:
        root_id = root_namespace.get("@id")
        if not isinstance(root_id, str):
            continue
        root_name = root_names_by_id[root_id]
        document_elements = list(document_elements_by_root_id[root_id])
        root_positions = [
            index
            for index, element in enumerate(document_elements)
            if _extract_reference_id(element.get("@id")) == root_id
        ]
        if root_positions:
            root_position = root_positions[0]
            document_elements.insert(0, document_elements.pop(root_position))
        if document_elements:
            documents.append((root_name, json.dumps(document_elements, ensure_ascii=False)))

    if unassigned_elements:
        unassigned_ids = [
            element.get("@id")
            for element in unassigned_elements
            if isinstance(element.get("@id"), str)
        ]
        raise ValueError(
            "Could not assign some elements to a root namespace via owningRelationship: "
            + ", ".join(unassigned_ids[:10])
        )

    return documents


def _deserialize_json_to_sysml_textual(json_import: str) -> Tuple[str, List[str]]:
    captured_warnings: List[str] = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")

        try:
            _project_model, deserialized_results = syside.json.loads(
                [("memory:///import.sysml", json_import)]
            )
        except Exception as exc:
            try:
                from syside.json import DeserializationError
            except Exception:
                try:
                    from syside.core import DeserializationError
                except Exception:
                    DeserializationError = type(None)

            if isinstance(exc, DeserializationError):
                report = getattr(exc, "report", None)
                if report is None and getattr(exc, "args", None) and len(exc.args) >= 2:
                    report = exc.args[1]
                captured_warnings.append(f"Deserialization failed: {report}")
                return "", captured_warnings
            raise

        for warning in wlist:
            captured_warnings.append(str(warning.message))

    deserialized_model, _ = deserialized_results[0]

    env = syside.Environment.get_default()
    id_map = syside.IdMap()
    for mutex in env.documents:
        with mutex.lock() as dep:
            id_map.insert_or_assign(dep)

    documents_to_resolve = [deserialized_model.document]
    with deserialized_model.document.mutex.lock() as locked_document:
        id_map.insert_or_assign(locked_document)

    try:
        deserialized_model.link(id_map)
    except Exception as exc:
        try:
            from syside.core import DeserializationError
        except Exception:
            DeserializationError = type(None)

        if isinstance(exc, DeserializationError):
            report = getattr(exc, "report", None)
            if report is None and getattr(exc, "args", None) and len(exc.args) >= 2:
                report = exc.args[1]
            print("Deserialization failed. Diagnostic report:")
            print_serde_report(report)
        else:
            raise

    syside.Sema().resolve(
        documents_to_resolve,
        env.index(),
        env.lib,
    )

    root_namespace = deserialized_model.document.root_node
    printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
    printer = syside.ModelPrinter.sysml()
    sysml_text = syside.pprint(root_namespace, printer, printer_cfg)
    return sysml_text, captured_warnings


def _deserialize_json_project_to_sysml_textual(
    json_flexo: Any,
) -> Tuple[List[Tuple[str, str]], List[str]]:
    split_documents = _split_root_namespace_documents(json_flexo)
    document_sources = [
        (f"memory:///{root_name}", document_json)
        for root_name, document_json in split_documents
    ]

    captured_warnings: List[str] = []
    results: List[Tuple[str, str]] = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        _project_model, deserialized_results = syside.json.loads(document_sources)

        for warning in wlist:
            captured_warnings.append(str(warning.message))

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

    for (root_name, _document_json), (deserialized_model, _report) in zip(
        split_documents,
        deserialized_results,
    ):
        root_namespace = deserialized_model.document.root_node
        printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
        printer = syside.ModelPrinter.sysml()
        sysml_text = syside.pprint(root_namespace, printer, printer_cfg)
        results.append((root_name, sysml_text))

    return results, captured_warnings


def convert_json_to_sysml_textual_multi_namespace(
    json_flexo: Any, debug: bool = False
) -> Tuple[List[Tuple[str, str]], List[str]]:
    del debug

    if len(find_root_namespaces(json_flexo)) > 1:
        return _deserialize_json_project_to_sysml_textual(json_flexo)

    results: List[Tuple[str, str]] = []
    captured_warnings: List[str] = []

    for root_index, root_namespace in find_root_namespaces(json_flexo):
        root_name = _root_namespace_name(root_namespace)
        json_import = make_root_namespace_first(json_flexo, root_index)
        sysml_text, warnings_for_root = _deserialize_json_to_sysml_textual(json_import)
        captured_warnings.extend(
            f"[{root_name}] {warning}" for warning in warnings_for_root
        )
        if sysml_text:
            results.append((root_name, sysml_text))

    return results, captured_warnings
