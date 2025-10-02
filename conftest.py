"""
Pytest configuration for flexo_syside tests.
Handles SysIDE license setup and mocking for CI environments.
"""
import pytest
import os
import sys
from unittest.mock import patch, Mock


def setup_syside_license():
    """Set up SysIDE license if available."""
    license_key = os.environ.get('SYSIDE_LICENSE_KEY')
    if license_key:
        try:
            import syside_license
            syside_license.check(license_key)
            return True
        except Exception as e:
            print(f"Failed to set up SysIDE license: {e}")
            return False
    return False


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with SysIDE license or mocking."""
    # Try to set up real license first
    license_available = setup_syside_license()
    
    if not license_available:
        # Mock syside module for CI/local testing without license
        mock_syside = Mock()
        
        # Mock the classes and functions that core.py uses
        mock_syside.JsonStringWriter = Mock()
        mock_syside.JsonStringOptions = Mock()
        mock_syside.SerializationOptions = Mock()
        mock_syside.FailAction = Mock()
        mock_syside.FailAction.Ignore = "ignore"
        mock_syside.load_model = Mock()
        mock_syside.try_load_model = Mock()
        mock_syside.serialize = Mock()
        
        # Patch syside module
        with patch.dict('sys.modules', {'syside': mock_syside}):
            yield
    else:
        # License is available, run tests normally
        yield


@pytest.fixture
def sample_sysml_content():
    """Provide sample SysML content for testing."""
    return '''
package TestPackage {
    part def Component {
        attribute name: String;
        attribute value: Real;
    }
    
    part def System {
        part components: Component[0..*];
    }
    
    part def Context {
        part mainSystem: System;
    }
}
'''


@pytest.fixture
def sample_json_data():
    """Provide sample JSON data for testing."""
    return [
        {"@id": "ns1", "@type": "Namespace", "qualifiedName": "2020-01-01T00:00:00Z"},
        {"@id": "comp1", "@type": "Component", "name": "TestComponent"},
        {"@id": "sys1", "@type": "System", "components": [{"@id": "comp1"}]}
    ]
