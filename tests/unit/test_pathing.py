"""
Unit tests for Caracal pathing module.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from caracal.pathing import source_of, ensure_source_tree


@pytest.mark.unit
class TestSourceOf:
    """Test source_of function."""
    
    def test_source_of_simple_path(self):
        """Test source_of with a simple path."""
        path = Path("/home/user/file.txt")
        result = source_of(path)
        assert result == Path("/home/user")
    
    def test_source_of_nested_path(self):
        """Test source_of with nested path."""
        path = Path("/a/b/c/d/file.txt")
        result = source_of(path)
        assert result == Path("/a/b/c/d")
    
    def test_source_of_single_component(self):
        """Test source_of with single component path."""
        path = Path("file.txt")
        result = source_of(path)
        assert result == path
    
    def test_source_of_root(self):
        """Test source_of with root path."""
        path = Path("/")
        result = source_of(path)
        assert result == path
    
    def test_source_of_relative_path(self):
        """Test source_of with relative path."""
        path = Path("dir/subdir/file.txt")
        result = source_of(path)
        assert result == Path("dir/subdir")


@pytest.mark.unit
class TestEnsureSourceTree:
    """Test ensure_source_tree function."""
    
    def test_ensure_source_tree_creates_directory(self):
        """Test that ensure_source_tree creates a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_dir"
            assert not test_path.exists()
            
            ensure_source_tree(test_path)
            
            assert test_path.exists()
            assert test_path.is_dir()
    
    def test_ensure_source_tree_creates_nested_directories(self):
        """Test that ensure_source_tree creates nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "a" / "b" / "c" / "d"
            assert not test_path.exists()
            
            ensure_source_tree(test_path)
            
            assert test_path.exists()
            assert test_path.is_dir()
            assert (Path(tmpdir) / "a").exists()
            assert (Path(tmpdir) / "a" / "b").exists()
            assert (Path(tmpdir) / "a" / "b" / "c").exists()
    
    def test_ensure_source_tree_existing_directory(self):
        """Test that ensure_source_tree handles existing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "existing"
            test_path.mkdir()
            
            # Should not raise error
            ensure_source_tree(test_path)
            
            assert test_path.exists()
            assert test_path.is_dir()
    
    def test_ensure_source_tree_partial_existing(self):
        """Test ensure_source_tree with partially existing path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create partial path
            partial = Path(tmpdir) / "a" / "b"
            partial.mkdir(parents=True)
            
            # Create full path
            full_path = partial / "c" / "d"
            ensure_source_tree(full_path)
            
            assert full_path.exists()
            assert full_path.is_dir()


@pytest.mark.unit
class TestPathingIntegration:
    """Integration tests for pathing functions."""
    
    def test_source_of_and_ensure_source_tree_together(self):
        """Test using source_of and ensure_source_tree together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "a" / "b" / "file.txt"
            dir_path = source_of(file_path)
            
            ensure_source_tree(dir_path)
            
            assert dir_path.exists()
            assert dir_path.is_dir()
            
            # Now we can create the file
            file_path.touch()
            assert file_path.exists()
