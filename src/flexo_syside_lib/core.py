from __future__ import annotations

import syside

from .expansion import (
    expand_minimal_json_to_full_json,
    expand_minimal_json_to_full_json_model,
)
from .model_walk import (
    children_iter as _children_iter,
    find_component_partusage,
    find_expression_attribute_values,
    find_part_by_name,
    find_partusage_by_definition,
    walk_ownership_tree,
)
from .payload import (
    ELEMENT_TYPE_KEY,
    apply_root_namespace_name as _apply_root_namespace_name,
    remove_uri_fields as _remove_uri_fields,
    replace_none_with_empty as _replace_none_with_empty,
    wrap_elements_as_payload as _wrap_elements_as_payload,
)
from .serde import (
    convert_json_to_sysml_textual,
    convert_sysml_file_textual_to_json,
    convert_sysml_files_textual_to_json,
    convert_sysml_models_textual_to_json,
    convert_sysml_string_textual_to_json,
    create_json_writer as _create_json_writer,
    create_serialization_options as _create_serialization_options,
    make_root_namespace_first_legacy as _make_root_namespace_first,
    model_to_json as _model_to_json,
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
    "ELEMENT_TYPE_KEY",
    "_apply_root_namespace_name",
    "_children_iter",
    "_create_json_writer",
    "_create_serialization_options",
    "_make_root_namespace_first",
    "_model_to_json",
    "_remove_uri_fields",
    "_replace_none_with_empty",
    "_wrap_elements_as_payload",
    "build_sysand_command",
    "collect_installed_environment_models",
    "collect_textual_models_from_directory",
    "convert_json_to_sysml_textual",
    "convert_sysml_file_textual_to_json",
    "convert_sysml_files_textual_to_json",
    "convert_sysml_models_textual_to_json",
    "convert_sysml_string_textual_to_json",
    "deduplicate_model_filenames",
    "derive_sysand_library_name",
    "expand_minimal_json_to_full_json",
    "expand_minimal_json_to_full_json_model",
    "find_primary_model_file",
    "is_safe_within_dir",
    "find_component_partusage",
    "find_expression_attribute_values",
    "find_part_by_name",
    "find_partusage_by_definition",
    "materialize_textual_models",
    "normalize_sysand_clone_iri",
    "run_sysand",
    "safe_model_filename",
    "safe_path_segment",
    "syside",
    "walk_ownership_tree",
]
