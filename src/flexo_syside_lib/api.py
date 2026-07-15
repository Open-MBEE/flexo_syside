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
    convert_sysml_models_textual_to_json,
    convert_sysml_string_textual_to_json,
)
from .model_walk import (
    find_component_partusage,
    find_expression_attribute_values,
    find_part_by_name,
    find_partusage_by_definition,
    walk_ownership_tree,
)
from .library_sync import (
    build_sysand_command,
    collect_installed_environment_models,
    collect_textual_models_from_directory,
    deduplicate_model_filenames,
    derive_sysand_library_name,
    find_primary_model_file,
    is_safe_within_dir,
    materialize_textual_models,
    normalize_sysand_clone_iri,
    run_sysand,
    safe_model_filename,
    safe_path_segment,
)

__all__ = [
    "build_sysand_command",
    "collect_installed_environment_models",
    "collect_textual_models_from_directory",
    "convert_json_to_sysml_textual",
    "convert_json_to_sysml_textual_multi_namespace",
    "convert_sysml_file_textual_to_json",
    "convert_sysml_files_textual_to_json",
    "convert_sysml_models_textual_to_json",
    "convert_sysml_string_textual_to_json",
    "deduplicate_model_filenames",
    "derive_sysand_library_name",
    "expand_minimal_json_to_full_json",
    "expand_minimal_json_to_full_json_model",
    "find_primary_model_file",
    "find_root_namespaces",
    "get_root_namespace_names",
    "is_safe_within_dir",
    "materialize_textual_models",
    "normalize_sysand_clone_iri",
    "find_partusage_by_definition",
    "run_sysand",
    "safe_model_filename",
    "safe_path_segment",
    "find_component_partusage",
    "walk_ownership_tree",
]
