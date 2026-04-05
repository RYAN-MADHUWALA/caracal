"""Concrete revocation event publishers for runtime deployment targets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from caracal.redis.client import RedisClient


class RedisPubSubRevocationEventPublisher:
    """Publish principal revocation events to an OSS Redis pub/sub channel."""

    DEFAULT_CHANNEL = "caracal:identity:revocation_events"

    def __init__(self, redis_client: RedisClient, *, channel: str = DEFAULT_CHANNEL) -> None:
        self._redis_client = redis_client
        self._channel = str(channel or "").strip()
        if not self._channel:
            raise ValueError("channel cannot be empty")

    async def publish_principal_revocation_event(
        self,
        *,
        event_type: str,
        principal_id: str,
        reason: str,
        actor_principal_id: Optional[str],
        root_principal_id: Optional[str],
        revoked_mandate_ids: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "event_type": event_type,
            "principal_id": principal_id,
            "reason": reason,
            "actor_principal_id": actor_principal_id,
            "root_principal_id": root_principal_id,
            "revoked_mandate_ids": list(revoked_mandate_ids or []),
            "metadata": dict(metadata or {}),
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        self._redis_client.publish(self._channel, json.dumps(payload, sort_keys=True))
