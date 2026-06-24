from __future__ import annotations

from .core_multi_namespace import (
    convert_json_to_sysml_textual_multi_namespace,
    find_root_namespaces,
    get_root_namespace_names,
)
from .expansion import (
    expand_minimal_json_to_full_json,
    expand_minimal_json_to_full_json_model,
)
from .serde import (
    convert_json_to_sysml_textual,
    convert_sysml_file_textual_to_json,
    convert_sysml_files_textual_to_json,
    convert_sysml_string_textual_to_json,
)
from .model_walk import (
    find_component_partusage,
    find_expression_attribute_values,
    find_part_by_name,
    find_partusage_by_definition,
    walk_ownership_tree,
)

__all__ = [
    "convert_json_to_sysml_textual",
    "convert_json_to_sysml_textual_multi_namespace",
    "convert_sysml_file_textual_to_json",
    "convert_sysml_files_textual_to_json",
    "convert_sysml_string_textual_to_json",
    "expand_minimal_json_to_full_json",
    "expand_minimal_json_to_full_json_model",
    "find_root_namespaces",
    "get_root_namespace_names",
    "find_partusage_by_definition",
    "find_component_partusage",
    "walk_ownership_tree",
]
