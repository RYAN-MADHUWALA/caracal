"""
Unit tests for Caracal version module.
"""
import pytest
from caracal._version import __version__
import caracal


@pytest.mark.unit
class TestVersion:
    """Test version information."""
    
    def test_version_exists(self):
        """Test that __version__ is defined."""
        assert __version__ is not None
    
    def test_version_is_string(self):
        """Test that __version__ is a string."""
        assert isinstance(__version__, str)
    
    def test_version_not_empty(self):
        """Test that __version__ is not empty."""
        assert len(__version__) > 0
    
    def test_version_accessible_from_package(self):
        """Test that version is accessible from caracal package."""
        assert hasattr(caracal, '__version__')
        assert caracal.__version__ == __version__
    
    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        # Should have at least major.minor format
        parts = __version__.split('.')
        assert len(parts) >= 2
        
        # First part should be numeric (major version)
        assert parts[0].isdigit() or parts[0].startswith('0')
