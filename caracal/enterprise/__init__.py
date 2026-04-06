"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Enterprise module exports for OSS runtime enterprise helpers.

Modules kept here (real implementation logic used by TUI/gateway):
    - ``license.py``      — EnterpriseLicenseValidator, config helpers
    - ``sync.py``          — EnterpriseSyncClient
    - ``exceptions.py``    — EnterpriseFeatureRequired

SDK extension entrypoints are exposed from ``caracal_sdk.enterprise``.
"""

# --- Real implementations (remain here) -----------------------------------

from caracal.enterprise.exceptions import EnterpriseFeatureRequired
from caracal.enterprise.license import (
    EnterpriseLicenseValidator,
    LicenseValidationResult,
    load_enterprise_config,
    save_enterprise_config,
    clear_enterprise_config,
)

__all__ = [
    "EnterpriseFeatureRequired",
    "EnterpriseLicenseValidator",
    "LicenseValidationResult",
    "load_enterprise_config",
    "save_enterprise_config",
    "clear_enterprise_config",
]
