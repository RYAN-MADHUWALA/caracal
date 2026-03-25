"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Unit tests for GatewayClient functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from caracal.deployment.gateway_client import (
    GatewayClient,
    JWTToken,
    ProviderRequest,
    QueuedRequest,
    QuotaStatus,
    RequestPriority,
)
from caracal.deployment.exceptions import (
    GatewayAuthenticationError,
    GatewayConnectionError,
    GatewayQuotaExceededError,
    GatewayTimeoutError,
    GatewayUnavailableError,
)


class TestJWTToken:
    """Test JWT token functionality."""
    
    def test_token_not_expired(self):
        """Test token that is not expired."""
        token = JWTToken(
            token="test-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert not token.is_expired()
    
    def test_token_expired(self):
        """Test token that is expired."""
        token = JWTToken(
            token="test-token",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        assert token.is_expired()
    
    def test_token_expires_within_buffer(self):
        """Test token that expires within buffer time."""
        token = JWTToken(
            token="test-token",
            expires_at=datetime.now() + timedelta(seconds=30)
        )
        
        # Should be considered expired with 60 second buffer
        assert token.is_expired(buffer_seconds=60)


class TestQueuedRequest:
    """Test queued request functionality."""
    
    def test_request_not_expired(self):
        """Test request that is not expired."""
        request = QueuedRequest(
            request=ProviderRequest(
                provider="test",
                method="GET",
                endpoint="/test"
            ),
            priority=RequestPriority.NORMAL,
            queued_at=datetime.now(),
            ttl_seconds=3600
        )
        
        assert not request.is_expired()
    
    def test_request_expired(self):
        """Test request that is expired."""
        request = QueuedRequest(
            request=ProviderRequest(
                provider="test",
                method="GET",
                endpoint="/test"
            ),
            priority=RequestPriority.NORMAL,
            queued_at=datetime.now() - timedelta(hours=2),
            ttl_seconds=3600
        )
        
        assert request.is_expired()


class TestGatewayClient:
    """Test GatewayClient functionality."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create mock config manager."""
        manager = MagicMock()
        manager.get_secret.return_value = "test-gateway-token"
        return manager
    
    @pytest.fixture
    def gateway_client(self, mock_config_manager):
        """Create gateway client instance."""
        return GatewayClient(
            gateway_url="https://gateway.example.com",
            config_manager=mock_config_manager,
            workspace="test"
        )
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, gateway_client, mock_config_manager):
        """Test successful authentication."""
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "jwt-token",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "refresh_token": "refresh-token"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            await gateway_client._authenticate()
            
            assert gateway_client._token is not None
            assert gateway_client._token.token == "jwt-token"
            assert gateway_client._token.refresh_token == "refresh-token"
            assert not gateway_client._token.is_expired()
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, gateway_client, mock_config_manager):
        """Test authentication failure."""
        # Mock HTTP client with 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with pytest.raises(GatewayAuthenticationError):
                await gateway_client._authenticate()
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, gateway_client):
        """Test successful token refresh."""
        # Set up existing token
        gateway_client._token = JWTToken(
            token="old-token",
            expires_at=datetime.now() - timedelta(hours=1),
            refresh_token="refresh-token"
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-jwt-token",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            await gateway_client._refresh_token()
            
            assert gateway_client._token.token == "new-jwt-token"
            assert not gateway_client._token.is_expired()
    
    @pytest.mark.asyncio
    async def test_call_provider_success(self, gateway_client, mock_config_manager):
        """Test successful provider call through gateway."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with patch.object(gateway_client, '_check_quota', return_value=None):
                request = ProviderRequest(
                    provider="test-provider",
                    method="GET",
                    endpoint="/test"
                )
                
                response = await gateway_client.call_provider("test-provider", request)
                
                assert response.status_code == 200
                assert response.data == {"result": "success"}
                assert response.error is None
                assert response.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_call_provider_authentication_error(self, gateway_client):
        """Test provider call with authentication error."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client with 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with patch.object(gateway_client, '_check_quota', return_value=None):
                request = ProviderRequest(
                    provider="test-provider",
                    method="GET",
                    endpoint="/test"
                )
                
                with pytest.raises(GatewayAuthenticationError):
                    await gateway_client.call_provider("test-provider", request)
    
    @pytest.mark.asyncio
    async def test_call_provider_quota_exceeded(self, gateway_client):
        """Test provider call with quota exceeded."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client with 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with patch.object(gateway_client, '_check_quota', return_value=None):
                request = ProviderRequest(
                    provider="test-provider",
                    method="GET",
                    endpoint="/test"
                )
                
                with pytest.raises(GatewayQuotaExceededError):
                    await gateway_client.call_provider("test-provider", request)
    
    @pytest.mark.asyncio
    async def test_call_provider_gateway_unavailable(self, gateway_client):
        """Test provider call when gateway is unavailable."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client with connection error
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with patch.object(gateway_client, '_check_quota', return_value=None):
                request = ProviderRequest(
                    provider="test-provider",
                    method="GET",
                    endpoint="/test"
                )
                
                with pytest.raises(GatewayUnavailableError):
                    await gateway_client.call_provider("test-provider", request)
                
                # Request should be queued
                assert gateway_client.get_queue_size() == 1
    
    @pytest.mark.asyncio
    async def test_get_available_providers(self, gateway_client):
        """Test getting available providers."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "providers": [
                {
                    "name": "openai",
                    "type": "openai",
                    "available": True,
                    "quota_remaining": 1000
                },
                {
                    "name": "anthropic",
                    "type": "anthropic",
                    "available": True,
                    "quota_remaining": 500
                }
            ]
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            providers = await gateway_client.get_available_providers()
            
            assert len(providers) == 2
            assert providers[0].name == "openai"
            assert providers[0].available is True
            assert providers[0].quota_remaining == 1000
    
    @pytest.mark.asyncio
    async def test_check_connection(self, gateway_client):
        """Test gateway connection check."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            health = await gateway_client.check_connection()
            
            assert health.healthy is True
            assert health.authenticated is True
            assert health.error is None
            assert health.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_quota_status(self, gateway_client):
        """Test getting quota status."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 10000,
            "used": 2500,
            "remaining": 7500,
            "reset_at": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            quota = await gateway_client.get_quota_status()
            
            assert quota.total_quota == 10000
            assert quota.used_quota == 2500
            assert quota.remaining_quota == 7500
            assert quota.percentage_used == 25.0
    
    @pytest.mark.asyncio
    async def test_queue_request(self, gateway_client):
        """Test request queuing."""
        request = ProviderRequest(
            provider="test-provider",
            method="GET",
            endpoint="/test"
        )
        
        await gateway_client._queue_request(request, RequestPriority.NORMAL)
        
        assert gateway_client.get_queue_size() == 1
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self, gateway_client):
        """Test queue size limit."""
        # Set small queue size
        gateway_client.max_queue_size = 5
        
        # Queue more requests than limit
        for i in range(10):
            request = ProviderRequest(
                provider="test-provider",
                method="GET",
                endpoint=f"/test{i}"
            )
            await gateway_client._queue_request(request, RequestPriority.NORMAL)
        
        # Should not exceed max size
        assert gateway_client.get_queue_size() <= 5
    
    def test_cleanup_expired_requests(self, gateway_client):
        """Test cleanup of expired requests."""
        # Add expired request
        expired_request = QueuedRequest(
            request=ProviderRequest(
                provider="test",
                method="GET",
                endpoint="/test"
            ),
            priority=RequestPriority.NORMAL,
            queued_at=datetime.now() - timedelta(hours=2),
            ttl_seconds=3600
        )
        
        gateway_client._request_queue.append(expired_request)
        
        # Add valid request
        valid_request = QueuedRequest(
            request=ProviderRequest(
                provider="test",
                method="GET",
                endpoint="/test2"
            ),
            priority=RequestPriority.NORMAL,
            queued_at=datetime.now(),
            ttl_seconds=3600
        )
        
        gateway_client._request_queue.append(valid_request)
        
        # Cleanup
        gateway_client._cleanup_expired_requests()
        
        # Only valid request should remain
        assert gateway_client.get_queue_size() == 1
    
    def test_clear_queue(self, gateway_client):
        """Test clearing request queue."""
        # Add some requests
        for i in range(5):
            request = QueuedRequest(
                request=ProviderRequest(
                    provider="test",
                    method="GET",
                    endpoint=f"/test{i}"
                ),
                priority=RequestPriority.NORMAL,
                queued_at=datetime.now(),
                ttl_seconds=3600
            )
            gateway_client._request_queue.append(request)
        
        assert gateway_client.get_queue_size() == 5
        
        # Clear queue
        gateway_client.clear_queue()
        
        assert gateway_client.get_queue_size() == 0
    
    @pytest.mark.asyncio
    async def test_close_client(self, gateway_client):
        """Test closing HTTP client."""
        # Create client
        await gateway_client._get_client()
        assert gateway_client._client is not None
        
        # Close client
        await gateway_client.close()
        assert gateway_client._client is None
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, gateway_client):
        """Test streaming provider response."""
        # Set up token
        gateway_client._token = JWTToken(
            token="jwt-token",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Mock streaming response
        async def mock_aiter_text():
            for chunk in ["chunk1", "chunk2", "chunk3"]:
                yield chunk
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_text = mock_aiter_text
        mock_response.headers = {}
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_context
        
        with patch.object(gateway_client, '_get_client', return_value=mock_client):
            with patch.object(gateway_client, '_check_quota', return_value=None):
                request = ProviderRequest(
                    provider="test-provider",
                    method="POST",
                    endpoint="/stream",
                    stream=True
                )
                
                chunks = []
                async for response in gateway_client.stream_provider_call("test-provider", request):
                    chunks.append(response.data["chunk"])
                
                assert len(chunks) == 3
                assert chunks == ["chunk1", "chunk2", "chunk3"]
