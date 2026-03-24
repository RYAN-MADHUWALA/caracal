"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Integration tests for enhanced MCP Adapter.

Tests the enhanced MeteringEvent features in MCP Adapter:
- Tool call interception with enhanced metering
- Resource read interception with enhanced metering
- Correlation ID propagation
- Decorator mode with enhanced metering
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime
from uuid import uuid4, UUID

from caracal.mcp.adapter import MCPAdapter, MCPContext, MCPResult
from caracal.core.metering import MeteringEvent, MeteringCollector
from caracal.core.authority import AuthorityEvaluator, AuthorityDecision
from caracal.core.mandate import Mandate
from caracal.core.ledger import LedgerWriter


@pytest.fixture
def mock_ledger_writer():
    """Create a mock ledger writer."""
    mock_writer = Mock(spec=LedgerWriter)
    mock_event = Mock()
    mock_event.event_id = str(uuid4())
    mock_writer.append_event.return_value = mock_event
    return mock_writer


@pytest.fixture
def metering_collector(mock_ledger_writer):
    """Create a real MeteringCollector instance."""
    return MeteringCollector(ledger_writer=mock_ledger_writer)


@pytest.fixture
def mock_authority_evaluator():
    """Create a mock authority evaluator."""
    evaluator = Mock(spec=AuthorityEvaluator)
    
    # Mock mandate
    mock_mandate = Mock(spec=Mandate)
    mock_mandate.mandate_id = uuid4()
    mock_mandate.principal_id = "test-agent"
    
    evaluator._get_mandate_with_cache.return_value = mock_mandate
    
    # Mock decision (allow by default)
    mock_decision = Mock(spec=AuthorityDecision)
    mock_decision.allowed = True
    mock_decision.reason = "Allowed"
    
    evaluator.validate_mandate.return_value = mock_decision
    
    return evaluator


@pytest.fixture
def mcp_adapter(mock_authority_evaluator, metering_collector):
    """Create an MCPAdapter instance for testing."""
    return MCPAdapter(
        authority_evaluator=mock_authority_evaluator,
        metering_collector=metering_collector,
        mcp_server_url="http://localhost:9001",
        request_timeout_seconds=10
    )


class TestEnhancedToolCallInterception:
    """Test tool call interception with enhanced metering features."""
    
    @pytest.mark.asyncio
    async def test_tool_call_with_correlation_id(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that tool call generates correlation_id."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        tool_name = "search"
        tool_args = {"query": "test"}
        
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={"mandate_id": mandate_id}
        )
        
        # Mock MCP server response
        with patch.object(mcp_adapter, '_forward_to_mcp_server', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"result": "search results"}
            
            # Execute
            result = await mcp_adapter.intercept_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                mcp_context=mcp_context
            )
        
        # Verify result
        assert result.success is True
        
        # Verify metering event was collected
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        # Check that correlation_id was added to metadata
        metadata = call_args.kwargs.get('metadata', {})
        assert 'correlation_id' in metadata
        assert metadata['correlation_id'] is not None
        assert len(metadata['correlation_id']) > 0
    
    @pytest.mark.asyncio
    async def test_tool_call_with_parent_event_id(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that tool call propagates parent_event_id from context."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        parent_event_id = str(uuid4())
        tool_name = "search"
        tool_args = {"query": "test"}
        
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={
                "mandate_id": mandate_id,
                "parent_event_id": parent_event_id
            }
        )
        
        # Mock MCP server response
        with patch.object(mcp_adapter, '_forward_to_mcp_server', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"result": "search results"}
            
            # Execute
            result = await mcp_adapter.intercept_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                mcp_context=mcp_context
            )
        
        # Verify result
        assert result.success is True
        
        # Verify metering event was collected with parent_event_id
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'parent_event_id' in metadata
        assert metadata['parent_event_id'] == parent_event_id
    
    @pytest.mark.asyncio
    async def test_tool_call_with_tags(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that tool call includes appropriate tags."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        tool_name = "search"
        tool_args = {"query": "test"}
        
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={"mandate_id": mandate_id}
        )
        
        # Mock MCP server response
        with patch.object(mcp_adapter, '_forward_to_mcp_server', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"result": "search results"}
            
            # Execute
            result = await mcp_adapter.intercept_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                mcp_context=mcp_context
            )
        
        # Verify result
        assert result.success is True
        
        # Verify metering event was collected with tags
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'tags' in metadata
        tags = metadata['tags']
        assert "mcp" in tags
        assert "tool" in tags
        assert tool_name in tags


