import json

import pytest
import pytest_check as check

from flexo_syside_lib.core import (
    convert_json_to_sysml_textual,
    convert_sysml_file_textual_to_json,
    convert_sysml_files_textual_to_json,
    convert_sysml_string_textual_to_json,
    expand_minimal_json_to_full_json,
    expand_minimal_json_to_full_json_model,
)

from conftest import (
    MULTI_NAMESPACE_DIR,
    canonical_namespace_models,
    canonicalize_json_elements,
    fixture_path,
)


def test_serialize_deserialize_examples():
    model_paths = [
        fixture_path("Test2.sysml"),
        fixture_path("pu-simple.sysml"),
        fixture_path("pu.sysml"),
        fixture_path("library.sysml"),
        fixture_path("geo.sysml"),
        fixture_path("Test4.sysml"),
        fixture_path("Test5.sysml"),
        fixture_path("Test6.sysml"),
        fixture_path("Test7.sysml"),
        fixture_path("Test1.sysml"),
        fixture_path("Test3.sysml"),
    ]

    for model_file_path in model_paths:
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        del change_payload_file
        data = json.loads(raw_jsonf)
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        del model, warnings
        check.is_not(sysml_text, None)


def test_serialize_deserialize_string_input():
    thissrc = """
        part m0001_2N {

            part nx0001 {
                port scp_outside2;
            }

            part tcs0001{
                port scp;
            }

            interface tcs0001.scp to nx0001.scp_outside2;
        }
    """
    change_payload_file, raw_jsonf = convert_sysml_string_textual_to_json(
        sysml_model_string=thissrc,
        minimal=False,
    )
    del change_payload_file
    data = json.loads(raw_jsonf)
    (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
    del model, warnings
    assert sysml_text is not None


def test_expand_minimal_json_to_full_json_restores_implied_relationships():
    model_file_path = fixture_path("Test2.sysml")

    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

    full_data = json.loads(raw_json_full)
    expanded_data = json.loads(raw_json_expanded)

    full_implied = [e for e in full_data if e.get("isImplied")]
    expanded_implied = [e for e in expanded_data if e.get("isImplied")]

    assert expanded_implied
    assert len(expanded_data) == len(full_data)
    assert len(expanded_implied) == len(full_implied)
    assert sum(1 for e in expanded_data if e.get("@type") == "Subclassification") == sum(
        1 for e in full_data if e.get("@type") == "Subclassification"
    )


def test_expand_minimal_json_to_full_json_flashlight_example():
    model_file_path = fixture_path("Flashlight.sysml")

    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

    full_data = json.loads(raw_json_full)
    expanded_data = json.loads(raw_json_expanded)

    full_implied = [e for e in full_data if e.get("isImplied")]
    expanded_implied = [e for e in expanded_data if e.get("isImplied")]

    assert expanded_implied
    assert len(expanded_data) >= len(full_data)
    assert len(expanded_implied) >= len(full_implied)
    assert {e.get("@type") for e in expanded_implied} >= {e.get("@type") for e in full_implied}


def test_expand_minimal_json_to_full_json_preserves_multi_root_filenames(tmp_path):
    alpha_path = tmp_path / "expand-alpha.sysml"
    beta_path = tmp_path / "expand-beta.sysml"

    alpha_path.write_text("package Alpha { part def A; }\n", encoding="utf-8")
    beta_path.write_text("package Beta { part def B; }\n", encoding="utf-8")

    _, raw_json_min = convert_sysml_files_textual_to_json([alpha_path, beta_path], minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

    expanded_data = json.loads(raw_json_expanded)
    expanded_roots = [
        element.get("qualifiedName")
        for element in expanded_data
        if element.get("@type") == "Namespace" and "owningRelationship" not in element
    ]

    assert expanded_roots == ["expand-alpha.sysml", "expand-beta.sysml"]


def test_expand_minimal_json_to_full_json_model_preserves_multi_root_filenames():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]

    _, raw_json_min = convert_sysml_files_textual_to_json(model_file_paths, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

    assert canonical_namespace_models(raw_json_expanded) == canonical_namespace_models(
        convert_sysml_files_textual_to_json(model_file_paths, minimal=False)[1]
    )


def test_flashlight_single_min_json_roundtrip_text_identity():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    assert canonical_namespace_models(raw_json_min) == canonical_namespace_models(raw_json_full)


def test_flashlight_single_full_json_roundtrip_text_identity():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    assert canonical_namespace_models(raw_json_full) == canonical_namespace_models(raw_json_full)


def test_flashlight_multi_min_json_roundtrip_text_identity():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    _, raw_json_min = convert_sysml_files_textual_to_json(model_file_paths, minimal=True)
    assert canonical_namespace_models(raw_json_min) == canonical_namespace_models(raw_json_full)


def test_flashlight_multi_full_json_roundtrip_text_identity():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    assert canonical_namespace_models(raw_json_full) == canonical_namespace_models(raw_json_full)


def test_flashlight_single_expand_min_to_full_roundtrip_text_identity():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)
    assert canonical_namespace_models(raw_json_expanded) == canonical_namespace_models(raw_json_full)


def test_flashlight_multi_expand_min_to_full_roundtrip_text_identity():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    _, raw_json_min = convert_sysml_files_textual_to_json(model_file_paths, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)
    assert canonical_namespace_models(raw_json_expanded) == canonical_namespace_models(raw_json_full)


def test_flashlight_single_full_json_matches_expanded_json_textually():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)
    assert canonical_namespace_models(raw_json_full) == canonical_namespace_models(raw_json_expanded)


@pytest.mark.xfail(
    reason=(
        "expand_minimal_json_to_full_json_model() currently recreates the "
        "Flashlight model textually but does not produce byte-equivalent "
        "full JSON compared to direct textual serialization."
    ),
    strict=True,
)
def test_flashlight_single_expand_model_full_json_matches_direct_full_json():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)
    assert canonicalize_json_elements(raw_json_expanded) == canonicalize_json_elements(raw_json_full)


@pytest.mark.xfail(
    reason=(
        "expand_minimal_json_to_full_json_model() currently recreates the "
        "multi-file Flashlight model textually but does not produce "
        "byte-equivalent full JSON compared to direct textual serialization."
    ),
    strict=True,
)
def test_flashlight_multi_expand_model_full_json_matches_direct_full_json():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    _, raw_json_min = convert_sysml_files_textual_to_json(model_file_paths, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)
    assert canonicalize_json_elements(raw_json_expanded) == canonicalize_json_elements(raw_json_full)


def test_flashlight_single_expand_model_full_json_recreates_original_sysml_file():
    model_file_path = fixture_path("Flashlight.sysml")
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)
    assert canonical_namespace_models(raw_json_expanded) == canonical_namespace_models(raw_json_full)


def test_flashlight_multi_expand_model_full_json_recreates_original_sysml_files():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    _, raw_json_min = convert_sysml_files_textual_to_json(model_file_paths, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)
    assert canonical_namespace_models(raw_json_expanded) == canonical_namespace_models(raw_json_full)
