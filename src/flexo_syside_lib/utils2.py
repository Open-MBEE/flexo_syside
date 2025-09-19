import json
from typing import Any, Dict, List, Set, Tuple
import re
import difflib


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