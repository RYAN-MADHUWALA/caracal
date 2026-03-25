"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Unit tests for ModeManager.

Tests mode detection, configuration persistence, and caching.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

from caracal.deployment.mode import Mode, ModeManager
from caracal.deployment.exceptions import (
    InvalidModeError,
    ModeConfigurationError,
    ModeDetectionError,
)


class TestModeDetection:
    """Test mode detection with fallback chain."""
    
    def test_get_mode_from_environment_variable(self, temp_dir):
        """Test mode detection from environment variable."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'dev'}):
                manager = ModeManager()
                mode = manager.get_mode()
                
                assert mode == Mode.DEVELOPMENT
    
    def test_get_mode_from_config_file(self, temp_dir):
        """Test mode detection from config file."""
        # Create config file
        config_file = temp_dir / "config.toml"
        config = {
            "mode": {
                "current": "dev",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                # Ensure no environment variable
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    assert mode == Mode.DEVELOPMENT
    
    def test_get_mode_defaults_to_user_mode(self, temp_dir):
        """Test mode defaults to USER when no config or env var."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                # Ensure no environment variable
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    assert mode == Mode.USER
    
    def test_get_mode_env_var_overrides_config(self, temp_dir):
        """Test environment variable takes precedence over config file."""
        # Create config file with USER mode
        config_file = temp_dir / "config.toml"
        config = {
            "mode": {
                "current": "user",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                # Set environment variable to DEV
                with patch.dict(os.environ, {'CARACAL_MODE': 'dev'}):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    assert mode == Mode.DEVELOPMENT
    
    def test_get_mode_handles_invalid_env_var(self, temp_dir):
        """Test invalid environment variable falls back to config/default."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                with patch.dict(os.environ, {'CARACAL_MODE': 'invalid'}):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    # Should fall back to default (USER)
                    assert mode == Mode.USER
    
    def test_get_mode_handles_invalid_config_file(self, temp_dir):
        """Test invalid config file falls back to default."""
        # Create invalid config file
        config_file = temp_dir / "config.toml"
        config_file.write_text("invalid toml content {{{")
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    # Should fall back to default (USER)
                    assert mode == Mode.USER
    
    def test_get_mode_handles_missing_mode_in_config(self, temp_dir):
        """Test config file without mode section falls back to default."""
        # Create config file without mode section
        config_file = temp_dir / "config.toml"
        config = {"other": {"setting": "value"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    mode = manager.get_mode()
                    
                    assert mode == Mode.USER


class TestModeCaching:
    """Test mode caching to avoid repeated file I/O."""
    
    def test_get_mode_caches_result(self, temp_dir):
        """Test that mode detection result is cached."""
        config_file = temp_dir / "config.toml"
        config = {"mode": {"current": "dev"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    
                    # First call should read from file
                    mode1 = manager.get_mode()
                    
                    # Modify config file
                    config["mode"]["current"] = "user"
                    with open(config_file, "w") as f:
                        toml.dump(config, f)
                    
                    # Second call should return cached value
                    mode2 = manager.get_mode()
                    
                    assert mode1 == mode2 == Mode.DEVELOPMENT
    
    def test_clear_cache_forces_redetection(self, temp_dir):
        """Test that clear_cache forces mode redetection."""
        config_file = temp_dir / "config.toml"
        config = {"mode": {"current": "dev"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                with patch.dict(os.environ, {}, clear=True):
                    manager = ModeManager()
                    
                    # First call
                    mode1 = manager.get_mode()
                    assert mode1 == Mode.DEVELOPMENT
                    
                    # Modify config file
                    config["mode"]["current"] = "user"
                    with open(config_file, "w") as f:
                        toml.dump(config, f)
                    
                    # Clear cache
                    manager.clear_cache()
                    
                    # Should detect new mode
                    mode2 = manager.get_mode()
                    assert mode2 == Mode.USER


class TestModeConfiguration:
    """Test mode configuration persistence."""
    
    def test_set_mode_creates_config_directory(self, temp_dir):
        """Test that set_mode creates config directory if it doesn't exist."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                manager.set_mode(Mode.DEVELOPMENT)
                
                assert config_dir.exists()
                assert config_dir.stat().st_mode & 0o777 == 0o700
    
    def test_set_mode_persists_to_config_file(self, temp_dir):
        """Test that set_mode persists mode to config file."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                manager.set_mode(Mode.DEVELOPMENT)
                
                # Read config file
                assert config_file.exists()
                config = toml.load(config_file)
                
                assert config["mode"]["current"] == "dev"
                assert "updated_at" in config["mode"]
    
    def test_set_mode_updates_cache(self, temp_dir):
        """Test that set_mode updates the cached mode."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                
                # Set mode
                manager.set_mode(Mode.DEVELOPMENT)
                
                # Get mode should return cached value without reading file
                mode = manager.get_mode()
                assert mode == Mode.DEVELOPMENT
    
    def test_set_mode_preserves_existing_config(self, temp_dir):
        """Test that set_mode preserves other config sections."""
        config_dir = temp_dir / ".caracal"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"
        
        # Create config with other sections
        config = {
            "other": {"setting": "value"},
            "mode": {"current": "user"}
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                manager.set_mode(Mode.DEVELOPMENT)
                
                # Read config file
                config = toml.load(config_file)
                
                assert config["mode"]["current"] == "dev"
                assert config["other"]["setting"] == "value"
    
    def test_set_mode_handles_corrupted_config(self, temp_dir):
        """Test that set_mode handles corrupted config file."""
        config_dir = temp_dir / ".caracal"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"
        
        # Create corrupted config file
        config_file.write_text("invalid toml {{{")
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                
                # Should not raise exception, should create new config
                manager.set_mode(Mode.DEVELOPMENT)
                
                # Read config file
                config = toml.load(config_file)
                assert config["mode"]["current"] == "dev"
    
    def test_set_mode_raises_on_invalid_mode(self, temp_dir):
        """Test that set_mode raises InvalidModeError for invalid mode."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            manager = ModeManager()
            
            with pytest.raises(InvalidModeError):
                manager.set_mode("invalid")  # type: ignore
    
    def test_set_mode_sets_file_permissions(self, temp_dir):
        """Test that set_mode sets proper file permissions."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(ModeManager, 'CONFIG_DIR', config_dir):
            with patch.object(ModeManager, 'CONFIG_FILE', config_file):
                manager = ModeManager()
                manager.set_mode(Mode.DEVELOPMENT)
                
                # Check file permissions (0600)
                assert config_file.stat().st_mode & 0o777 == 0o600


class TestModeHelpers:
    """Test mode helper methods."""
    
    def test_is_dev_mode_returns_true_for_dev(self, temp_dir):
        """Test is_dev_mode returns True for development mode."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'dev'}):
                manager = ModeManager()
                assert manager.is_dev_mode() is True
                assert manager.is_user_mode() is False
    
    def test_is_user_mode_returns_true_for_user(self, temp_dir):
        """Test is_user_mode returns True for user mode."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'user'}):
                manager = ModeManager()
                assert manager.is_user_mode() is True
                assert manager.is_dev_mode() is False


class TestCodePathResolution:
    """Test code path resolution based on mode."""
    
    def test_get_code_path_returns_path(self, temp_dir):
        """Test get_code_path returns a valid path."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'user'}):
                manager = ModeManager()
                code_path = manager.get_code_path()
                
                assert isinstance(code_path, Path)
                assert code_path.exists()
    
    def test_get_code_path_dev_mode_returns_repo_path(self, temp_dir):
        """Test get_code_path in dev mode returns repository path."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'dev'}):
                manager = ModeManager()
                code_path = manager.get_code_path()
                
                # Should contain caracal package
                assert code_path.name == "caracal"
                assert (code_path / "__init__.py").exists()
    
    def test_get_code_path_user_mode_returns_package_path(self, temp_dir):
        """Test get_code_path in user mode returns installed package path."""
        with patch.object(ModeManager, 'CONFIG_DIR', temp_dir):
            with patch.dict(os.environ, {'CARACAL_MODE': 'user'}):
                manager = ModeManager()
                code_path = manager.get_code_path()
                
                # Should be the caracal package directory
                assert code_path.name == "caracal"
                assert (code_path / "__init__.py").exists()
