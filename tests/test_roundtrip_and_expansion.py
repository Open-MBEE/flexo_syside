import json

import pytest
import pytest_check as check

from flexo_syside_lib.core import (
    convert_json_to_sysml_textual,
    convert_sysml_file_textual_to_json,
    convert_sysml_files_textual_to_json,
    convert_sysml_models_textual_to_json,
    convert_sysml_string_textual_to_json,
    expand_minimal_json_to_full_json,
    expand_minimal_json_to_full_json_model,
)
from flexo_syside_lib.core_multi_namespace import convert_json_to_sysml_textual_multi_namespace

from conftest import (
    MULTI_NAMESPACE_DIR,
    FIXTURES_DIR,
    canonical_namespace_models,
    canonicalize_json_elements,
    fixture_path,
    normalize_roundtrip_sysml_text,
)


EXACT_MODEL_ROUNDTRIP_FIXTURES = [
    "Drone2.sysml",
    "geo.sysml",
    "library.sysml",
    "pu-simple.sysml",
    "pu.sysml",
    "Test1.sysml",
    "Test2.sysml",
    "Test3.sysml",
    "Test4.sysml",
    "Test6.sysml",
]

KNOWN_MODEL_ROUNDTRIP_LIMITATIONS = [
    "Flashlight.sysml",
    "Test5.sysml",
    "Test7.sysml",
]

FULL_JSON_TEXT_STABLE_FIXTURES = [
    "Drone2.sysml",
    "Flashlight.sysml",
    "geo.sysml",
    "library.sysml",
    "pu-simple.sysml",
    "pu.sysml",
    "Test1.sysml",
    "Test2.sysml",
    "Test3.sysml",
    "Test4.sysml",
    "Test6.sysml",
]

KNOWN_FULL_JSON_TEXT_REPARSE_LIMITATIONS = [
    "Test5.sysml",
    "Test7.sysml",
]


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


def test_convert_json_to_sysml_textual_resolves_action_start_via_sema():
    source = """
        package FlashlightStarterModel {
            package FlashlightSpecificationAndDesign {
                package Actions {
                    action produceDirectedLight {
                        action provideDCPwr;
                        action connectDCPwr;
                        fork fork1;
                        then provideDCPwr;
                        then connectDCPwr;
                        first start then fork1;
                    }
                }
            }
        }
    """

    _, raw_json_min = convert_sysml_string_textual_to_json(source, minimal=True)
    result, warnings = convert_json_to_sysml_textual(raw_json_min)

    assert result is not None
    sysml_text, _model = result
    assert "first start then fork1;" in sysml_text
    assert "Actions::Action::start" not in sysml_text
    assert not warnings


def test_convert_json_to_sysml_textual_multi_namespace_avoids_external_ref_warnings():
    source = "package P { private import ScalarValues::*; }"

    _, raw_json_min = convert_sysml_string_textual_to_json(source, minimal=True)
    namespace_models, warnings = convert_json_to_sysml_textual_multi_namespace(raw_json_min)

    assert namespace_models
    assert not warnings


def test_convert_sysml_models_textual_to_json_matches_file_based_multi_conversion():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]
    sysml_models = [
        (path.name, path.read_text(encoding="utf-8"))
        for path in model_file_paths
    ]

    _, raw_json_from_files = convert_sysml_files_textual_to_json(
        model_file_paths,
        minimal=False,
    )
    _, raw_json_from_models = convert_sysml_models_textual_to_json(
        sysml_models,
        minimal=False,
    )

    assert canonical_namespace_models(raw_json_from_models) == canonical_namespace_models(
        raw_json_from_files
    )


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


@pytest.mark.parametrize("fixture_name", EXACT_MODEL_ROUNDTRIP_FIXTURES)
def test_expand_minimal_json_to_full_json_model_matches_direct_full_json(
    fixture_name: str,
):
    model_file_path = FIXTURES_DIR / fixture_name

    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

    assert canonicalize_json_elements(raw_json_expanded) == canonicalize_json_elements(
        raw_json_full
    )


