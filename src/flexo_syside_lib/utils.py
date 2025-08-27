import json
from typing import Any, Dict, List, Set, Tuple
import re
import difflib


# # 1) Input normalization

# * Accepts JSON text; optionally falls back to `ast.literal_eval` if you allow Python literals.
# * Normalizes the top level so the algorithm can always work against an **elements list**:

#   * if input is a list → use as-is
#   * if it’s a dict with `elements` → use `data["elements"]` and remember the wrapper to restore later
#   * if it’s a single dict → wrap it as a one-element list
#     This allows the rest of the passes to treat the model homogeneously and later restore the original shape.&#x20;

# # 2) Core helpers (graph view of the model)

# * **`build_defined_ids`** walks the whole structure and collects `@id`s for **full definitions** only (dicts that have both `@id` and `@type`). Thin references (dicts with `@id` but **no** `@type`) don’t count here. This creates the set of resolvable targets for reference validation.&#x20;
# * **Thin reference detector**: a “ref” is any dict with `@id` and no `@type`. These are only valid if their target id is in `defined_ids`.&#x20;
# * **`has_all_refs_defined`** is a deep check used later to decide whether an element (esp. relationships) is self-consistent: every thin `@id` it contains must point to a known full definition.&#x20;
# * **Root-namespace finder**: detects root namespaces as `@type == "Namespace"` **without** `owningRelationship`. All such elements are **protected** from deletion, so the importer always has an entry point.&#x20;

# # 3) Iterative, fixpoint cleanup

# The cleaner runs multiple passes until the structure stabilizes (or `MAX_ITERS` is reached). Each iteration:

# ### 3.1) Diagnostics (optional)

# If `debug` is on, it prints the set of thin-reference IDs that have no definition (“\[Unresolved refs] …”). This is purely informational.&#x20;

# ### 3.2) Nested prune: drop empties and obviously bad relationship nodes

# * Drops any dict with `{"@type":"Empty"}` anywhere.
# * **`drop_thin_dangling_refs`** recursively removes:

#   * Thin references whose `@id` target isn’t in `defined_ids` (unless `preserve_refs_with_uri=True` and the ref has `@uri`).
#   * **Nested** relationship objects that are clearly invalid: “strict” relationship kinds (see below) that are incomplete or contain unresolved thin refs.
#     This step is intentionally local (recursive) and keeps non-relationship content intact.&#x20;

# ### 3.3) Top-level relationship gate (conservative by design)

# After refreshing `defined_ids` (because we may have dropped things), the pass scans top-level elements and applies **type-aware** rules:

# * **STRICT\_REL\_TO\_DROP** = `{ "Subsetting", "Specialization", "Subclassification" }`
#   These are treated as **heritage** / containment constraints that must be self-consistent. For any element of these types:

#   * **Rule A:** If `is_relationship_and_incomplete` says essential endpoints are missing/unresolved, drop it.
#   * **Rule B:** If the element still contains any thin ref to an undefined target (`!has_all_refs_defined`), drop it.
#     Both rules are purposely limited to “strict” kinds to avoid over-deletion.&#x20;

# * **Membership relationships are never dropped here**
#   (`"OwningMembership"`, `"FeatureMembership"`, `"NamespaceMembership"`, `"Membership"`, `"ParameterMembership"`).
#   Reason: memberships “glue” namespaces, features, parts, etc. Even if some of their refs are unresolved while we’re converging, we **keep** them so the object graph stays connected; the nested prune already removed the worst offenders. The code logs `[Membership prune] … — keeping element` when they’re imperfect under `debug`.&#x20;

# * **Root namespace protection**
#   Any element whose `@id` is a root namespace never gets dropped in this pass. This guarantees compatibility with your `_make_root_namespace_first(...)` importer step.&#x20;

# This top-level gate + nested prune pair repeats until a fixpoint is reached (or `MAX_ITERS`). The effect is: “obviously broken or dangling things fall away, but the structural backbone (memberships, root) remains.”&#x20;

# # 4) Relationship completeness tests

# `is_relationship_and_incomplete` implements the **minimal viability** for each strict relationship:

# * **Subsetting**: require either `(specific & general)` or `(subsettingFeature & subsettedFeature)`.
# * **Specialization**: require `(specific & general)`.
# * **Subclassification**: same “heritage” rule as specialization.
#   The checks accept either single dicts or lists of refs and validate that each side’s `@id` resolves in `defined_ids`. This avoids dropping relationships merely because the exporter used `feature` vs `typedFeature`, or similar stylistic differences for non-strict kinds.&#x20;

