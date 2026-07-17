from __future__ import annotations

import json
import os
import tempfile
import warnings
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

import syside

from .payload import ELEMENT_TYPE_KEY, wrap_elements_as_payload
from .utils2 import print_serde_report

try:
    _PACKAGE_VERSION = package_version("flexo_syside_lib")
except PackageNotFoundError:
    _PACKAGE_VERSION = "unknown"


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


def _write_models_to_temp_paths(
    tmp_dir: str,
    sysml_models: list[tuple[str, str]],
) -> tuple[list[str], list[str]]:
    basenames = [Path(filename).name for filename, _text in sysml_models]
    temp_paths: list[str] = []
    used_paths: set[str] = set()
    for index, (filename, sysml_text) in enumerate(sysml_models):
        relative_path = Path(str(filename or "").replace("\\", "/"))
        parts = [part for part in relative_path.parts if part not in {"", ".", ".."}]
        basename = parts[-1] if parts else f"model-{index + 1}.sysml"
        suffix = Path(basename).suffix.lower()
        if suffix not in {".sysml", ".kerml", ".syml"}:
            suffix = ".sysml"
        stem = Path(basename).stem or f"model-{index + 1}"
        rel_parts = [f"{index:04d}"]
        if len(parts) > 1:
            rel_parts.extend(parts[:-1])
        rel_parts.append(f"{stem}{suffix}")
        temp_path = Path(tmp_dir).joinpath(*rel_parts)
        while os.fspath(temp_path) in used_paths:
            temp_path = temp_path.with_name(f"{temp_path.stem}-{index + 1}{temp_path.suffix}")
        used_paths.add(os.fspath(temp_path))
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(sysml_text, encoding="utf-8")
        temp_paths.append(os.fspath(temp_path))
    return basenames, temp_paths


def _build_environment_from_models(
    environment_models: list[tuple[str, str]] | None,
) -> Any:
    if not environment_models:
        return None

    with tempfile.TemporaryDirectory(prefix="flexo_syside_env_") as env_dir:
        _basenames, env_paths = _write_models_to_temp_paths(env_dir, environment_models)
        model, diagnostics = syside.try_load_model(env_paths)
        _assert_no_diagnostic_errors(
            diagnostics,
            context="environment model load",
            input_names=[name for name, _text in environment_models],
            staged_paths=env_paths,
        )
        return model.to_environment() if model is not None and hasattr(model, "to_environment") else None


def _format_diagnostic_entry(diag: Any) -> str:
    message = str(getattr(diag, "message", None) or getattr(diag, "text", None) or diag).strip()
    severity = getattr(diag, "severity", None) or getattr(diag, "level", None)
    severity_name = str(getattr(severity, "name", severity) or "unknown").lower()

    file_path = str(
        getattr(diag, "file", None)
        or getattr(getattr(diag, "location", None), "file", None)
        or getattr(getattr(diag, "location", None), "resource", None)
        or ""
    ).strip()
    line = getattr(diag, "line", None)
    col = getattr(diag, "col", None)

    location = file_path
    if line is not None:
        location = f"{location}:{line}" if location else str(line)
        if col is not None:
            location = f"{location}:{col}"
    if location:
        return f"[{severity_name}] {location} {message}".strip()
    return f"[{severity_name}] {message}".strip()


def _assert_no_diagnostic_errors(
    diagnostics: Any,
    *,
    context: str,
    input_names: list[str],
    staged_paths: list[str],
) -> None:
    if not diagnostics.contains_errors(warnings_as_errors=True):
        return

    all_diagnostics = list(getattr(diagnostics, "all", []) or [])
    lines = [
        f"flexo_syside_lib { _PACKAGE_VERSION } {context} failed with {len(all_diagnostics)} diagnostic(s)",
        f"input_names={input_names}",
        f"staged_paths={staged_paths}",
    ]
    if not all_diagnostics:
        lines.append("diagnostics=[]")
    else:
        lines.append("diagnostics:")
        lines.extend(f"- {_format_diagnostic_entry(diag)}" for diag in all_diagnostics[:20])
        if len(all_diagnostics) > 20:
            lines.append(f"- ... {len(all_diagnostics) - 20} more diagnostic(s)")
    raise AssertionError("\n".join(lines))


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
    _assert_no_diagnostic_errors(
        diagnostics,
        context="single-file model load",
        input_names=[Path(sysml_file_path).name],
        staged_paths=[sysml_file_path],
    )

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
    _assert_no_diagnostic_errors(
        diagnostics,
        context="multi-file model load",
        input_names=[Path(sysml_file_path).name for sysml_file_path in sysml_file_paths],
        staged_paths=sysml_file_paths,
    )

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


def convert_sysml_models_textual_to_json(
    sysml_models: list[tuple[str, str]],
    json_out_path: str | None = None,
    minimal: bool = False,
    environment_models: list[tuple[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not sysml_models:
        raise ValueError("sysml_models must not be empty")

    with tempfile.TemporaryDirectory(prefix="flexo_syside_models_") as tmp_dir:
        basenames, temp_paths = _write_models_to_temp_paths(tmp_dir, sysml_models)
        environment = _build_environment_from_models(environment_models)
        model, diagnostics = syside.try_load_model(temp_paths, environment=environment)
        _assert_no_diagnostic_errors(
            diagnostics,
            context="textual models load",
            input_names=[name for name, _text in sysml_models],
            staged_paths=temp_paths,
        )

        json_string = model_to_json(
            model,
            minimal,
            root_namespace_names=basenames,
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
    _assert_no_diagnostic_errors(
        diagnostics,
        context="string model load",
        input_names=["<string>"],
        staged_paths=["<memory>"],
    )

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
