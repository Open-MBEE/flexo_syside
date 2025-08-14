import syside
from pathlib import Path
import re
import difflib

from sysmlv2_client import SysMLV2Client, SysMLV2Error, SysMLV2NotFoundError
import json 
from pprint import pprint

from typing import List, Dict, Any
import pathlib
import os
import ast

# utils_syside.py
from typing import Any

def print_serde_report(report: Any) -> None:
    """Pretty-print a syside SerdeReport (best-effort, tolerant of attribute differences)."""
    if report is None:
        print("No report attached.")
        return

    # Try common container attributes
    messages = getattr(report, "messages", None) or getattr(report, "diagnostics", None) or []

    # If the report knows how to stringify itself, show it first.
    to_string = getattr(report, "to_string", None)
    if callable(to_string):
        print(to_string())

    if not messages:
        # Fallback to raw repr if no messages list is found
        print(repr(report))
        return

    for i, msg in enumerate(messages, 1):
        sev = getattr(msg, "severity", None)
        sev_name = getattr(sev, "name", None) or str(sev) or "UNKNOWN"

        text = (
            getattr(msg, "message", None)
            or getattr(msg, "text", None)
            or str(msg)
        )

        code = getattr(msg, "code", None)

        # Location best-effort
        loc = getattr(msg, "location", None) or getattr(msg, "range", None) or getattr(msg, "span", None)
        where = ""
        if loc is not None:
            start = getattr(loc, "start", None) or getattr(loc, "begin", None)
            if start is not None:
                line = getattr(start, "line", None)
                col = getattr(start, "column", None)
                if line is not None and col is not None:
                    where = f" @ {line}:{col}"

        # Maybe the element/name is present
        element = getattr(msg, "element", None)
        el_name = getattr(element, "name", None)
        if el_name:
            where += f" (element: {el_name})"

        print(f"{i:02d}. [{sev_name}] {text}{f' (code {code})' if code else ''}{where}")


import json
from typing import Any, Dict, List, Set, Tuple

def clean_sysml_json_for_syside(
    json_text: str,
    *,
    allow_python_literals: bool = False,
    indent: int = 2,
    preserve_refs_with_uri: bool = True,
) -> str:
    """
    Clean a SysMLv2 JSON document for syside deserialization:
      1) Remove dangling thin references (objects that only have @-prefixed keys with @id not defined).
      2) Drop relationship elements whose required related elements are missing after step 1.
      3) Iterate to a fixpoint.

    Relationship integrity rules (best-effort; extends as needed):
      - Subsetting: requires both ends, via either {"specific","general"} or {"subsettingFeature","subsettedFeature"}.
      - Specialization: requires {"specific","general"}.
      - FeatureTyping: requires {"typedFeature"} and at least one of {"type","general"}.
      - FeatureValue: requires {"featureWithValue","value"}.

    Parameters
    ----------
    json_text : str
        The input JSON string.
    allow_python_literals : bool
        If True, fallback to `ast.literal_eval` if JSON parsing fails.
    indent : int
        Indentation for the returned JSON. Use None for compact.
    preserve_refs_with_uri : bool
        If True, thin refs that include an '@uri' field are kept even if @id is missing
        (treat as external references).

    Returns
    -------
    str: cleaned JSON string.
    """
    # ---------- Parse ----------
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        if not allow_python_literals:
            raise
        import ast
        data = ast.literal_eval(json_text)

    # ---------- Normalize top-level ----------
    if isinstance(data, list):
        elements = data
        root_wrapper = None
    elif isinstance(data, dict) and isinstance(data.get("elements"), list):
        elements = data["elements"]
        root_wrapper = data  # keep original structure
    elif isinstance(data, dict):
        elements = [data]
        root_wrapper = None
    else:
        # Not a recognized form; return as-is
        return json.dumps(data, ensure_ascii=False, indent=indent)

    # ---------- Helpers ----------
    def build_defined_ids(els: List[Dict[str, Any]]) -> Set[str]:
        s: Set[str] = set()
        for el in els:
            if isinstance(el, dict):
                _id = el.get("@id")
                if isinstance(_id, str):
                    s.add(_id)
        return s

    def is_thin_ref(obj: Any) -> bool:
        if not isinstance(obj, dict):
            return False
        if "@id" not in obj:
            return False
        if "@type" in obj:
            return False
        # only @-prefixed keys allowed
        for k in obj:
            if not k.startswith("@"):
                return False
        return True

    def has_uri(obj: Any) -> bool:
        return isinstance(obj, dict) and ("@uri" in obj)

    DROP = object()

    def drop_thin_dangling_refs(obj: Any, defined_ids: Set[str]) -> Any:
        """Recursively remove thin references that point to undefined IDs."""
        if is_thin_ref(obj):
            ref_id = obj.get("@id")
            if ref_id not in defined_ids:
                # Optionally keep external references that carry @uri
                if preserve_refs_with_uri and has_uri(obj):
                    return obj
                return DROP
            return obj

        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                cv = drop_thin_dangling_refs(v, defined_ids)
                if cv is DROP:
                    # drop the field entirely
                    continue
                cleaned[k] = cv
            return cleaned

        if isinstance(obj, list):
            out = []
            for item in obj:
                ci = drop_thin_dangling_refs(item, defined_ids)
                if ci is DROP:
                    continue
                out.append(ci)
            return out

        return obj

    # Relationship validation: for a given element (post thin-ref cleanup), decide whether to keep it.
    def is_relationship_and_incomplete(el: Dict[str, Any]) -> bool:
        t = el.get("@type")

        def has_ref_key(name: str) -> bool:
            v = el.get(name)
            return isinstance(v, dict) and "@id" in v

        # Subsetting: need both ends (either specific/general OR subsettingFeature/subsettedFeature)
        if t == "Subsetting":
            a = has_ref_key("specific") and has_ref_key("general")
            b = has_ref_key("subsettingFeature") and has_ref_key("subsettedFeature")
            return not (a or b)

        # Specialization: specific + general
        if t == "Specialization":
            return not (has_ref_key("specific") and has_ref_key("general"))

        # FeatureTyping: typedFeature + (type OR general)
        if t == "FeatureTyping":
            has_typed = has_ref_key("typedFeature")
            has_type_or_gen = has_ref_key("type") or has_ref_key("general")
            return not (has_typed and has_type_or_gen)

        # FeatureValue: featureWithValue + value
        if t == "FeatureValue":
            return not (has_ref_key("featureWithValue") and has_ref_key("value"))

        # You can extend here with other relationship kinds that syside treats as “heritage”
        return False

    # ---------- Fixpoint cleanup ----------
    changed = True
    while changed:
        changed = False

        # 1) Compute defined IDs from current elements
        defined_ids = build_defined_ids(elements)

        # 2) Prune thin dangling refs everywhere
        new_elements: List[Dict[str, Any]] = []
        for el in elements:
            cleaned_el = drop_thin_dangling_refs(el, defined_ids)
            if cleaned_el is DROP:
                # shouldn't happen for top-level elements (they have @type), but be safe
                changed = True
                continue
            new_elements.append(cleaned_el)
        elements = new_elements

        # 3) Drop incomplete relationship elements (e.g., “Invalid heritage relationship - missing related element”)
        kept: List[Dict[str, Any]] = []
        for el in elements:
            if isinstance(el, dict) and is_relationship_and_incomplete(el):
                # Drop this element
                changed = True
                continue
            kept.append(el)
        elements = kept

        # If we dropped elements, the defined_ids set shrinks → loop to catch any newly dangling refs.

    # ---------- Rebuild root ----------
    if root_wrapper is None:
        result = elements if isinstance(data, list) else (elements[0] if len(elements) == 1 else elements)
    else:
        out = dict(root_wrapper)
        out["elements"] = elements
        result = out

    #return (result)
    return json.dumps(result, ensure_ascii=False, indent=indent)


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

