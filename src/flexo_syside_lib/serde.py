from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import syside

from .payload import ELEMENT_TYPE_KEY, wrap_elements_as_payload
from .utils2 import print_serde_report


def make_root_namespace_first_legacy(json_str: str) -> str:
    obj = json.loads(json_str)

    found_root_namespace = None
    timestamp = datetime.fromisoformat("1970-01-01T12:00:00+00:00")

    def empty_to_none_and_search(element: Any, index: int | None = None) -> Any:
        nonlocal found_root_namespace, timestamp

        if isinstance(element, dict):
            if (
                element.get(ELEMENT_TYPE_KEY) == "Namespace"
                and "owningRelationship" not in element
            ):
                current = element.get("qualifiedName", None)
                if current is None:
                    found_root_namespace = index
                else:
                    try:
                        current_dt = datetime.fromisoformat(current.replace("Z", "+00:00"))
                        if current_dt > timestamp:
                            timestamp = current_dt
                            found_root_namespace = index
                    except Exception:
                        if found_root_namespace is None:
                            found_root_namespace = index

            return {
                key: empty_to_none_and_search(value)
                for key, value in element.items()
            }

        if isinstance(element, list):
            return [empty_to_none_and_search(value, i) for i, value in enumerate(element)]

        if element == "":
            return None

        return element

    obj = [empty_to_none_and_search(element, i) for i, element in enumerate(obj)]

    if found_root_namespace is None:
        raise ValueError("No root namespace found")

    obj.insert(0, obj.pop(found_root_namespace))
    return json.dumps(obj)


def create_json_writer() -> syside.JsonStringWriter:
    json_options = syside.JsonStringOptions()
    json_options.include_cross_ref_uris = False
    json_options.indent = False
    return syside.JsonStringWriter(json_options)


def create_serialization_options() -> syside.SerializationOptions:
    options = syside.SerializationOptions().minimal().with_options(
        use_standard_names=True,
        include_derived=True,
        include_redefined=True,
        include_default=False,
        include_optional=False,
        include_implied=True,
    )
    options.fail_action = syside.FailAction.Ignore
    return options


def model_to_json(
    model: syside.Model,
    minimal: bool = False,
    set_rootnamespace_date: bool = False,
    root_namespace_names: list[str] | None = None,
) -> str:
    assert len(model.user_docs) >= 1
    if root_namespace_names is not None:
        assert len(root_namespace_names) == len(model.user_docs)

    options = syside.SerializationOptions.minimal() if minimal else create_serialization_options()

    serialized_elements: list[dict[str, Any]] = []
    root_namespace_count = 0

    for doc_index, doc_mutex in enumerate(model.user_docs):
        writer = create_json_writer()
        with doc_mutex.lock() as locked:
            syside.serialize(locked.root_node, writer, options)
        doc_elements = json.loads(writer.result)
        for element in doc_elements:
            if (
                element.get(ELEMENT_TYPE_KEY) == "Namespace"
                and "owningRelationship" not in element
            ):
                if root_namespace_names is not None:
                    element["qualifiedName"] = root_namespace_names[doc_index]
                elif set_rootnamespace_date:
                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    element["qualifiedName"] = now_str
                    root_namespace_count += 1
                break
        serialized_elements.extend(doc_elements)

    if set_rootnamespace_date:
        assert root_namespace_count == len(model.user_docs)

    return json.dumps(serialized_elements, indent=2)


def convert_sysml_file_textual_to_json(
    sysml_file_path: str,
    json_out_path: str | None = None,
    minimal: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    model, diagnostics = syside.try_load_model([sysml_file_path])
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = model_to_json(
        model,
        minimal,
        root_namespace_names=[Path(sysml_file_path).name],
    )
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)

    data = json.loads(json_string)
    return wrap_elements_as_payload(data), json_string


def convert_sysml_files_textual_to_json(
    sysml_file_paths: list[str],
    json_out_path: str | None = None,
    minimal: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    model, diagnostics = syside.try_load_model(sysml_file_paths)
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = model_to_json(
        model,
        minimal,
        root_namespace_names=[Path(sysml_file_path).name for sysml_file_path in sysml_file_paths],
    )
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)

    data = json.loads(json_string)
    return wrap_elements_as_payload(data), json_string


def convert_sysml_string_textual_to_json(
    sysml_model_string: str,
    json_out_path: str | None = None,
    minimal: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    model, diagnostics = syside.load_model(sysml_source=sysml_model_string)
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = model_to_json(model, minimal)
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)

    data = json.loads(json_string)
    return wrap_elements_as_payload(data), json_string


def convert_json_to_sysml_textual(
    json_flexo: Any,
    debug: bool = False,
    make_root_namespace_first: bool = False,
) -> tuple[tuple[str, Any] | None, list[str]]:
    del debug
    captured_warnings: list[str] = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")

        if isinstance(json_flexo, (dict, list)):
            json_in = json.dumps(json_flexo, ensure_ascii=False)
        elif isinstance(json_flexo, str):
            json_in = json_flexo
        else:
            raise TypeError(
                f"json_flexo must be dict/list/str, got {type(json_flexo).__name__}"
            )

        json_import = (
            make_root_namespace_first_legacy(json_in)
            if make_root_namespace_first
            else json_in
        )

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
                model = getattr(exc, "model", None)
                if report is None and getattr(exc, "args", None) and len(exc.args) >= 2:
                    model = exc.args[0]
                    report = exc.args[1]
                del model
                captured_warnings.append(f"Deserialization failed: {report}")
                return None, captured_warnings
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
            model = getattr(exc, "model", None)
            if report is None and getattr(exc, "args", None) and len(exc.args) >= 2:
                model = exc.args[0]
                report = exc.args[1]
            del model
            print("Deserialization failed. Diagnostic report:")
            print_serde_report(report)
        else:
            raise

    root_namespace = deserialized_model.document.root_node
    printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
    printer = syside.ModelPrinter.sysml()
    sysml_text = syside.pprint(root_namespace, printer, printer_cfg)
    return (sysml_text, deserialized_model), captured_warnings
