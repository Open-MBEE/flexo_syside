import json
from typing import Any, Dict, List, Set, Tuple
import re
import difflib

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