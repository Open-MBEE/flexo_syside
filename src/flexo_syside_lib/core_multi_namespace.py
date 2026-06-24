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


def _split_root_namespace_documents(
    json_flexo: Any,
) -> List[Tuple[str, str]]:
    elements = _normalize_json_input(json_flexo)
    roots = find_root_namespaces(elements)
    documents: List[Tuple[str, str]] = []

    for idx, (root_index, root_namespace) in enumerate(roots):
        next_root_index = roots[idx + 1][0] if idx + 1 < len(roots) else len(elements)
        root_name = _root_namespace_name(root_namespace)
        document_elements = elements[root_index:next_root_index]
        documents.append((root_name, json.dumps(document_elements, ensure_ascii=False)))

    return documents


def _deserialize_json_to_sysml_textual(json_import: str) -> Tuple[str, List[str]]:
    captured_warnings: List[str] = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")

        try:
            deserialized_model, _ = syside.json.loads(json_import, "memory:///import.sysml")
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

    id_map = syside.IdMap()
    for mutex in syside.Environment.get_default().documents:
        with mutex.lock() as dep:
            id_map.insert_or_assign(dep)

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

    root_namespace = deserialized_model.document.root_node
    printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
    printer = syside.ModelPrinter.sysml()
    sysml_text = syside.pprint(root_namespace, printer, printer_cfg)
    return sysml_text, captured_warnings


def _deserialize_json_project_to_sysml_textual(
    json_flexo: Any,
) -> Tuple[List[Tuple[str, str]], List[str]]:
    document_sources = [
        (f"memory:///{root_name}", document_json)
        for root_name, document_json in _split_root_namespace_documents(json_flexo)
    ]

    captured_warnings: List[str] = []
    results: List[Tuple[str, str]] = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        project_model, deserialized_results = syside.json.loads(document_sources)

        for warning in wlist:
            captured_warnings.append(str(warning.message))

    del project_model

    for (root_name, _document_json), (deserialized_model, _report) in zip(
        _split_root_namespace_documents(json_flexo),
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
