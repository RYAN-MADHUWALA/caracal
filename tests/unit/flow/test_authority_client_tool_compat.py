"""Unit tests for legacy AuthorityClient tool-call compatibility paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("aiohttp")

from caracal_sdk._compat import SDKConfigurationError
from caracal_sdk.authority_client import AuthorityClient


_MANDATE_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.unit
def test_legacy_authority_client_call_tool_routes_to_canonical_endpoint() -> None:
    client = AuthorityClient(base_url="http://localhost:8000")
    client._make_request = Mock(return_value={"success": True})

    with pytest.warns(DeprecationWarning, match="non-canonical"):
        result = client.call_tool(
            tool_name="tool.echo",
            mandate_id=_MANDATE_ID,
            tool_args={"payload": "ok"},
            metadata={"source": "legacy"},
        )

    assert result == {"success": True}
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="/mcp/tool/call",
        data={
            "tool_id": "tool.echo",
            "mandate_id": _MANDATE_ID,
            "tool_args": {"payload": "ok"},
            "metadata": {"source": "legacy"},
        },
    )
    client.close()


@pytest.mark.unit
def test_legacy_authority_client_call_tool_rejects_principal_id() -> None:
    client = AuthorityClient(base_url="http://localhost:8000")

    with pytest.raises(SDKConfigurationError, match="principal_id"):
        client.call_tool(
            tool_id="tool.echo",
            mandate_id=_MANDATE_ID,
            metadata={"principal_id": "forbidden"},
        )

    with pytest.raises(SDKConfigurationError, match="principal_id"):
        client.call_tool(
            tool_id="tool.echo",
            mandate_id=_MANDATE_ID,
            tool_args={"principal_id": "forbidden"},
        )

    client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_async_authority_client_call_tool_routes_to_canonical_endpoint() -> None:
    pytest.importorskip("aiohttp")
    from caracal_sdk.async_authority_client import AsyncAuthorityClient

    client = AsyncAuthorityClient(base_url="http://localhost:8000")
    client._make_request = AsyncMock(return_value={"success": True})

    with pytest.warns(DeprecationWarning, match="non-canonical"):
        result = await client.call_tool(
            tool_id="tool.echo",
            mandate_id=_MANDATE_ID,
            tool_args={"payload": "ok"},
            metadata={"source": "legacy"},
        )

    assert result == {"success": True}
    client._make_request.assert_awaited_once_with(
        method="POST",
        endpoint="/mcp/tool/call",
        data={
            "tool_id": "tool.echo",
            "mandate_id": _MANDATE_ID,
            "tool_args": {"payload": "ok"},
            "metadata": {"source": "legacy"},
        },
    )
    await client.close()
