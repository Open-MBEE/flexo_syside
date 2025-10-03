# Optionally import main classes/functions here for API exposure
# Import only if dependencies are available to avoid CI issues
try:
    from .core import convert_sysml_file_textual_to_json
except ImportError:
    # In CI environments where dependencies might not be available
    pass

__version__ = "0.1.0"
