import syside
from pathlib import Path


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
        clean_element = _remove_uri_fields(element_no_none.copy())

        # Add identity
        identity = {"@id": clean_element.get("@id")} if "@id" in clean_element else {}

        transformed.append({
            "payload": clean_element,
            "identity": identity
        })

    return transformed

def _make_root_namespace_first(json_str: str) -> str:
    obj = json.loads(json_str)
    found_root_namespace = None
    for i, element in enumerate(obj):
        if element["@type"] == "Namespace" and "owningRelationship" not in element:
            assert found_root_namespace is None
            found_root_namespace = i
    if found_root_namespace is not None:
        obj.insert(0, obj.pop(found_root_namespace))
    else:
        raise ValueError("No root namespace found")
    return json.dumps(obj)

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

    return json_string

def _create_json_writer() -> syside.JsonStringWriter:
    json_options = syside.JsonStringOptions()
    json_options.include_cross_ref_uris = False
    json_options.indent = False
    writer = syside.JsonStringWriter(json_options)
    return writer

def _create_serialization_options() -> syside.SerializationOptions:
    options = syside.SerializationOptions()
    options = options.with_options(
        use_standard_names=True,
        include_derived=True,
        include_redefined=True,
        include_default=False,
        include_optional=False,
        include_implied=True,
    )
    options.fail_action = syside.FailAction.Ignore
    
    return options

def convert_sysml_file_textual_to_json(sysml_file_path:str, json_out_path:str = None, minimal:bool=False) -> str:
    # load sysml textual notation and create json dump
    (model, diagnostics) = syside.try_load_model([sysml_file_path])

    # Only errors cause an exception. SysIDE may also report warnings and
    # informational messages
    assert not diagnostics.contains_errors(warnings_as_errors=True)

    json_string = _model_to_json(model, minimal)
    if json_out_path is not None:
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(json_string)

    data = json.loads(json_string)
    return _wrap_elements_as_payload(data)

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
    return _wrap_elements_as_payload(data)

def convert_json_to_sysml_textual(json_flexo:str, sysml_out_path:str = None, debug:bool=False) ->str:
    MODEL_FILE_PATH = sysml_out_path
    if sysml_out_path is None:
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / "import.sysml"
    # The deserialized model will be stored in a document with MODEL_PATH path.
    # The MODEL_PATH does not necessarily need to exist on the local file system.
    # gives a valid file URI regardless of platform
    MODEL_PATH = MODEL_FILE_PATH.as_uri()

    # Normalize input to a JSON string (no double-encoding!)
    if isinstance(json_flexo, (dict, list)):
        json_in = json.dumps(json_flexo, ensure_ascii=False)
    elif isinstance(json_flexo, str):
        json_in = json_flexo
    else:
        raise TypeError(f"json_flexo must be dict/list/str, got {type(json_flexo).__name__}")

    # 1) Clean dangling refs & incomplete relationships → JSON string out
    json_clean = clean_sysml_json_for_syside(json_in, preserve_refs_with_uri=True, debug=debug)

    # 2) Ensure root namespace is first (this function expects a JSON string)
    json_import = _make_root_namespace_first(json_clean)

    # 3) Deserialize
    try:
        deserialized_model, model_doc = syside.json.loads(json_import, MODEL_PATH)
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

            print("Deserialization failed. Diagnostic report:")
            print_serde_report(report)
        else:
            # Not a syside deserialization error; re-raise (or handle differently)
            raise

    # Create an environment to have access to stdlib docs
    # If you have exported the stdlib to JSON as well, you do not need this
    # environment. However, currently we have a bug that prevents us from
    # loading the stdlib from JSON.
    default_env = syside.Environment.get_default()
    stdlib_docs = default_env.documents

    # Create an IdMap that will be used to link deserialized models together
    map = syside.IdMap()

    # Add stdlib docs to the IdMap
    # This part is not needed if you have exported the stdlib to JSON as well.
    for doc in stdlib_docs:
        with doc.lock() as locked:
            map.insert_or_assign(locked)

    # Add deserialized JSON docs to the map
    with model_doc.lock() as locked:
        map.insert_or_assign(locked)

    deserialized_model.link(map)

    # Save the deserialized model to a file
    root_namespace = deserialized_model.document.root_node
    printer_cfg = syside.PrinterConfig(line_width=80, tab_width=2)
    printer = syside.ModelPrinter.sysml()
    sysml_text = syside.pprint(root_namespace, printer, printer_cfg)

    return sysml_text, deserialized_model