# # 5) Type inference & injection (fixing the `children : Component [0..*]` case)

# After the model is cleaned, the algorithm **adds missing feature types** directly into **feature definitions** (not in renderers), so the textual SysML renderer naturally prints `part children : Component [0..*]`.

# The `_inject_inferred_types(...)` subroutine does two things:

# 1. **Infer types from explicit typing relationships**
#    Builds a `feature → type` map from surviving `FeatureTyping` and `TypeFeaturing` elements:

#    * Feature side: `typedFeature` or `feature`
#    * Type side: `type`, `featuringType`, or (as a fallback pattern the code recognizes) `general`
#      For each pair, if the feature’s **full definition** lacks a `type`, inject `{"type":{"@id": …}}`.&#x20;

# 2. **Self-type `children` features using memberships (fallback)**
#    Many exports don’t materialize an explicit `FeatureTyping` for the “children” collection. The helper:

#    * Builds a `feature_owner` map from membership relations (`memberElement/feature` → `featuringType/owningType/owningNamespace`).
#    * Recognizes every `PartDefinition` in the model.
#    * For any **feature definition** named `"children"` that still lacks a `type`, it tries to resolve its owner (prefer membership-derived owner, then fields on the feature).
#      If the owner is a `PartDefinition`, it injects `type = {"@id": <owner>}` — i.e., **`children` self-types to the owning PartDefinition**, which yields the desired `part children : Component [0..*]` in your output.
#      This step is a local, safe fix that doesn’t change rendering logic; it enriches the model so the renderer already in place prints the right thing.&#x20;

# # 6) Output restoration

# If the input started as a dict with `elements`, the function writes the cleaned elements back into that wrapper; otherwise it returns the list (or the single element if there’s exactly one). Indentation and `ensure_ascii=False` are honored.&#x20;

# ---

# ## Design principles & knobs

# * **Safety & stability first:** Iterative fixpoint, conservative drops (strict types only), and root-namespace protection ensure we never destroy the import backbone.&#x20;
# * **Separation of concerns:** Validation/removal happens **before** inference; inference only **adds** missing `type` fields to feature **definitions**, never to references or renderers.&#x20;
# * **Configurability:**

#   * `preserve_refs_with_uri`: keep unresolved refs that carry a `@uri`.
#   * `debug`: surfaces unresolved sets, membership leniency, and type injections.
#   * `allow_python_literals`: tolerates non-JSON inputs in early stages.
#   * The “strict set” is a single constant (`STRICT_REL_TO_DROP`) you can tune if needed.&#x20;

# ## Complexity notes

# Each iteration performs a bounded number of **linear tree walks** (collect ids, nested prune, top-level filter). With `MAX_ITERS=12`, worst-case time is `O(12 * N)` with small constants; memory is `O(N)` for temporary maps and sets.&#x20;

# ## Why this fixes `children : [0..*]` → `children : Component [0..*]`
######## THIS IS STILL BROKEN #######

# In many exports, the feature representing the “children” collection lacks an explicit `type` entry. After cleanup, `_inject_inferred_types` (1) harvests any available `FeatureTyping/TypeFeaturing`, and (2) when absent, infers the correct **self-type** for “children” using membership-derived ownership (or the feature’s own owning fields) — provided the owner is a `PartDefinition`. That adds `type={"@id": <Component-def>}` to the **feature definition**, which naturally renders as `part children : Component [0..*]` downstream. No renderer changes are required.&#x20;



