"""Central adapter for deployment edition behavior resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union

from caracal.deployment.edition import Edition, EditionManager
from caracal.deployment.exceptions import EditionConfigurationError


class DeploymentEditionAdapter:
    """Single adapter surface for edition-aware behavior in runtime and UI flows."""

    def __init__(self, edition_manager: Optional[EditionManager] = None) -> None:
        self._edition_manager = edition_manager or EditionManager()

    def get_edition(self) -> Edition:
        return self._edition_manager.get_edition()

    def set_edition(
        self,
        edition: Edition,
        gateway_url: Optional[str] = None,
        gateway_token: Optional[str] = None,
    ) -> None:
        self._edition_manager.set_edition(
            edition,
            gateway_url=gateway_url,
            gateway_token=gateway_token,
        )

    def is_enterprise(self) -> bool:
        return self.get_edition() == Edition.ENTERPRISE

    def is_opensource(self) -> bool:
        return self.get_edition() == Edition.OPENSOURCE

    def get_gateway_url(self) -> Optional[str]:
        return self._edition_manager.get_gateway_url()

    def get_gateway_token(self) -> Optional[str]:
        return self._edition_manager.get_gateway_token()

    def get_provider_client(self) -> Union["Broker", "GatewayClient"]:
        from caracal.deployment.broker import Broker
        from caracal.deployment.gateway_client import GatewayClient

        if self.is_enterprise():
            gateway_url = self.get_gateway_url()
            if not gateway_url:
                raise EditionConfigurationError(
                    "Enterprise execution requires a gateway URL "
                    "(CARACAL_ENTERPRISE_URL/CARACAL_GATEWAY_ENDPOINT/CARACAL_GATEWAY_URL)."
                )
            return GatewayClient(gateway_url=gateway_url)
        return Broker()

    def clear_cache(self) -> None:
        self._edition_manager.clear_cache()

    def assert_enterprise_license_valid(self) -> None:
        """Fail closed when enterprise mode is active but license state is invalid."""
        if not self.is_enterprise():
            return

        try:
            from caracal.enterprise.license import load_enterprise_config

            cfg = load_enterprise_config()
        except Exception as exc:
            raise EditionConfigurationError(
                "Enterprise startup requires a readable persisted enterprise license configuration."
            ) from exc

        if not isinstance(cfg, dict):
            raise EditionConfigurationError(
                "Enterprise startup requires a valid persisted enterprise license configuration."
            )

        if not bool(cfg.get("valid", False)):
            raise EditionConfigurationError(
                "Enterprise startup requires a valid enterprise license."
            )

        license_key = str(cfg.get("license_key") or "").strip()
        if not license_key:
            raise EditionConfigurationError(
                "Enterprise startup requires a persisted enterprise license key."
            )

        expires_at_raw = str(cfg.get("expires_at") or "").strip()
        if expires_at_raw:
            try:
                normalized = expires_at_raw.replace("Z", "+00:00")
                expires_at = datetime.fromisoformat(normalized)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                else:
                    expires_at = expires_at.astimezone(timezone.utc)
            except ValueError as exc:
                raise EditionConfigurationError(
                    "Enterprise startup requires a parseable license expiry timestamp."
                ) from exc

            if expires_at <= datetime.now(timezone.utc):
                raise EditionConfigurationError(
                    "Enterprise startup requires a non-expired enterprise license."
                )


def get_deployment_edition_adapter(
    *,
    edition_manager: Optional[EditionManager] = None,
    enforce_startup_license_validation: bool = False,
) -> DeploymentEditionAdapter:
    adapter = DeploymentEditionAdapter(edition_manager=edition_manager)
    if enforce_startup_license_validation:
        adapter.assert_enterprise_license_valid()
    return adapter
