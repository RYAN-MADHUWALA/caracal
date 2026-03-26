"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Enterprise module — mixed real implementations and redirected stubs.

Modules kept here (real implementation logic used by TUI/gateway):
    - ``license.py``      — EnterpriseLicenseValidator, config helpers
    - ``sync.py``          — EnterpriseSyncClient
    - ``exceptions.py``    — EnterpriseFeatureRequired

Extension stubs (moved to ``caracal_sdk.enterprise``):
    - ComplianceExtension, AnalyticsExtension, WorkflowsExtension,
      SSOExtension, LicenseExtension, SyncExtension

New code should import extensions from ``caracal_sdk.enterprise.*``.
"""

import warnings

# --- Real implementations (remain here) -----------------------------------

from caracal.enterprise.exceptions import EnterpriseFeatureRequired
from caracal.enterprise.license import (
    EnterpriseLicenseValidator,
    LicenseValidationResult,
    load_enterprise_config,
    save_enterprise_config,
    clear_enterprise_config,
)

# --- Extension stubs (redirect to sdk/enterprise/) -------------------------
# These emit a deprecation warning on import.

def __getattr__(name: str):
    _redirected = {
        "ComplianceExtension": "caracal_sdk.enterprise.compliance",
        "AnalyticsExtension": "caracal_sdk.enterprise.analytics",
        "WorkflowsExtension": "caracal_sdk.enterprise.workflows",
        "SSOExtension": "caracal_sdk.enterprise.sso",
        "LicenseExtension": "caracal_sdk.enterprise.license",
        "SyncExtension": "caracal_sdk.enterprise.sync",
    }
    if name in _redirected:
        import importlib
        warnings.warn(
            f"Importing {name} from caracal.enterprise is deprecated. "
            f"Use {_redirected[name]} instead. "
            "Old import paths will be removed in v0.4.",
            DeprecationWarning,
            stacklevel=2,
        )
        module = importlib.import_module(_redirected[name])
        return getattr(module, name)
    raise AttributeError(f"module 'caracal.enterprise' has no attribute {name!r}")


__all__ = [
    # Real implementations
    "EnterpriseFeatureRequired",
    "EnterpriseLicenseValidator",
    "LicenseValidationResult",
    "load_enterprise_config",
    "save_enterprise_config",
    "clear_enterprise_config",
    # Redirected stubs
    "ComplianceExtension",
    "AnalyticsExtension",
    "WorkflowsExtension",
    "SSOExtension",
    "LicenseExtension",
    "SyncExtension",
]