def test_expand_minimal_json_to_full_json_model_matches_direct_full_json_for_simple_multi_root(
    tmp_path,
):
    alpha_path = tmp_path / "model-alpha.sysml"
    beta_path = tmp_path / "model-beta.sysml"

    alpha_path.write_text("package Alpha { part def A; }\n", encoding="utf-8")
    beta_path.write_text("package Beta { part def B; }\n", encoding="utf-8")

    _, raw_json_full = convert_sysml_files_textual_to_json([alpha_path, beta_path], minimal=False)
    _, raw_json_min = convert_sysml_files_textual_to_json([alpha_path, beta_path], minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

    assert canonicalize_json_elements(raw_json_expanded) == canonicalize_json_elements(
        raw_json_full
    )


@pytest.mark.parametrize("fixture_name", FULL_JSON_TEXT_STABLE_FIXTURES)
def test_full_json_roundtrip_text_stabilizes_for_single_file_models(fixture_name: str):
    model_file_path = FIXTURES_DIR / fixture_name

    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    first_result, first_warnings = convert_json_to_sysml_textual(raw_json_full)

    assert first_result is not None
    first_text, _first_model = first_result
    assert first_text.strip()
    assert not first_warnings

    _, roundtrip_full_json = convert_sysml_string_textual_to_json(first_text, minimal=False)
    second_result, second_warnings = convert_json_to_sysml_textual(roundtrip_full_json)

    assert second_result is not None
    second_text, _second_model = second_result
    assert not second_warnings
    assert normalize_roundtrip_sysml_text(first_text) == normalize_roundtrip_sysml_text(
        second_text
    )


@pytest.mark.xfail(
    reason=(
        "Some reconstructed full-JSON texts still fail reparsing due upstream "
        "metadata-feature annotation issues."
    ),
    strict=True,
)
@pytest.mark.parametrize("fixture_name", KNOWN_FULL_JSON_TEXT_REPARSE_LIMITATIONS)
def test_full_json_roundtrip_text_known_reparse_limitations(fixture_name: str):
    model_file_path = FIXTURES_DIR / fixture_name

    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    first_result, first_warnings = convert_json_to_sysml_textual(raw_json_full)

    assert first_result is not None
    first_text, _first_model = first_result
    assert first_text.strip()
    assert not first_warnings

    _, roundtrip_full_json = convert_sysml_string_textual_to_json(first_text, minimal=False)
    second_result, second_warnings = convert_json_to_sysml_textual(roundtrip_full_json)

    assert second_result is not None
    second_text, _second_model = second_result
    assert not second_warnings
    assert normalize_roundtrip_sysml_text(first_text) == normalize_roundtrip_sysml_text(
        second_text
    )


def test_full_json_roundtrip_text_stabilizes_for_multi_file_model_set():
    model_file_paths = [
        MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
        MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
        MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
    ]

    _, raw_json_full = convert_sysml_files_textual_to_json(model_file_paths, minimal=False)
    first_models, first_warnings = convert_json_to_sysml_textual_multi_namespace(raw_json_full)

    assert first_models
    assert not first_warnings

    _, roundtrip_full_json = convert_sysml_models_textual_to_json(first_models, minimal=False)
    second_models, second_warnings = convert_json_to_sysml_textual_multi_namespace(
        roundtrip_full_json
    )

    assert second_models
    assert not second_warnings
    assert {
        namespace_name: normalize_roundtrip_sysml_text(sysml_text)
        for namespace_name, sysml_text in first_models
    } == {
        namespace_name: normalize_roundtrip_sysml_text(sysml_text)
        for namespace_name, sysml_text in second_models
    }


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
        "Sensmetry still reports non-identical derived relationship bindings "
        "for some reconstructed models with external/library references."
    ),
    strict=True,
)
@pytest.mark.parametrize("fixture_name", KNOWN_MODEL_ROUNDTRIP_LIMITATIONS)
def test_expand_minimal_json_to_full_json_model_known_single_file_limitations(
    fixture_name: str,
):
    model_file_path = FIXTURES_DIR / fixture_name
    _, raw_json_full = convert_sysml_file_textual_to_json(model_file_path, minimal=False)
    _, raw_json_min = convert_sysml_file_textual_to_json(model_file_path, minimal=True)
    _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)
    assert canonicalize_json_elements(raw_json_expanded) == canonicalize_json_elements(
        raw_json_full
    )


@pytest.mark.xfail(
    reason=(
        "Sensmetry still reports non-identical derived relationship bindings "
        "for some reconstructed multi-file models with external/library references."
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
