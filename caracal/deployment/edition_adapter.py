"""Central adapter for deployment edition behavior resolution."""

from __future__ import annotations

from typing import Optional, Union

from caracal.deployment.edition import Edition, EditionManager


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
        return self._edition_manager.get_provider_client()

    def clear_cache(self) -> None:
        self._edition_manager.clear_cache()


def get_deployment_edition_adapter(
    *,
    edition_manager: Optional[EditionManager] = None,
) -> DeploymentEditionAdapter:
    return DeploymentEditionAdapter(edition_manager=edition_manager)
