# Optionally import main classes/functions here for API exposure
# Import only if dependencies are available to avoid CI issues
try:
    from .core import convert_sysml_file_textual_to_json
    from .core import convert_sysml_string_textual_to_json
    from .core import convert_json_to_sysml_textual
    from .core import expand_minimal_json_to_full_json
    from .core import expand_backend_elements_for_api
    from .api_expand import merge_expanded_elements_for_api
except ImportError:
    # In CI environments where dependencies might not be available
    pass

__version__ = "0.1.0"
