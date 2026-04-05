"""Hard-cut validation tests for configuration loading."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from caracal.config.settings import (
    CaracalConfig,
    InvalidConfigurationError,
    MerkleConfig,
    StorageConfig,
    _validate_config,
)


def _base_config() -> CaracalConfig:
    return CaracalConfig(storage=StorageConfig(backup_dir="/tmp/caracal-test-backups"))


@pytest.mark.unit
def test_validate_config_rejects_software_merkle_backend_in_hardcut() -> None:
    config = _base_config()
    config.merkle = MerkleConfig(
        signing_backend="software",
        private_key_path="/tmp/merkle_signing_key.pem",
    )

    with patch.dict(os.environ, {"CARACAL_HARDCUT_MODE": "1"}, clear=False):
        with pytest.raises(InvalidConfigurationError, match="must be 'vault'"):
            _validate_config(config)


@pytest.mark.unit
def test_validate_config_requires_vault_merkle_refs_in_hardcut() -> None:
    config = _base_config()
    config.merkle = MerkleConfig(signing_backend="vault")

    with patch.dict(os.environ, {"CARACAL_HARDCUT_MODE": "1"}, clear=False):
        with pytest.raises(InvalidConfigurationError, match="vault_key_ref"):
            _validate_config(config)


@pytest.mark.unit
def test_validate_config_accepts_vault_merkle_refs_in_hardcut() -> None:
    config = _base_config()
    config.merkle = MerkleConfig(
        signing_backend="vault",
        vault_key_ref="vault://caracal/runtime/merkle-signing",
        vault_public_key_ref="vault://caracal/runtime/merkle-signing.public",
    )

    with patch.dict(os.environ, {"CARACAL_HARDCUT_MODE": "1"}, clear=False):
        _validate_config(config)
