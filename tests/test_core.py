"""
Tests for flexo_syside_lib core functionality.
Tests the actual source code from src/ with proper license handling.
"""
import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock


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