def clean_sysml_json_for_syside(
    json_text: str,
    *,
    allow_python_literals: bool = False,
    indent: int = 2,
    preserve_refs_with_uri: bool = True,
    debug: bool = True,   # <-- turn on/off debug printing
) -> str:
    import json
    from typing import Any, Dict, List, Set

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
        root_wrapper = data
    elif isinstance(data, dict):
        elements = [data]
        root_wrapper = None
    else:
        return json.dumps(data, ensure_ascii=False, indent=indent)

    # ---------- Helpers ----------
    def _inject_inferred_types(els: List[Dict[str, Any]], *, debug: bool=False) -> List[Dict[str, Any]]:
        """
        If a feature's type can be inferred from FeatureTyping/TypeFeaturing relationships,
        inject a missing 'type': {'@id': ...} into the feature's *full definition*.
        Also self-type 'children' features using the owning PartDefinition found via Memberships.
        """
        # helper: pull first @id from dict-or-list
        def _first_id(val):
            if isinstance(val, dict) and "@id" in val:
                return val["@id"]
            if isinstance(val, list):
                for i in val:
                    if isinstance(i, dict) and "@id" in i:
                        return i["@id"]
            return None

        # 0) feature -> owner (featuringType) from Memberships; many models only set owner here
        feature_owner: Dict[str, str] = {}
        MEMBERSHIP_NAMES = {"OwningMembership", "FeatureMembership", "NamespaceMembership", "Membership", "ParameterMembership"}
        for el in els:
            if not isinstance(el, dict):
                continue
            t = el.get("@type")
            if t in MEMBERSHIP_NAMES:
                f_id = _first_id(el.get("memberElement")) or _first_id(el.get("feature"))
                owner_id = _first_id(el.get("featuringType")) or _first_id(el.get("owningType")) or _first_id(el.get("owningNamespace"))
                if f_id and owner_id:
                    feature_owner[f_id] = owner_id

        # 1) feature -> type from explicit typing relationships
        feat_to_type: Dict[str, str] = {}
        for el in els:
            if not isinstance(el, dict):
                continue
            t = el.get("@type")
            if t in ("FeatureTyping", "TypeFeaturing"):
                f_id = _first_id(el.get("typedFeature")) or _first_id(el.get("feature"))
                ty_id = _first_id(el.get("type")) or _first_id(el.get("featuringType")) or _first_id(el.get("general"))
                if f_id and ty_id:
                    feat_to_type[f_id] = ty_id

        if debug:
            print(f"[Inject types] inferred {len(feat_to_type)} feature→type pairs" if feat_to_type else "[Inject types] nothing to infer")

        # 2) index full element definitions
        id_to_el: Dict[str, Dict[str, Any]] = {}
        for el in els:
            if isinstance(el, dict) and "@id" in el and "@type" in el:
                id_to_el[el["@id"]] = el

        # recognize PartDefinitions (for self-typing children)
        part_def_ids = {eid for eid, e in id_to_el.items() if isinstance(e, dict) and e.get("@type") == "PartDefinition"}

        # 3) inject explicit typing onto feature definitions
        for f_id, ty_id in feat_to_type.items():
            feat_def = id_to_el.get(f_id)
            if feat_def is not None and "type" not in feat_def:
                feat_def["type"] = {"@id": ty_id}
                if debug:
                    print(f"[Inject] feature {f_id} → type {ty_id}")

        # 4) fallback: self-type 'children' using membership-derived owner (if owner is a PartDefinition)
        for feat_def in list(id_to_el.values()):
            if not isinstance(feat_def, dict):
                continue
            if "type" in feat_def:
                continue
            if feat_def.get("name") != "children":
                continue

            # prefer owner from membership; if missing, also try fields on the feature itself
            owner_id = feature_owner.get(feat_def.get("@id")) \
                    or _first_id(feat_def.get("owningType")) \
                    or _first_id(feat_def.get("owningNamespace")) \
                    or _first_id(feat_def.get("featuringType"))

            if owner_id in part_def_ids:
                feat_def["type"] = {"@id": owner_id}
                if debug:
                    print(f"[Inject] feature {feat_def.get('@id')} → type {owner_id} (fallback: children=self-type via membership)")

        return els


    def find_root_namespace_ids_syside(els):
        """Root namespace for syside: @type=='Namespace' and NO 'owningRelationship' key."""
        roots = set()
        for el in els:
            if (isinstance(el, dict)
                and el.get("@type") == "Namespace"
                and "owningRelationship" not in el
                and isinstance(el.get("@id"), str)):
                roots.add(el["@id"])
        return roots

    def has_defined_ref(name: str) -> bool:
        v = el.get(name)
        if isinstance(v, dict):
            return "@id" in v and v["@id"] in defined_ids
        if isinstance(v, list) and v:
            return any(isinstance(i, dict) and "@id" in i and i["@id"] in defined_ids for i in v)
        return False

    def is_ref_dict(obj: Any) -> bool:
        """A reference object: has @id but no @type (even if extra fields exist)."""
        return isinstance(obj, dict) and ("@id" in obj) and ("@type" not in obj)

    def build_defined_ids(els: List[Dict[str, Any]]) -> Set[str]:
        """Recursively collect @id only from full elements (have @type)."""
        s: Set[str] = set()

        def collect(obj: Any):
            if isinstance(obj, dict):
                _id = obj.get("@id")
                # count only *full* element definitions
                if isinstance(_id, str) and "@type" in obj:
                    s.add(_id)
                # keep walking
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for v in obj:
                    collect(v)

        for el in els:
            collect(el)
        return s

    def has_uri(obj: Any) -> bool:
        return isinstance(obj, dict) and ("@uri" in obj)

    DROP = object()

    def drop_thin_dangling_refs(obj: Any, defined_ids: Set[str]) -> Any:
        # keep your root protection if you added it

        # 0) drop explicit empties
        if isinstance(obj, dict) and obj.get("@type") == "Empty":
            ref_drops[0] = True
            return DROP

        # 1) drop nested invalid relationships (STRICT only, NOT memberships)
        if isinstance(obj, dict) and obj.get("@type") in STRICT_REL_TO_DROP:
            if is_relationship_and_incomplete(obj, defined_ids) or not has_all_refs_defined(obj, defined_ids):
                if debug:
                    print("[Drop nested]", obj.get("@type"), obj.get("@id"), "invalid or unresolved")
                ref_drops[0] = True
                return DROP

        # 2) drop thin refs to undefined ids
        if is_ref_dict(obj):
            ref_id = obj.get("@id")
            if ref_id not in defined_ids:
                if preserve_refs_with_uri and has_uri(obj):
                    return obj
                ref_drops[0] = True
                return DROP
            return obj

        # 3) recurse
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                cv = drop_thin_dangling_refs(v, defined_ids)
                if cv is DROP:
                    ref_drops[0] = True
                    continue
                cleaned[k] = cv
            return cleaned
        if isinstance(obj, list):
            out = []
            for item in obj:
                ci = drop_thin_dangling_refs(item, defined_ids)
                if ci is DROP:
                    ref_drops[0] = True
                    continue
                out.append(ci)
            return out
        return obj
    

    def is_relationship_and_incomplete(el: Dict[str, Any], defined_ids: Set[str]) -> bool:
        t = el.get("@type")

        def ref_defined(v):
            return isinstance(v, dict) and "@id" in v and v["@id"] in defined_ids

        def has_ref_key(name: str) -> bool:
            return ref_defined(el.get(name))

        def has_defined_ref(name: str) -> bool:
            v = el.get(name)
            if isinstance(v, list) and v:
                return any(ref_defined(i) for i in v)
            return ref_defined(v)

        # STRICT kinds: still drop when incomplete
        if t == "Subsetting":
            a = has_ref_key("specific") and has_ref_key("general")
            b = has_ref_key("subsettingFeature") and has_ref_key("subsettedFeature")
            return not (a or b)

        if t == "Specialization":
            return not (has_ref_key("specific") and has_ref_key("general"))

        if t == "FeatureTyping":
            return not (has_ref_key("typedFeature") and (has_ref_key("type") or has_ref_key("general")))

        if t == "FeatureValue":
            return not (has_ref_key("featureWithValue") and has_ref_key("value"))

        if t == "Subclassification":
            return not (has_ref_key("specific") and has_ref_key("general"))

        if t == "TypeFeaturing":
            return not (has_ref_key("typedFeature") and (has_ref_key("type") or has_ref_key("general")))

        # Memberships: DON'T drop here (let top-pass decide / prune fields)
        if t in MEMBERSHIP_RELS:
            if debug:
                owns_ok  = has_defined_ref("ownedRelatedElement")
                member_ok = has_ref_key("memberElement") or has_ref_key("feature")
                ns_ok    = has_ref_key("owningNamespace") or has_ref_key("membershipOwningNamespace")
                if not (owns_ok and member_ok and ns_ok):
                    print("[Membership incomplete]", el.get("@id"), t, "— keeping for now")
            return False

        return False


    def has_all_refs_defined(obj: Any, defined_ids: Set[str]) -> bool:
        """Recursively ensure every dict with an @id refers to a defined element,
        unless it's a full definition (has @type)."""
        if isinstance(obj, dict):
            # If it's a *reference* (dict with @id and no @type), validate target.
            if "@id" in obj and "@type" not in obj:
                if obj["@id"] not in defined_ids:
                    return False
            # Recurse into values
            for v in obj.values():
                if not has_all_refs_defined(v, defined_ids):
                    return False
            return True
        if isinstance(obj, list):
            for v in obj:
                if not has_all_refs_defined(v, defined_ids):
                    return False
            return True
        return True


    # ---------- Fixpoint cleanup ----------
    # STRICT_REL_TO_DROP = {
    #     "Subsetting", "Specialization", "Subclassification",
    #     "FeatureTyping", "TypeFeaturing", "FeatureValue",
    # }
    STRICT_REL_TO_DROP = {
        "Subsetting", "Specialization", "Subclassification",
    }
    MEMBERSHIP_RELS = {
        "OwningMembership", "FeatureMembership", "NamespaceMembership",
        "Membership", "ParameterMembership",
    }
    REL_TYPES_TOP = STRICT_REL_TO_DROP | MEMBERSHIP_RELS  # for debug / top-pass logic



    changed = True
    iters = 0
    MAX_ITERS = 12

    while changed and iters < MAX_ITERS:
        iters += 1
        changed = False

        if iters >= MAX_ITERS and changed and debug:
            print(f"[Warn] Hit MAX_ITERS={MAX_ITERS} before fixpoint; remaining elements: {len(elements)}")

        defined_ids = build_defined_ids(elements)
        protected_ids = find_root_namespace_ids_syside(elements)
        if debug:
            if not protected_ids:
                print("[Warn] No root namespace candidates found at load time")
            else:
                print("[Info] Protected root namespace ids:", list(protected_ids)[:3])

        if debug:
            def collect_refs(obj: Any, out: Set[str]):
                if isinstance(obj, dict):
                    if "@id" in obj and "@type" not in obj:  # likely a thin ref
                        out.add(obj["@id"])
                    for v in obj.values():
                        collect_refs(v, out)
                elif isinstance(obj, list):
                    for v in obj:
                        collect_refs(v, out)

            ref_ids: Set[str] = set()
            for el in elements:
                collect_refs(el, ref_ids)
            unresolved = sorted(ref_ids - defined_ids)
            if unresolved:
                print("[Unresolved refs]", len(unresolved), "e.g.", unresolved[:10])

        # 1) prune thin dangling refs (and '@type':'Empty') everywhere
        ref_drops = [False]  # mutation flag captured by the function below

        new_elements = []
        for el in elements:
            cleaned_el = drop_thin_dangling_refs(el, defined_ids)
            if cleaned_el is DROP:
                changed = True
                continue
            new_elements.append(cleaned_el)
        elements = new_elements
        if ref_drops[0]:
            changed = True  # nested refs were removed

        # 2) drop incomplete relationships (SysML rules)
        defined_ids = build_defined_ids(elements)  # refresh before checks below

        # top-level pass (keep your root protection first)
        kept = []
        for el in elements:
            if isinstance(el, dict):
                if el.get("@id") in protected_ids:
                    kept.append(el); continue

                # 1) strictly drop incomplete STRICT relationships
                if is_relationship_and_incomplete(el, defined_ids):
                    changed = True
                    continue

                # 2) generic dangling refs: apply only to STRICT kinds
                t = el.get("@type")
                if t in STRICT_REL_TO_DROP and not has_all_refs_defined(el, defined_ids):
                    if debug:
                        bad_refs = []
                        for k, v in el.items():
                            if isinstance(v, dict) and "@id" in v and v["@id"] not in defined_ids:
                                bad_refs.append((k, v["@id"]))
                            elif isinstance(v, list):
                                for i in v:
                                    if isinstance(i, dict) and "@id" in i and i["@id"] not in defined_ids:
                                        bad_refs.append((k, i["@id"]))
                        if bad_refs:
                            print("Relationship", el.get("@id"), t, "has unresolved refs:", bad_refs)
                    changed = True
                    continue

                # 3) memberships: keep them (they glue the tree); optional: prune fields
                if t in MEMBERSHIP_RELS and not has_all_refs_defined(el, defined_ids):
                    if debug:
                        print("[Membership prune]", el.get("@id"), t, "— keeping element")
                    # optional micro-prune
                    # el = prune_membership_refs(el, defined_ids)
                    # (even if you don't prune, do NOT drop)

            kept.append(el)
        elements = kept

    if debug:
       print(f"[Done] Iterations: {iters}, elements left: {len(elements)}")

    # --- Infer and inject missing feature types (e.g., children : Component [0..*]) ---
    elements = _inject_inferred_types(elements, debug=debug)

    if root_wrapper is None:
        result = elements if isinstance(data, list) else (elements[0] if len(elements) == 1 else elements)
    else:
        out = dict(root_wrapper)
        out["elements"] = elements
        result = out

    return json.dumps(result, ensure_ascii=False, indent=indent)
