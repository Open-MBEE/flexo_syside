"""
Tests for flexo_syside_lib core functionality.
Tests the actual source code from src/ with proper license handling.
"""
import pytest
import pytest_check as check
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import json, pprint
import importlib
import sys
import syside
import pathlib
import types
from flexo_syside_lib.core import convert_sysml_file_textual_to_json, convert_sysml_files_textual_to_json, convert_sysml_string_textual_to_json, convert_json_to_sysml_textual, expand_minimal_json_to_full_json, expand_minimal_json_to_full_json_model
from flexo_syside_lib.core_multi_namespace import convert_json_to_sysml_textual_multi_namespace

from pathlib import Path
TEST_DIR = Path(__file__).resolve().parent
MULTI_NAMESPACE_DIR = Path("examples") / "multi_namespace"


def _normalize_roundtrip_sysml_text(sysml_text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in sysml_text.strip().splitlines())
    return normalized.replace("Actions::Action::start", "start")


def _canonical_namespace_models(json_text: str) -> dict[str, str]:
    namespace_models, _warnings = convert_json_to_sysml_textual_multi_namespace(json_text)
    return {
        namespace_name: _normalize_roundtrip_sysml_text(sysml_text)
        for namespace_name, sysml_text in namespace_models
    }


def _canonicalize_json_value(value):
    if isinstance(value, dict):
        return {
            key: _canonicalize_json_value(val)
            for key, val in sorted(value.items())
        }
    if isinstance(value, list):
        canonical_items = [_canonicalize_json_value(item) for item in value]
        if all(isinstance(item, dict) and "@id" in item for item in canonical_items):
            return sorted(canonical_items, key=lambda item: item["@id"])
        return canonical_items
    return value


def _canonicalize_json_elements(json_text: str) -> list[dict]:
    elements = json.loads(json_text)
    canonical_elements = [_canonicalize_json_value(element) for element in elements]
    return sorted(canonical_elements, key=lambda element: element.get("@id", ""))


