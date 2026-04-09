"""Shared tool-registry contract helpers for CLI and TUI flows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, Optional

from caracal.core.authority import AuthorityEvaluator
from caracal.db.models import RegisteredTool
from caracal.exceptions import CaracalError
from caracal.mcp.adapter import MCPAdapter


class _NoopMeteringCollector:
    def collect_event(self, _event) -> None:
        return None


def _normalize_tool_ids(tool_ids: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for tool_id in tool_ids:
        value = str(tool_id or "").strip()
        if value and value not in normalized:
            normalized.append(value)
    if not normalized:
        raise CaracalError("At least one tool_id is required")
    return normalized


def resolve_issue_scopes_from_tool_ids(
    *,
    db_session,
    tool_ids: Iterable[str],
    providers: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Resolve canonical provider/action/resource scopes from registered tool IDs."""
    normalized_tool_ids = _normalize_tool_ids(tool_ids)
    provider_filter = {
        str(provider).strip()
        for provider in (providers or [])
        if str(provider).strip()
    }

    adapter = MCPAdapter(
        authority_evaluator=AuthorityEvaluator(db_session),
        metering_collector=_NoopMeteringCollector(),
    )

    mappings: list[Dict[str, Any]] = []
    for tool_id in normalized_tool_ids:
        mapping = adapter._resolve_active_tool_mapping(
            tool_id=tool_id,
            mcp_context=None,
            require_credential=False,
        )
        provider_name = str(mapping["provider_name"])
        if provider_filter and provider_name not in provider_filter:
            allowed = ", ".join(sorted(provider_filter))
            raise CaracalError(
                f"Tool '{tool_id}' maps to provider '{provider_name}' which is outside selected provider filter: {allowed}"
            )
        mappings.append(mapping)

    return {
        "tool_ids": [mapping["tool_id"] for mapping in mappings],
        "providers": sorted({str(mapping["provider_name"]) for mapping in mappings}),
        "resource_scope": sorted({str(mapping["resource_scope"]) for mapping in mappings}),
        "action_scope": sorted({str(mapping["action_scope"]) for mapping in mappings}),
    }


def list_tool_bindings_by_provider(
    *,
    db_session,
    include_inactive: bool = False,
) -> Dict[str, list[str]]:
    """Return provider->tool_id bindings from persisted tool registry records."""
    query = db_session.query(RegisteredTool)
    if not include_inactive:
        query = query.filter_by(active=True)

    bindings: dict[str, list[str]] = defaultdict(list)
    for row in query.order_by(RegisteredTool.tool_id.asc()).all():
        provider_name = str(getattr(row, "provider_name", "") or "").strip()
        tool_id = str(getattr(row, "tool_id", "") or "").strip()
        if not provider_name or not tool_id:
            continue
        bindings[provider_name].append(tool_id)

    return dict(bindings)
