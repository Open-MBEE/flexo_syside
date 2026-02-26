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

        transformed.append({
            "payload": clean_element,
            "identity": identity
        })

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
        # with open("debug.json", "w", encoding="utf-8") as f:
        #     f.write(json_import)

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

def _children_iter(elem):
    children = getattr(elem, "owned_elements", None)
    if not children:
        return []
    try:
        return list(children)
    except TypeError:
        out = []
        children.for_each(lambda e: out.append(e))
        return out

def find_partusage_by_definition(elem, defining_part_name: str, usage_name: str | None = None):
    """
    Return the FIRST/HIGHEST PartUsage whose PartDefinition name matches `defining_part_name`
    and optionally whose own PartUsage.name matches `usage_name`.

    Parameters:
      elem                : SysML AST root node for traversal.
      defining_part_name  : The PartDefinition.name to match (e.g., "Component").
      usage_name          : Optional PartUsage.name to filter on (e.g., "rootmodule").
    """
    def has_matching_def(node):
        """Return True if this PartUsage has a PartDefinition with the given name."""
        if not node.try_cast(syside.PartUsage):
            return False
        try:
            for pd in node.part_definitions:
                if getattr(pd, "name", None) == defining_part_name:
                    return True
        except Exception:
            pass
        return False

    def matches_usage_name(node):
        """Optional check that PartUsage.name matches the filter (if provided)."""
        if usage_name is None:
            return True
        return getattr(node, "name", None) == usage_name

    def dfs(node):
        is_part = bool(node.try_cast(syside.PartUsage))
        here_matches = is_part and has_matching_def(node) and matches_usage_name(node)

        subtree_has_match = here_matches
        child_found = None

        for ch in _children_iter(node):
            found, child_has = dfs(ch)
            subtree_has_match = subtree_has_match or child_has or (found is not None)
            if found is not None and child_found is None:
                child_found = found

        if here_matches:
            return node, True  # this node satisfies the filters, return it

        if child_found is not None:
            return child_found, True

        return None, subtree_has_match

    found, _ = dfs(elem)
    return found

def find_component_partusage(elem):
    """
    Find the FIRST/HIGHEST PartUsage whose PartDefinition name is "Component"
    AND that PartUsage has at least one DIRECT child that is a PartUsage.
    Return that DIRECT child (the first direct PartUsage child encountered).
    Works with SysIDE's Python SysMLv2 API.
    """

    def is_component_partusage(node) -> bool:
        pu = node.try_cast(syside.PartUsage)
        if not pu:
            return False
        try:
            for pd in pu.part_definitions:
                if getattr(pd, "name", None) == "Component":
                    return True
        except Exception:
            # If we cannot inspect part_definitions (API inconsistency or other error),
            # conservatively treat this node as not being a Component.
            pass
        return False

    def first_direct_partusage_child(node):
        for ch in _children_iter(node):
            pu_child = ch.try_cast(syside.PartUsage)
            if pu_child:
                return ch  # return the direct child node itself
        return None

    def dfs(node):
        # Pre-order: highest match wins
        if is_component_partusage(node):
            direct_child = first_direct_partusage_child(node)
            if direct_child is not None:
                return direct_child

        for ch in _children_iter(node):
            found = dfs(ch)
            if found is not None:
                return found

        return None

    return dfs(elem)

def walk_ownership_tree(element, level: int = 0) -> None:
    """
    Prints out all elements in a model in a tree-like format, where child
    elements appear indented under their parent elements. For example:

    Parent
      Child1
      Child2
        Grandchild

    Args:
        element: The model element to start printing from (syside.Element)
        level: How many levels to indent (increases for nested elements)
    """

    if element.try_cast(syside.AttributeUsage):
        attr = element.cast(syside.AttributeUsage)
        expression_a1 = next(iter(attr.owned_elements), None)
        if expression_a1 is not None and isinstance(expression_a1, syside.LiteralRational):
            print("  " * level, f"{attr.name} = {expression_a1.value}")
        elif expression_a1 is not None and isinstance(expression_a1, syside.LiteralInteger):
            print("  " * level, f"{attr.name} = {expression_a1.value}")
        else:
            print("  " * level, f"{attr.name}", type(expression_a1))
    elif element.name is not None:
        print("  " * level, element.name)
    # Recursively call walk_ownership_tree() for each owned element
    # (child element).
    element.owned_elements.for_each(
        lambda owned_element: walk_ownership_tree(owned_element, level + 1)
    )

def find_part_by_name(element, name: str, part_level: int = 0):
    """
    Depth-first search for a PartUsage by name.
    Prints the part hierarchy as it goes and returns the first match.
    
    Args:
        element: The model element to search from (syside.Element)
        name: The part name to find
        part_level: Current indentation level for printing
    """

    part = element.try_cast(syside.PartUsage)
    if part:
        print("  " * part_level + part.name)
        if part.name == name:
            return part
        part_level += 1  # indent children of parts

    # Iterate children in a way that allows early return
    children = getattr(element, "owned_elements", None)
    if not children:
        return None

    # Try to iterate directly; if not iterable, materialize via for_each
    try:
        iterator = iter(children)
    except TypeError:
        lst = []
        children.for_each(lambda e: lst.append(e))
        iterator = iter(lst)

    for child in iterator:
        found = find_part_by_name(child, name, part_level)
        if found is not None:
            return found

    return None

def find_expression_attribute_values(element, level=0):
    """
    Find and evaluate expression attribute values in a SysML model element.
    Follows the CTO-provided logic. Expects 'syside' to be importable.
    """
    try:
        import syside  # type: ignore
    except Exception:
        # Defer to evaluate_sysml_expressions' import path resolution
        try:
            from flexo_syside_lib import syside  # type: ignore
        except Exception:
            from flexo_syside_lib.core import syside  # type: ignore

    if hasattr(element, "try_cast") and element.try_cast(syside.AttributeUsage):
        attr = element.cast(syside.AttributeUsage)
        expression_a1 = None
        try:
            expression_a1 = next(iter(attr.owned_elements), None)
        except Exception:
            expression_a1 = None
        if expression_a1 is not None and isinstance(expression_a1, syside.Expression):
            compiler = syside.Compiler()
            result, report = compiler.evaluate(expression_a1)
            assert not report.fatal, report.diagnostics
            name = (
                getattr(attr, "qualified_name", None)
                or getattr(attr, "declared_name", None)
                or "<unnamed>"
            )
            print(f"{name}: {result}")

    try:
        element.owned_elements.for_each(
            lambda owned_element: find_expression_attribute_values(
                owned_element, level + 1
            )
        )
    except Exception:
        # If owned_elements is not an iterable with for_each, try a generic iteration
        try:
            for owned_element in element.owned_elements:
                find_expression_attribute_values(owned_element, level + 1)
        except Exception:
            pass