def convert_json_to_sysml_textual(json_flexo:str, sysml_out_path:str = None) ->str:
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
    json_clean = clean_sysml_json_for_syside(json_in, preserve_refs_with_uri=True)

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

UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,)

def _to_text(x: Any) -> str:
    """Coerce input to text for comparison."""
    if isinstance(x, (dict, list)):
        # Raw JSON dump (unordered); canonicalize step comes later.
        return json.dumps(x, ensure_ascii=False)
    if isinstance(x, (bytes, bytearray)):
        return bytes(x).decode("utf-8", errors="replace")
    if isinstance(x, (str,)):
        return x
    # Path-like?
    try:
        p = Path(x)
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    # Fallback to stringification
    return str(x)

def _canonicalize_if_json(text: str) -> str:
    """If text is valid JSON, return a canonical JSON string (sorted keys, stable spacing)."""
    try:
        obj = json.loads(text)
    except Exception:
        return text  # not JSON; return as-is
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _scrub_uuids_text(s: str, replacement: str = "<UUID>") -> str:
    return UUID_RE.sub(replacement, s)

def compare_ignoring_uuids(
    a: Any,
    b: Any,
    *,
    replacement: str = "<UUID>",
    canonicalize_json: bool = True,
    normalize_ws: bool = True,
) -> bool:
    """Compare two blobs after removing UUIDs. Accepts str/dict/list/bytes/Path."""
    sa = _to_text(a)
    sb = _to_text(b)

    if canonicalize_json:
        sa = _canonicalize_if_json(sa)
        sb = _canonicalize_if_json(sb)

    sa = _scrub_uuids_text(sa, replacement)
    sb = _scrub_uuids_text(sb, replacement)

    if normalize_ws:
        sa = re.sub(r"\s+", " ", sa).strip()
        sb = re.sub(r"\s+", " ", sb).strip()

    return sa == sb

def diff_ignoring_uuids(
    a: Any,
    b: Any,
    *,
    replacement: str = "<UUID>",
    canonicalize_json: bool = True,
) -> str:
    """Unified diff after UUID scrubbing. Accepts str/dict/list/bytes/Path."""
    sa = _to_text(a)
    sb = _to_text(b)
    if canonicalize_json:
        sa = _canonicalize_if_json(sa)
        sb = _canonicalize_if_json(sb)
    sa = _scrub_uuids_text(sa, replacement)
    sb = _scrub_uuids_text(sb, replacement)
    return "\n".join(difflib.unified_diff(sa.splitlines(), sb.splitlines(), lineterm=""))