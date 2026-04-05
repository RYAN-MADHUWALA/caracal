"""Grouped migration-oriented SDK surface."""

from caracal_sdk.authority_client import AuthorityClient
from caracal_sdk.async_authority_client import AsyncAuthorityClient
from caracal_sdk.secrets import SecretsAdapter, SecretsAdapterError

__all__ = [
    "AuthorityClient",
    "AsyncAuthorityClient",
    "SecretsAdapter",
    "SecretsAdapterError",
]