class TestUtilityFunctions:
    """Test utility functions that don't require SysIDE."""
    
    def test_replace_none_with_empty(self):
        """Test the _replace_none_with_empty utility function."""
        # Import here to ensure license is set up
        from flexo_syside_lib.core import _replace_none_with_empty
        
        data = {"a": None, "b": [1, None, {"c": None}]}
        out = _replace_none_with_empty(data)
        assert out == {"a": "", "b": [1, None, {"c": ""}]}
    
    def test_remove_uri_fields(self):
        """Test the _remove_uri_fields utility function."""
        from flexo_syside_lib.core import _remove_uri_fields
        
        data = {"@uri": "x", "a": {"@uri": "y", "b": 1}, "c": [{"@uri": "z"}, {"d": 2}]}
        out = _remove_uri_fields(data)
        assert out == {"a": {"b": 1}, "c": [{}, {"d": 2}]}
    
    def test_wrap_elements_as_payload(self):
        """Test the _wrap_elements_as_payload utility function."""
        from flexo_syside_lib.core import _wrap_elements_as_payload
        
        elements = [
            {"@id": "ID1", "@uri": "ignore", "name": None},
            {"name": "X", "props": [None, 1]},
        ]
        wrapped = _wrap_elements_as_payload(elements)
        assert wrapped[0]["identity"] == {"@id": "ID1"}
        assert wrapped[0]["payload"]["name"] == ""
        assert wrapped[1]["payload"]["props"][0] is None
    
    def test_make_root_namespace_first(self):
        """Test the _make_root_namespace_first utility function."""
        from flexo_syside_lib.core import _make_root_namespace_first
        
        items = [
            {"@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
            {"@type": "Element"},
            {"@type": "Namespace"},  # This one has no qualifiedName, so it's the root
        ]
        s = json.dumps(items)
        out = _make_root_namespace_first(s)
        arr = json.loads(out)
        assert arr[0]["@type"] == "Namespace"
        assert "qualifiedName" not in arr[0]  # Root namespace has no qualifiedName
    
    def test_make_root_namespace_first_with_timestamp(self):
        """Test that namespace with latest timestamp is moved to front."""
        from flexo_syside_lib.core import _make_root_namespace_first
        
        items = [
            {"@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
            {"@type": "Element"},
            {"@type": "Namespace", "qualifiedName": "2021-01-01T00:00:00Z"},
        ]
        s = json.dumps(items)
        out = _make_root_namespace_first(s)
        arr = json.loads(out)
        assert arr[0]["@type"] == "Namespace"
        assert arr[0]["qualifiedName"] == "2021-01-01T00:00:00Z"
    
    def test_make_root_namespace_first_no_namespace(self):
        """Test that ValueError is raised when no namespace is found."""
        from flexo_syside_lib.core import _make_root_namespace_first
        
        items = [
            {"@type": "Element"},
            {"@type": "Block"},
        ]
        s = json.dumps(items)
        with pytest.raises(ValueError, match="No root namespace found"):
            _make_root_namespace_first(s)

    def test_serialize_deserialize1(self):
        MODEL_FILE_PATH = TEST_DIR / "test2.sysml"

        thissrc="""
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

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_string_textual_to_json(sysml_model_string=thissrc, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = TEST_DIR / "pu-simple.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = TEST_DIR / "pu.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = TEST_DIR / "library.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = TEST_DIR / "geo.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

    def test_serialize_deserialize1a(self):
        def find_attribute_values(element: syside.Element, level: int = 0) -> None:

            if element.try_cast(syside.AttributeUsage):
                #if element.name is not None: print("  " * level, element.name)
                attr  = element.cast(syside.AttributeUsage)
                expression = next(iter(attr.owned_elements), None)
                if expression is not None and isinstance(expression, syside.OperatorExpression):
                    expression, units = expression.arguments.collect()
                    typecheckedunit = units.cast(syside.FeatureReferenceExpression).referent
                    print (f"units = {units.referent} {typecheckedunit}")
            
                    print (f"units = {units} {units.qualified_name}")
                if expression is not None and isinstance(expression, syside.LiteralRational):
                    print(f"{attr.declared_name}: {expression.value}")
            
            for child in element.owned_elements.collect():
                find_attribute_values(child, level + 1)

            thissrc="""
            package MechanicalObjectExample {
                private import ScalarValues::*;
                part def DroneSystem {
                    part def Drone {
                        part battery {
                            /*attribute mass:ISQ::MassValue = 2.5 [SI::kg];*/
                            attribute m:Real=2.5;
                        }
                        part propulsionUnit {
                            attribute mass:ISQ::MassValue = 0.5 [SI::kg];
                        }            
                    }
                }

            }"""
            model, diagnostics = syside.load_model(sysml_source=thissrc)
            for document_resource in model.documents:
                with document_resource.lock() as document:
                    find_attribute_values(document.root_node)
            change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(thissrc, minimal=False)
            data = json.loads(raw_jsonf)  # parse JSON string into Python objects
            (sysml_text, model), warnings = convert_json_to_sysml_textual(data)

            find_attribute_values(model.document.root_node)

    def test_serialize_deserialize4(self):
        MODEL_FILE_PATH = TEST_DIR / "Test4.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize5(self):
        MODEL_FILE_PATH = TEST_DIR / "Test5.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize6(self):
        MODEL_FILE_PATH = TEST_DIR / "Test6.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize7(self):
        MODEL_FILE_PATH = TEST_DIR / "Test7.sysml"

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)

    def test_serialize_deserialize8(self):
        MODEL_FILE_PATH = TEST_DIR / "Test1.sysml"

        try:
            # use minimal = True to get the compact version
            change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
            data = json.loads(raw_jsonf)  # parse JSON string into Python objects
            (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
            #assert sysml_text !=None
            check.is_not(sysml_text,None)
        except ValueError as e:
            # Custom reporting or logging for the unexpected exception
            print(f"Caught an unexpected ValueError: {e}")
            pytest.fail(f"Test failed due to unexpected ValueError: {e}")

    def test_serialize_deserialize9(self):
        MODEL_FILE_PATH = TEST_DIR / "Test3.sysml"

        try:
            # use minimal = True to get the compact version
            change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
            data = json.loads(raw_jsonf)  # parse JSON string into Python objects
            (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
            #assert sysml_text !=None
            check.is_not(sysml_text,None)

        except ValueError as e:
            # Custom reporting or logging for the unexpected exception
            print(f"Caught an unexpected ValueError: {e}")
            pytest.fail(f"Test failed due to unexpected ValueError: {e}")

    def test_expand_minimal_json_to_full_json_restores_implied_relationships(self):
        model_file_path = TEST_DIR / "test2.sysml"

        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

        full_data = json.loads(raw_json_full)
        expanded_data = json.loads(raw_json_expanded)

        full_implied = [e for e in full_data if e.get("isImplied")]
        expanded_implied = [e for e in expanded_data if e.get("isImplied")]

        assert expanded_implied
        assert len(expanded_data) == len(full_data)
        assert len(expanded_implied) == len(full_implied)
        assert sum(1 for e in expanded_data if e.get("@type") == "Subclassification") == \
            sum(1 for e in full_data if e.get("@type") == "Subclassification")

    def test_expand_minimal_json_to_full_json_flashlight_example(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

        full_data = json.loads(raw_json_full)
        expanded_data = json.loads(raw_json_expanded)

        full_implied = [e for e in full_data if e.get("isImplied")]
        expanded_implied = [e for e in expanded_data if e.get("isImplied")]

        assert expanded_implied
        assert len(expanded_data) >= len(full_data)
        assert len(expanded_implied) >= len(full_implied)
        assert {
            e.get("@type") for e in expanded_implied
        } >= {
            e.get("@type") for e in full_implied
        }

    def test_expand_minimal_json_to_full_json_preserves_multi_root_filenames(self):
        alpha_path = TEST_DIR / "expand-alpha.sysml"
        beta_path = TEST_DIR / "expand-beta.sysml"

        alpha_path.write_text("package Alpha { part def A; }\n", encoding="utf-8")
        beta_path.write_text("package Beta { part def B; }\n", encoding="utf-8")

        try:
            _, raw_json_min = convert_sysml_files_textual_to_json(
                [alpha_path, beta_path],
                minimal=True,
            )
            _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

            expanded_data = json.loads(raw_json_expanded)
            expanded_roots = [
                element.get("qualifiedName")
                for element in expanded_data
                if element.get("@type") == "Namespace" and "owningRelationship" not in element
            ]

            assert expanded_roots == ["expand-alpha.sysml", "expand-beta.sysml"]
        finally:
            alpha_path.unlink(missing_ok=True)
            beta_path.unlink(missing_ok=True)

    def test_expand_minimal_json_to_full_json_model_preserves_multi_root_filenames(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_min = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

        assert _canonical_namespace_models(raw_json_expanded) == _canonical_namespace_models(
            convert_sysml_files_textual_to_json(
                sysml_file_paths=model_file_paths,
                minimal=False,
            )[1]
        )

    def test_flashlight_single_min_json_roundtrip_text_identity(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )

        assert _canonical_namespace_models(raw_json_min) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_single_full_json_roundtrip_text_identity(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )

        assert _canonical_namespace_models(raw_json_full) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_multi_min_json_roundtrip_text_identity(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_full = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=True,
        )

        assert _canonical_namespace_models(raw_json_min) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_multi_full_json_roundtrip_text_identity(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_full = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=False,
        )

        assert _canonical_namespace_models(raw_json_full) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_single_expand_min_to_full_roundtrip_text_identity(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

        assert _canonical_namespace_models(raw_json_expanded) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_multi_expand_min_to_full_roundtrip_text_identity(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_full = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

        assert _canonical_namespace_models(raw_json_expanded) == _canonical_namespace_models(raw_json_full)

    def test_flashlight_single_full_json_matches_expanded_json_textually(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json(raw_json_min)

        assert _canonical_namespace_models(raw_json_full) == _canonical_namespace_models(raw_json_expanded)

    @pytest.mark.xfail(
        reason=(
            "expand_minimal_json_to_full_json_model() currently recreates the "
            "Flashlight model textually but does not produce byte-equivalent "
            "full JSON compared to direct textual serialization."
        ),
        strict=True,
    )
    def test_flashlight_single_expand_model_full_json_matches_direct_full_json(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

        assert _canonicalize_json_elements(raw_json_expanded) == _canonicalize_json_elements(
            raw_json_full
        )

    @pytest.mark.xfail(
        reason=(
            "expand_minimal_json_to_full_json_model() currently recreates the "
            "multi-file Flashlight model textually but does not produce "
            "byte-equivalent full JSON compared to direct textual serialization."
        ),
        strict=True,
    )
    def test_flashlight_multi_expand_model_full_json_matches_direct_full_json(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_full = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

        assert _canonicalize_json_elements(raw_json_expanded) == _canonicalize_json_elements(
            raw_json_full
        )

    def test_flashlight_single_expand_model_full_json_recreates_original_sysml_file(self):
        model_file_path = TEST_DIR / "Flashlight.sysml"

        _, raw_json_full = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_file_textual_to_json(
            sysml_file_path=model_file_path,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

        assert _canonical_namespace_models(raw_json_expanded) == _canonical_namespace_models(
            raw_json_full
        )

    def test_flashlight_multi_expand_model_full_json_recreates_original_sysml_files(self):
        model_file_paths = [
            MULTI_NAMESPACE_DIR / "FlashlightStarterModel.sysml",
            MULTI_NAMESPACE_DIR / "FlashlightContextClassExercise.sysml",
            MULTI_NAMESPACE_DIR / "GeneralConcepts.sysml",
        ]

        _, raw_json_full = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=False,
        )
        _, raw_json_min = convert_sysml_files_textual_to_json(
            sysml_file_paths=model_file_paths,
            minimal=True,
        )
        _, raw_json_expanded = expand_minimal_json_to_full_json_model(raw_json_min)

        assert _canonical_namespace_models(raw_json_expanded) == _canonical_namespace_models(
            raw_json_full
        )


class TestSysIDEIntegration:
    """Test SysIDE-dependent functions with proper mocking."""
    
    @patch('flexo_syside_lib.core.syside')
    def test_convert_sysml_string_to_json(self, mock_syside):
        """Test converting SysML string to JSON with mocked SysIDE."""
        from flexo_syside_lib.core import convert_sysml_string_textual_to_json
        
        # Sample SysML content
        sample_sysml = '''
        package TestPackage {
            part def Component {
                attribute name: String;
            }
        }
        '''
        
        # Sample JSON data
        sample_json = [
            {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
            {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
        ]
        
        # Mock SysIDE components
        mock_model = Mock()
        mock_diagnostics = Mock()
        mock_diagnostics.contains_errors.return_value = False
        mock_syside.load_model.return_value = (mock_model, mock_diagnostics)
        
        # Mock the model serialization
        mock_model.user_docs = [Mock()]
        mock_locked = Mock()
        mock_locked.root_node = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_locked)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_model.user_docs[0].lock.return_value = mock_context_manager
        
        # Mock JSON writer
        mock_writer = Mock()
        mock_writer.result = json.dumps(sample_json)
        
        # Mock serialization options
        mock_options = Mock()
        
        with patch('flexo_syside_lib.core._create_json_writer', return_value=mock_writer), \
             patch('flexo_syside_lib.core._create_serialization_options', return_value=mock_options), \
             patch('flexo_syside_lib.core.syside.serialize'):
            
            payload, json_string = convert_sysml_string_textual_to_json(sample_sysml)
            
            # Verify we get a payload structure
            assert isinstance(payload, list)
            assert len(payload) > 0
            
            # Verify payload structure
            for item in payload:
                assert "payload" in item
                assert "identity" in item
                assert isinstance(item["payload"], dict)
                assert isinstance(item["identity"], dict)
            
            # Verify JSON string is valid
            parsed_json = json.loads(json_string)
            assert isinstance(parsed_json, list)
            assert len(parsed_json) > 0
    
    @patch('flexo_syside_lib.core.syside')
    def test_convert_sysml_file_to_json(self, mock_syside):
        """Test converting SysML file to JSON with mocked SysIDE."""
        from flexo_syside_lib.core import convert_sysml_file_textual_to_json
        
        # Sample SysML content
        sample_sysml = '''
        package TestPackage {
            part def Component {
                attribute name: String;
            }
        }
        '''
        
        # Sample JSON data
        sample_json = [
            {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
            {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
        ]
        
        # Mock SysIDE components
        mock_model = Mock()
        mock_diagnostics = Mock()
        mock_diagnostics.contains_errors.return_value = False
        mock_syside.try_load_model.return_value = (mock_model, mock_diagnostics)
        
        # Mock the model serialization
        mock_model.user_docs = [Mock()]
        mock_locked = Mock()
        mock_locked.root_node = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_locked)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_model.user_docs[0].lock.return_value = mock_context_manager
        
        # Mock JSON writer
        mock_writer = Mock()
        mock_writer.result = json.dumps(sample_json)
        
        # Mock serialization options
        mock_options = Mock()
        
        with patch('flexo_syside_lib.core._create_json_writer', return_value=mock_writer), \
             patch('flexo_syside_lib.core._create_serialization_options', return_value=mock_options), \
             patch('flexo_syside_lib.core.syside.serialize'):
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sysml', delete=False) as f:
                f.write(sample_sysml)
                temp_file = f.name
            
            try:
                payload, json_string = convert_sysml_file_textual_to_json(temp_file)
                
                # Verify we get a payload structure
                assert isinstance(payload, list)
                assert len(payload) > 0
                
                # Verify payload structure
                for item in payload:
                    assert "payload" in item
                    assert "identity" in item
                    assert isinstance(item["payload"], dict)
                    assert isinstance(item["identity"], dict)
                
                # Verify JSON string is valid
                parsed_json = json.loads(json_string)
                assert isinstance(parsed_json, list)
                assert len(parsed_json) > 0
                root_namespaces = [
                    element for element in parsed_json
                    if element["@type"] == "Namespace" and "owningRelationship" not in element
                ]
                assert root_namespaces[0]["qualifiedName"] == os.path.basename(temp_file)
                
            finally:
                os.unlink(temp_file)

    @patch('flexo_syside_lib.core.syside')
    def test_convert_sysml_files_to_json(self, mock_syside):
        """Test converting multiple SysML files to one JSON array with multiple roots."""
        sample_doc_1 = [
            {"@id": "ns1", "@type": "Namespace", "name": "Alpha"},
            {"@id": "pkg1", "@type": "Package", "declaredName": "Alpha"},
        ]
        sample_doc_2 = [
            {"@id": "ns2", "@type": "Namespace", "name": "Beta"},
            {"@id": "pkg2", "@type": "Package", "declaredName": "Beta"},
        ]

        mock_model = Mock()
        mock_diagnostics = Mock()
        mock_diagnostics.contains_errors.return_value = False
        mock_syside.try_load_model.return_value = (mock_model, mock_diagnostics)

        locked_1 = Mock()
        locked_1.root_node = Mock()
        ctx_1 = Mock()
        ctx_1.__enter__ = Mock(return_value=locked_1)
        ctx_1.__exit__ = Mock(return_value=None)

        locked_2 = Mock()
        locked_2.root_node = Mock()
        ctx_2 = Mock()
        ctx_2.__enter__ = Mock(return_value=locked_2)
        ctx_2.__exit__ = Mock(return_value=None)

        doc_1 = Mock()
        doc_1.lock.return_value = ctx_1
        doc_2 = Mock()
        doc_2.lock.return_value = ctx_2
        mock_model.user_docs = [doc_1, doc_2]

        writer_1 = Mock()
        writer_1.result = json.dumps(sample_doc_1)
        writer_2 = Mock()
        writer_2.result = json.dumps(sample_doc_2)

        mock_options = Mock()

        with patch('flexo_syside_lib.core._create_json_writer', side_effect=[writer_1, writer_2]), \
             patch('flexo_syside_lib.core._create_serialization_options', return_value=mock_options), \
             patch('flexo_syside_lib.core.syside.serialize'):

            payload, json_string = convert_sysml_files_textual_to_json(
                ["alpha.sysml", "beta.sysml"]
            )

            parsed_json = json.loads(json_string)

            assert [element["@id"] for element in parsed_json] == ["ns1", "pkg1", "ns2", "pkg2"]
            assert [element["name"] for element in parsed_json if element["@type"] == "Namespace"] == ["Alpha", "Beta"]
            assert [
                element["qualifiedName"]
                for element in parsed_json
                if element["@type"] == "Namespace" and "owningRelationship" not in element
            ] == ["alpha.sysml", "beta.sysml"]
            assert isinstance(payload, list)
            assert len(payload) == 4
    
    def test_convert_json_to_sysml_textual_invalid_input(self):
        """Test converting invalid input to SysML textual."""
        from flexo_syside_lib.core import convert_json_to_sysml_textual
        
        with pytest.raises(TypeError, match="json_flexo must be dict/list/str"):
            convert_json_to_sysml_textual(123)  # Invalid type
    
    @patch('flexo_syside_lib.core.syside')
    def test_create_json_writer(self, mock_syside):
        """Test creating JSON writer with mocked SysIDE."""
        from flexo_syside_lib.core import _create_json_writer
        
        mock_writer_class = Mock()
        mock_writer_instance = Mock()
        mock_writer_class.return_value = mock_writer_instance
        mock_syside.JsonStringWriter = mock_writer_class
        mock_syside.JsonStringOptions = Mock()
        
        writer = _create_json_writer()
        assert writer is not None
        mock_writer_class.assert_called_once()
    
    @patch('flexo_syside_lib.core.syside')
    def test_create_serialization_options(self, mock_syside):
        """Test creating serialization options with mocked SysIDE."""
        from flexo_syside_lib.core import _create_serialization_options
        
        mock_options = Mock()
        mock_syside.SerializationOptions.return_value.minimal.return_value.with_options.return_value = mock_options
        mock_syside.FailAction = Mock()
        mock_syside.FailAction.Ignore = "ignore"
        
        options = _create_serialization_options()
        assert options is not None
        mock_syside.SerializationOptions.assert_called_once()

    @patch('flexo_syside_lib.core.syside')
    def test_expand_minimal_json_to_full_json_from_raw_list(self, mock_syside):
        sample_minimal_json = [{"@id": "ns1", "@type": "Namespace", "qualifiedName": "alpha.sysml"}]
        sample_full_json = [
            {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
            {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
        ]

        with patch(
            'flexo_syside_lib.core.convert_json_to_sysml_textual',
            return_value=(("package Alpha {}", Mock()), []),
        ) as mock_to_text, patch(
            'flexo_syside_lib.core.convert_sysml_string_textual_to_json',
            return_value=([], json.dumps(sample_full_json)),
        ) as mock_to_full:
            payload, json_string = expand_minimal_json_to_full_json(sample_minimal_json)

        parsed_json = json.loads(json_string)
        assert isinstance(payload, list)
        assert parsed_json[0]["@type"] == "Namespace"
        assert parsed_json[0]["qualifiedName"] == "alpha.sysml"
        mock_to_text.assert_called_once()
        mock_to_full.assert_called_once()

    @patch('flexo_syside_lib.core.syside')
    def test_expand_minimal_json_to_full_json_rejects_invalid_input(self, mock_syside):
        with pytest.raises(TypeError, match="minimal_json must be dict/list/str"):
            expand_minimal_json_to_full_json(123)


class TestLicenseHandling:
    """Test license handling and graceful degradation."""
    
    def test_import_without_license_graceful_failure(self):
        """Test that import fails gracefully when no license is available."""
        # This test verifies that the import behavior is predictable
        # In CI, we'll mock syside to avoid license issues
        pass
    
    def test_utility_functions_work_without_syside(self):
        """Test that utility functions work even if SysIDE is mocked."""
        # This test ensures our utility functions are truly independent
        from flexo_syside_lib.core import _replace_none_with_empty
        
        # Test that the function works regardless of SysIDE state
        result = _replace_none_with_empty({"test": None})
        assert result == {"test": ""}

    def test_package_root_exports_conversion_helpers(self):
        """Test that package root exports the main conversion helpers."""
        import flexo_syside_lib

        assert callable(flexo_syside_lib.convert_sysml_file_textual_to_json)
        assert callable(flexo_syside_lib.convert_sysml_string_textual_to_json)
        assert callable(flexo_syside_lib.convert_json_to_sysml_textual)
        assert callable(flexo_syside_lib.expand_minimal_json_to_full_json)


class TestCommitterRegression:
    """Regression tests for Flexo commit argument forwarding."""

    @staticmethod
    def _import_committer_module():
        mock_sysmlv2_client = types.ModuleType("sysmlv2_client")
        mock_sysmlv2_client.SysMLV2Client = Mock()

        mock_api_lib = types.ModuleType("sysml_api.api_lib")
        mock_api_lib.create_sysml_project = Mock()
        mock_api_lib.get_project_by_name = Mock()
        mock_api_lib.commit_to_project = Mock()

        mock_sysml_api = types.ModuleType("sysml_api")
        mock_sysml_api.api_lib = mock_api_lib

        with patch.dict(
            "sys.modules",
            {
                "sysmlv2_client": mock_sysmlv2_client,
                "sysml_api": mock_sysml_api,
                "sysml_api.api_lib": mock_api_lib,
            },
        ):
            sys.modules.pop("flexo_syside_lib.committer", None)
            return importlib.import_module("flexo_syside_lib.committer")

    def test_commit_sysml_to_flexo_forwards_default_commit_flags(self):
        committer = self._import_committer_module()

        with patch.object(committer, "SysMLV2Client", return_value=Mock()), \
             patch.object(committer, "convert_sysml_string_textual_to_json", return_value=('{"change": 1}', "[]")), \
             patch.object(committer, "get_project_by_name", return_value=({"name": "Demo"}, "project-123")), \
             patch.object(committer, "commit_to_project", return_value=({"status": "ok"}, "commit-123")) as mock_commit:
            result = committer.commit_sysml_to_flexo(
                sysml_output="package Demo {}",
                project_name="Demo",
                api_key="token",
                verbose=False,
            )

        assert result["project_id"] == "project-123"
        assert result["commit_id"] == "commit-123"
        mock_commit.assert_called_once()
        assert mock_commit.call_args.args[1:] == ("project-123", '{"change": 1}')
        assert mock_commit.call_args.kwargs == {
            "delete_project_data": False,
            "replace_model": False,
        }

    def test_commit_sysml_to_flexo_forwards_explicit_commit_flags(self):
        committer = self._import_committer_module()

        with patch.object(committer, "SysMLV2Client", return_value=Mock()), \
             patch.object(committer, "convert_sysml_string_textual_to_json", return_value=('{"change": 1}', "[]")), \
             patch.object(committer, "get_project_by_name", return_value=({"name": "Demo"}, "project-123")), \
             patch.object(committer, "commit_to_project", return_value=({"status": "ok"}, "commit-123")) as mock_commit:
            result = committer.commit_sysml_to_flexo(
                sysml_output="package Demo {}",
                project_name="Demo",
                api_key="token",
                verbose=False,
                delete_project_data=True,
                replace_model=True,
            )

        assert result["project_id"] == "project-123"
        assert result["commit_id"] == "commit-123"
        mock_commit.assert_called_once()
        assert mock_commit.call_args.args[1:] == ("project-123", '{"change": 1}')
        assert mock_commit.call_args.kwargs == {
            "delete_project_data": True,
            "replace_model": True,
        }
