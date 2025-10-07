import syside
from pathlib import Path
from datetime import datetime, timezone

from sysmlv2_client import SysMLV2Client, SysMLV2Error, SysMLV2NotFoundError
from .utils import clean_sysml_json_for_syside
from .utils2 import print_serde_report
import json 
from pprint import pprint

from typing import List, Dict, Any
import pathlib
import os
import ast

# utils_syside.py
from typing import Any

def _replace_none_with_empty(obj):
    if isinstance(obj, dict):
        return {k: _replace_none_with_empty(v) if v is not None else "" for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_none_with_empty(x) for x in obj]
    else:
        return obj


def _remove_uri_fields(obj: Any) -> Any:
    """Recursively remove all @uri fields from a nested JSON-like structure."""
    if isinstance(obj, dict):
        return {k: _remove_uri_fields(v) for k, v in obj.items() if k != "@uri"}
    elif isinstance(obj, list):
        return [_remove_uri_fields(item) for item in obj]
    return obj

def _wrap_elements_as_payload(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform elements into the target format:
    - Wrap each element in 'payload'
    - Add 'identity' with '@id'
    - Remove all '@uri' keys
    - Optionally prefill common fields
    """
    transformed = []

    for element in data:
        # some elements have null as value, such as qualified_name. Flexo has currently a bug that causes an exception
        element_no_none = _replace_none_with_empty(element)
        clean_element = element_no_none

        # Add identity
        identity = {"@id": clean_element.get("@id")} if "@id" in clean_element else {}
        clean_element["identity"] = identity

        transformed.append({"payload": clean_element})

    return transformed

def _make_root_namespace_first(json_str: str) -> str:
    obj = json.loads(json_str)

    found_root_namespace = None
    timestamp = datetime.fromisoformat("1970-01-01T12:00:00+00:00")

    def empty_to_none_and_search(element, index=None):
        nonlocal found_root_namespace, timestamp

        # Replace empty strings with None recursively
        if isinstance(element, dict):
            # detect root namespace while walking
            if element.get("@type") == "Namespace" and "owningRelationship" not in element:
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
                        pass  # ignore malformed dates

            return {k: empty_to_none_and_search(v) for k, v in element.items()}

        elif isinstance(element, list):
            return [empty_to_none_and_search(v, i) for i, v in enumerate(element)]

        elif element == "":
            return None

        else:
            return element

    obj = [empty_to_none_and_search(e, i) for i, e in enumerate(obj)]

    if found_root_namespace is not None:
        obj.insert(0, obj.pop(found_root_namespace))
    else:
        raise ValueError("No root namespace found")

    return json.dumps(obj)


def _create_json_writer() -> syside.JsonStringWriter:
    json_options = syside.JsonStringOptions()
    json_options.include_cross_ref_uris = False
    json_options.indent = False
    writer = syside.JsonStringWriter(json_options)
    return writer

def _create_serialization_options() -> syside.SerializationOptions:
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

def _model_to_json (model:syside.Model, minimal:bool=False):
    # Export the model to JSON
    assert len(model.user_docs) == 1

    writer = _create_json_writer()
    if minimal:
        options = syside.SerializationOptions.minimal()
    else:
        options =_create_serialization_options()

    with model.user_docs[0].lock() as locked:
        syside.serialize(locked.root_node, writer, options)
        json_string = writer.result

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    obj = json.loads(json_string)
    for element in obj:
        if element.get("@type") == "Namespace" and "owningRelationship" not in element:
            element["qualifiedName"] = now_str   # set the value here
            #print(element)
            break
            
    return json.dumps(obj, indent=2)


def convert_sysml_file_textual_to_json(sysml_file_path:str, json_out_path:str = None, minimal:bool=False) -> str:
    # load sysml textual notation and create json dump
    model, diagnostics = syside.try_load_model([sysml_file_path])

    # Only errors cause an exception. SysIDE may also report warnings and
    # informational messages
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = _model_to_json(model, minimal)
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)

    data = json.loads(json_string)
    return _wrap_elements_as_payload(data), json_string

def convert_sysml_string_textual_to_json(sysml_model_string:str, json_out_path:str = None, minimal:bool=False) -> str:
    model, diagnostics = syside.load_model(sysml_source=sysml_model_string)

    # Only errors cause an exception. SysIDE may also report warnings and
    # informational messages
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = _model_to_json(model, minimal)
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)
    
    data = json.loads(json_string)
    return _wrap_elements_as_payload(data), json_string

import warnings

def convert_json_to_sysml_textual(json_flexo:str, debug:bool=False):
    captured_warnings = []

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")  # capture all warnings

        # Normalize input to a JSON string (no double-encoding!)
        if isinstance(json_flexo, (dict, list)):
            json_in = json.dumps(json_flexo, ensure_ascii=False)
        elif isinstance(json_flexo, str):
            json_in = json_flexo
        else:
            raise TypeError(f"json_flexo must be dict/list/str, got {type(json_flexo).__name__}")

        # 1) Clean dangling refs & incomplete relationships → JSON string out
        #json_clean = clean_sysml_json_for_syside(json_in, preserve_refs_with_uri=True, debug=debug)

        # 2) Ensure root namespace is first (this function expects a JSON string)
        json_import = _make_root_namespace_first(json_in)

        # 3) Deserialize
        try:
            deserialized_model, _ = syside.json.loads(json_import, "memory:///import.sysml")
        except Exception as exc:
            # Try to catch the specific syside error type first
            try:
                from syside.json import DeserializationError  # sometimes exported here
            except Exception:
                try:
                    from syside.core import DeserializationError  # or here, depending on version
                except Exception:
                    DeserializationError = type(None)  # fallback so isinstance won't match

            if isinstance(exc, DeserializationError):
                # Many versions set these as attributes...
                report = getattr(exc, "report", None)
                model = getattr(exc, "model", None)

                # ...but they are always present in .args as a fallback
                if report is None and getattr(exc, "args", None):
                    if len(exc.args) >= 2:
                        model = exc.args[0]
                        report = exc.args[1]

                captured_warnings.append(f"Deserialization failed: {report}")
                return None, captured_warnings
            else:
                # Not a syside deserialization error; re-raise (or handle differently)
                raise


        # Collect warnings from this phase
        for w in wlist:
            captured_warnings.append(str(w.message))

    # Create an IdMap that will be used to link deserialized models together
    map = syside.IdMap()

    # Create an environment to have access to stdlib docs
    # If you have exported the stdlib to JSON as well, you do not need this
    # environment. However, currently we have a bug that prevents us from
    # loading the stdlib from JSON.
    for mutex in syside.Environment.get_default().documents:
        with mutex.lock() as dep:
            map.insert_or_assign(dep)

    try:
        report, success = deserialized_model.link(map)
    except Exception as exc:
        try:
            from syside.core import DeserializationError  # or here, depending on version
        except Exception:
            DeserializationError = type(None)  # fallback so isinstance won't match

        if isinstance(exc, DeserializationError):
            # Many versions set these as attributes...
            report = getattr(exc, "report", None)
            model = getattr(exc, "model", None)

            # ...but they are always present in .args as a fallback
            if report is None and getattr(exc, "args", None):
                if len(exc.args) >= 2:
                    model = exc.args[0]
                    report = exc.args[1]

            print("Deserialization failed. Diagnostic report:")
            print_serde_report(report)
        else:
            # Not a syside deserialization error; re-raise (or handle differently)
            raise
        
#    assert success, str(report.messages)
 
    # Save the deserialized model to a file
    root_namespace = deserialized_model.document.root_node
    printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
    printer = syside.ModelPrinter.sysml()
    sysml_text = syside.pprint(root_namespace, printer, printer_cfg)

    return (sysml_text, deserialized_model), captured_warnings