class TestEnhancedResourceReadInterception:
    """Test resource read interception with enhanced metering features."""
    
    @pytest.mark.asyncio
    async def test_resource_read_with_correlation_id(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that resource read generates correlation_id."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        resource_uri = "file:///test/file.txt"
        
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={"mandate_id": mandate_id}
        )
        
        # Mock resource fetch
        from caracal.mcp.adapter import MCPResource
        mock_resource = MCPResource(
            uri=resource_uri,
            content="test content",
            mime_type="text/plain",
            size=12
        )
        
        with patch.object(mcp_adapter, '_fetch_resource', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_resource
            
            # Execute
            result = await mcp_adapter.intercept_resource_read(
                resource_uri=resource_uri,
                mcp_context=mcp_context
            )
        
        # Verify result
        assert result.success is True
        
        # Verify metering event was collected with correlation_id
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'correlation_id' in metadata
        assert metadata['correlation_id'] is not None
    
    @pytest.mark.asyncio
    async def test_resource_read_with_tags(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that resource read includes appropriate tags."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        resource_uri = "file:///test/file.txt"
        
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={"mandate_id": mandate_id}
        )
        
        # Mock resource fetch
        from caracal.mcp.adapter import MCPResource
        mock_resource = MCPResource(
            uri=resource_uri,
            content="test content",
            mime_type="text/plain",
            size=12
        )
        
        with patch.object(mcp_adapter, '_fetch_resource', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_resource
            
            # Execute
            result = await mcp_adapter.intercept_resource_read(
                resource_uri=resource_uri,
                mcp_context=mcp_context
            )
        
        # Verify result
        assert result.success is True
        
        # Verify metering event was collected with tags
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'tags' in metadata
        tags = metadata['tags']
        assert "mcp" in tags
        assert "resource" in tags
        assert "file" in tags  # Resource type from URI


class TestDecoratorModeEnhanced:
    """Test decorator mode with enhanced metering features."""
    
    @pytest.mark.asyncio
    async def test_decorator_with_correlation_id(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that decorator mode generates correlation_id."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        
        # Create a test function to decorate
        @mcp_adapter.as_decorator()
        async def test_tool(agent_id: str, mandate_id: str, query: str):
            return f"Result for {query}"
        
        # Execute
        result = await test_tool(
            agent_id=agent_id,
            mandate_id=str(mandate_id),
            query="test query"
        )
        
        # Verify result
        assert result == "Result for test query"
        
        # Verify metering event was collected with correlation_id
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'correlation_id' in metadata
        assert metadata['correlation_id'] is not None
    
    @pytest.mark.asyncio
    async def test_decorator_with_tags(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that decorator mode includes appropriate tags."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        
        # Create a test function to decorate
        @mcp_adapter.as_decorator()
        async def test_tool(agent_id: str, mandate_id: str, query: str):
            return f"Result for {query}"
        
        # Execute
        result = await test_tool(
            agent_id=agent_id,
            mandate_id=str(mandate_id),
            query="test query"
        )
        
        # Verify result
        assert result == "Result for test query"
        
        # Verify metering event was collected with tags
        assert mock_ledger_writer.append_event.called
        call_args = mock_ledger_writer.append_event.call_args
        
        metadata = call_args.kwargs.get('metadata', {})
        assert 'tags' in metadata
        tags = metadata['tags']
        assert "mcp" in tags
        assert "tool" in tags
        assert "test_tool" in tags
        assert "decorator" in tags


class TestCorrelationPropagation:
    """Test correlation ID propagation across operations."""
    
    @pytest.mark.asyncio
    async def test_correlation_propagation_in_nested_operations(
        self,
        mcp_adapter,
        mock_ledger_writer
    ):
        """Test that correlation_id can be propagated through nested operations."""
        # Setup
        agent_id = "test-agent-123"
        mandate_id = str(uuid4())
        parent_event_id = str(uuid4())
        tool_name = "search"
        tool_args = {"query": "test"}
        
        # First operation with parent_event_id
        mcp_context = MCPContext(
            agent_id=agent_id,
            metadata={
                "mandate_id": mandate_id,
                "parent_event_id": parent_event_id
            }
        )
        
        # Mock MCP server response
        with patch.object(mcp_adapter, '_forward_to_mcp_server', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"result": "search results"}
            
            # Execute first operation
            result1 = await mcp_adapter.intercept_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                mcp_context=mcp_context
            )
        
        # Verify first operation
        assert result1.success is True
        
        # Get the correlation_id from first operation
        first_call_args = mock_ledger_writer.append_event.call_args_list[0]
        first_metadata = first_call_args.kwargs.get('metadata', {})
        first_correlation_id = first_metadata.get('correlation_id')
        
        # Second operation using first correlation_id as parent
        mcp_context2 = MCPContext(
            agent_id=agent_id,
            metadata={
                "mandate_id": mandate_id,
                "parent_event_id": first_correlation_id
            }
        )
        
        with patch.object(mcp_adapter, '_forward_to_mcp_server', new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"result": "more results"}
            
            # Execute second operation
            result2 = await mcp_adapter.intercept_tool_call(
                tool_name="analyze",
                tool_args={"data": "test"},
                mcp_context=mcp_context2
            )
        
        # Verify second operation
        assert result2.success is True
        
        # Verify parent_event_id was propagated
        second_call_args = mock_ledger_writer.append_event.call_args_list[1]
        second_metadata = second_call_args.kwargs.get('metadata', {})
        assert second_metadata.get('parent_event_id') == first_correlation_id
