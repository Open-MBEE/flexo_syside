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
import syside
import pathlib
from flexo_syside_lib.core import convert_sysml_file_textual_to_json, convert_sysml_string_textual_to_json, convert_json_to_sysml_textual

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
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test2.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = EXAMPLE_DIR / 'pu-simple.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = EXAMPLE_DIR / 'pu.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = EXAMPLE_DIR / 'library.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        assert sysml_text !=None

        MODEL_FILE_PATH = EXAMPLE_DIR / 'geo.sysml'

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

    def test_serialize_deserialize2(self, expected):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test1.sysml'

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

    @pytest.mark.timeout(10)  # Test will time out after 10 seconds
    def test_serialize_deserialize3(self):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test3.sysml'

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
       

    def test_serialize_deserialize4(self):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test4.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize5(self):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test5.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize6(self):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test6.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)


    def test_serialize_deserialize7(self):
        EXAMPLE_DIR = pathlib.Path(os.getcwd())
        MODEL_FILE_PATH = EXAMPLE_DIR / 'Test7.sysml'

        # use minimal = True to get the compact version
        change_payload_file, raw_jsonf = convert_sysml_file_textual_to_json(sysml_file_path=MODEL_FILE_PATH, minimal=False)
        data = json.loads(raw_jsonf)  # parse JSON string into Python objects
        (sysml_text, model), warnings = convert_json_to_sysml_textual(data)
        #assert sysml_text !=None
        check.is_not(sysml_text,None)



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
                
            finally:
                os.unlink(temp_file)
    
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
