"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Unit tests for EditionManager.

Tests edition detection, configuration persistence, provider client factory, and caching.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import toml

from caracal.deployment.edition import Edition, EditionManager
from caracal.deployment.exceptions import (
    InvalidEditionError,
    EditionConfigurationError,
    EditionDetectionError,
)


class TestEditionDetection:
    """Test edition detection with fallback chain."""
    
    def test_get_edition_from_config_file(self, temp_dir):
        """Test edition detection from config file."""
        # Create config file
        config_file = temp_dir / "config.toml"
        config = {
            "edition": {
                "current": "enterprise",
                "gateway_url": "https://gateway.example.com",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                edition = manager.get_edition()
                
                assert edition == Edition.ENTERPRISE
    
    def test_get_edition_defaults_to_opensource(self, temp_dir):
        """Test edition defaults to OPENSOURCE when no config."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                manager = EditionManager()
                edition = manager.get_edition()
                
                assert edition == Edition.OPENSOURCE
    
    def test_get_edition_auto_detects_from_gateway_url(self, temp_dir):
        """Test edition auto-detection from gateway URL in config."""
        # Create config file with gateway URL but no edition
        config_file = temp_dir / "config.toml"
        config = {
            "edition": {
                "gateway_url": "https://gateway.example.com"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                edition = manager.get_edition()
                
                assert edition == Edition.ENTERPRISE
    
    def test_get_edition_auto_detects_from_env_var(self, temp_dir):
        """Test edition auto-detection from environment variable."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                with patch.dict(os.environ, {'CARACAL_GATEWAY_URL': 'https://gateway.example.com'}):
                    manager = EditionManager()
                    edition = manager.get_edition()
                    
                    assert edition == Edition.ENTERPRISE
    
    def test_get_edition_auto_detects_from_enterprise_module(self, temp_dir):
        """Test edition auto-detection from enterprise module presence."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                # Mock the enterprise module import
                with patch.dict('sys.modules', {'caracal.enterprise': MagicMock()}):
                    manager = EditionManager()
                    edition = manager.get_edition()
                    
                    assert edition == Edition.ENTERPRISE
    
    def test_get_edition_handles_invalid_config_file(self, temp_dir):
        """Test invalid config file falls back to auto-detection."""
        # Create invalid config file
        config_file = temp_dir / "config.toml"
        config_file.write_text("invalid toml content {{{")
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                edition = manager.get_edition()
                
                # Should fall back to default (OPENSOURCE)
                assert edition == Edition.OPENSOURCE
    
    def test_get_edition_handles_missing_edition_in_config(self, temp_dir):
        """Test config file without edition section falls back to auto-detection."""
        # Create config file without edition section
        config_file = temp_dir / "config.toml"
        config = {"other": {"setting": "value"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                edition = manager.get_edition()
                
                assert edition == Edition.OPENSOURCE
    
    def test_get_edition_handles_invalid_edition_value(self, temp_dir):
        """Test invalid edition value in config falls back to auto-detection."""
        # Create config file with invalid edition
        config_file = temp_dir / "config.toml"
        config = {
            "edition": {
                "current": "invalid_edition"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                edition = manager.get_edition()
                
                # Should fall back to auto-detection (OPENSOURCE)
                assert edition == Edition.OPENSOURCE


class TestEditionCaching:
    """Test edition caching to avoid repeated file I/O."""
    
    def test_get_edition_caches_result(self, temp_dir):
        """Test that edition detection result is cached."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "enterprise", "gateway_url": "https://gateway.example.com"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                
                # First call should read from file
                edition1 = manager.get_edition()
                
                # Modify config file
                config["edition"]["current"] = "opensource"
                config["edition"].pop("gateway_url", None)
                with open(config_file, "w") as f:
                    toml.dump(config, f)
                
                # Second call should return cached value
                edition2 = manager.get_edition()
                
                assert edition1 == edition2 == Edition.ENTERPRISE
    
    def test_clear_cache_forces_redetection(self, temp_dir):
        """Test that clear_cache forces edition redetection."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "enterprise", "gateway_url": "https://gateway.example.com"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                
                # First call
                edition1 = manager.get_edition()
                assert edition1 == Edition.ENTERPRISE
                
                # Modify config file
                config["edition"]["current"] = "opensource"
                config["edition"].pop("gateway_url", None)
                with open(config_file, "w") as f:
                    toml.dump(config, f)
                
                # Clear cache
                manager.clear_cache()
                
                # Should detect new edition
                edition2 = manager.get_edition()
                assert edition2 == Edition.OPENSOURCE


class TestEditionConfiguration:
    """Test edition configuration persistence."""
    
    def test_set_edition_creates_config_directory(self, temp_dir):
        """Test that set_edition creates config directory if it doesn't exist."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(Edition.OPENSOURCE)
                
                assert config_dir.exists()
                assert config_dir.stat().st_mode & 0o777 == 0o700
    
    def test_set_edition_persists_to_config_file(self, temp_dir):
        """Test that set_edition persists edition to config file."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(Edition.OPENSOURCE)
                
                # Read config file
                assert config_file.exists()
                config = toml.load(config_file)
                
                assert config["edition"]["current"] == "opensource"
                assert "updated_at" in config["edition"]
    
    def test_set_edition_enterprise_requires_gateway_url(self, temp_dir):
        """Test that setting Enterprise edition requires gateway URL."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                
                with pytest.raises(EditionConfigurationError, match="Gateway URL is required"):
                    manager.set_edition(Edition.ENTERPRISE)
    
    def test_set_edition_enterprise_stores_gateway_url(self, temp_dir):
        """Test that setting Enterprise edition stores gateway URL."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(
                    Edition.ENTERPRISE,
                    gateway_url="https://gateway.example.com",
                    gateway_token="test_token"
                )
                
                # Read config file
                config = toml.load(config_file)
                
                assert config["edition"]["current"] == "enterprise"
                assert config["edition"]["gateway_url"] == "https://gateway.example.com"
                assert config["edition"]["gateway_token"] == "test_token"
    
    def test_set_edition_opensource_removes_gateway_config(self, temp_dir):
        """Test that setting Open Source edition removes gateway configuration."""
        config_dir = temp_dir / ".caracal"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"
        
        # Create config with gateway settings
        config = {
            "edition": {
                "current": "enterprise",
                "gateway_url": "https://gateway.example.com",
                "gateway_token": "test_token"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(Edition.OPENSOURCE)
                
                # Read config file
                config = toml.load(config_file)
                
                assert config["edition"]["current"] == "opensource"
                assert "gateway_url" not in config["edition"]
                assert "gateway_token" not in config["edition"]
    
    def test_set_edition_updates_cache(self, temp_dir):
        """Test that set_edition updates the cached edition."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                
                # Set edition
                manager.set_edition(Edition.OPENSOURCE)
                
                # Get edition should return cached value without reading file
                edition = manager.get_edition()
                assert edition == Edition.OPENSOURCE
    
    def test_set_edition_preserves_existing_config(self, temp_dir):
        """Test that set_edition preserves other config sections."""
        config_dir = temp_dir / ".caracal"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"
        
        # Create config with other sections
        config = {
            "other": {"setting": "value"},
            "edition": {"current": "opensource"}
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(
                    Edition.ENTERPRISE,
                    gateway_url="https://gateway.example.com"
                )
                
                # Read config file
                config = toml.load(config_file)
                
                assert config["edition"]["current"] == "enterprise"
                assert config["other"]["setting"] == "value"
    
    def test_set_edition_handles_corrupted_config(self, temp_dir):
        """Test that set_edition handles corrupted config file."""
        config_dir = temp_dir / ".caracal"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.toml"
        
        # Create corrupted config file
        config_file.write_text("invalid toml {{{")
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                
                # Should not raise exception, should create new config
                manager.set_edition(Edition.OPENSOURCE)
                
                # Read config file
                config = toml.load(config_file)
                assert config["edition"]["current"] == "opensource"
    
    def test_set_edition_raises_on_invalid_edition(self, temp_dir):
        """Test that set_edition raises InvalidEditionError for invalid edition."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            manager = EditionManager()
            
            with pytest.raises(InvalidEditionError):
                manager.set_edition("invalid")  # type: ignore
    
    def test_set_edition_sets_file_permissions(self, temp_dir):
        """Test that set_edition sets proper file permissions."""
        config_dir = temp_dir / ".caracal"
        config_file = config_dir / "config.toml"
        
        with patch.object(EditionManager, 'CONFIG_DIR', config_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                manager.set_edition(Edition.OPENSOURCE)
                
                # Check file permissions (0600)
                assert config_file.stat().st_mode & 0o777 == 0o600


class TestEditionHelpers:
    """Test edition helper methods."""
    
    def test_is_enterprise_returns_true_for_enterprise(self, temp_dir):
        """Test is_enterprise returns True for enterprise edition."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "enterprise", "gateway_url": "https://gateway.example.com"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                assert manager.is_enterprise() is True
                assert manager.is_opensource() is False
    
    def test_is_opensource_returns_true_for_opensource(self, temp_dir):
        """Test is_opensource returns True for open source edition."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "opensource"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                assert manager.is_opensource() is True
                assert manager.is_enterprise() is False


class TestProviderClientFactory:
    """Test provider client factory method."""
    
    def test_get_provider_client_returns_broker_for_opensource(self, temp_dir):
        """Test get_provider_client returns Broker for open source edition."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "opensource"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                client = manager.get_provider_client()
                
                from caracal.deployment.broker import Broker
                assert isinstance(client, Broker)
    
    def test_get_provider_client_returns_gateway_for_enterprise(self, temp_dir):
        """Test get_provider_client returns GatewayClient for enterprise edition."""
        config_file = temp_dir / "config.toml"
        config = {"edition": {"current": "enterprise", "gateway_url": "https://gateway.example.com"}}
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                client = manager.get_provider_client()
                
                from caracal.deployment.gateway_client import GatewayClient
                assert isinstance(client, GatewayClient)


class TestGatewayConfiguration:
    """Test gateway configuration retrieval methods."""
    
    def test_get_gateway_url_returns_configured_url(self, temp_dir):
        """Test get_gateway_url returns configured URL."""
        config_file = temp_dir / "config.toml"
        config = {
            "edition": {
                "current": "enterprise",
                "gateway_url": "https://gateway.example.com"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                url = manager.get_gateway_url()
                
                assert url == "https://gateway.example.com"
    
    def test_get_gateway_url_returns_none_when_not_configured(self, temp_dir):
        """Test get_gateway_url returns None when not configured."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                manager = EditionManager()
                url = manager.get_gateway_url()
                
                assert url is None
    
    def test_get_gateway_token_returns_configured_token(self, temp_dir):
        """Test get_gateway_token returns configured token."""
        config_file = temp_dir / "config.toml"
        config = {
            "edition": {
                "current": "enterprise",
                "gateway_url": "https://gateway.example.com",
                "gateway_token": "test_jwt_token"
            }
        }
        with open(config_file, "w") as f:
            toml.dump(config, f)
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                token = manager.get_gateway_token()
                
                assert token == "test_jwt_token"
    
    def test_get_gateway_token_returns_none_when_not_configured(self, temp_dir):
        """Test get_gateway_token returns None when not configured."""
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', temp_dir / "config.toml"):
                manager = EditionManager()
                token = manager.get_gateway_token()
                
                assert token is None
    
    def test_get_gateway_url_handles_corrupted_config(self, temp_dir):
        """Test get_gateway_url handles corrupted config file."""
        config_file = temp_dir / "config.toml"
        config_file.write_text("invalid toml {{{")
        
        with patch.object(EditionManager, 'CONFIG_DIR', temp_dir):
            with patch.object(EditionManager, 'CONFIG_FILE', config_file):
                manager = EditionManager()
                url = manager.get_gateway_url()
                
                assert url is None
