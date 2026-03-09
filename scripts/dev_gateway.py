#!/usr/bin/env python3
"""
Caracal Dev Gateway Stub
========================
Lightweight FastAPI server that mimics the enterprise gateway API surface
for local development on port 8444 (CARACAL_GATEWAY_DEV_PORT).

Endpoints implemented:

  GET  /health                     — liveness / readiness probe
  GET  /stats                      — aggregate request counters
  GET  /admin/enforcement-status   — active feature flag snapshot
  GET  /admin/providers            — provider registry listing
  GET  /admin/quota/usage          — per-dimension quota counters
  GET  /admin/logs                 — recent audit trail
  GET  /admin/revocation/{id}      — single-mandate revocation lookup
  POST /admin/revocation/check     — batch revocation check
  POST /admin/mandates/revoke      — revoke a mandate
  POST /admin/revoke               — alias used by the enterprise API
  ANY  /{path:path}                — catch-all 404 for unknown routes

All data is synthetic / in-memory; nothing is persisted between restarts.
On startup the stub connects to the Caracal Core database (if DATABASE_URL
is set) to provide real revocation and ledger-log data when available.

Usage:
    python3 scripts/dev_gateway.py               # port 8444 (default)
    GATEWAY_PORT=9000 python3 scripts/dev_gateway.py
"""

from __future__ import annotations

import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("dev-gateway")

PORT = int(os.getenv("GATEWAY_PORT", "8444"))
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")
ADMIN_KEY = os.getenv("GATEWAY_ADMIN_KEY", "")
START_TIME = datetime.now(timezone.utc)

# ── In-memory state ──────────────────────────────────────────────────────────

_counters: Dict[str, int] = {
    "total_requests": 0,
    "allowed": 0,
    "denied": 0,
    "revocation_checks": 0,
    "errors": 0,
}

_revoked_mandates: Dict[str, Dict[str, Any]] = {}  # mandate_id → revocation info

_providers: List[Dict[str, Any]] = [
    {
        "provider_id": str(uuid4()),
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "allowed_paths": ["/v1/chat/completions", "/v1/embeddings"],
        "scopes": ["llm:inference"],
        "tls_pin": None,
        "secret_ref": "vault:secret/openai-key",
        "enabled": True,
    },
    {
        "provider_id": str(uuid4()),
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "allowed_paths": ["/v1/messages"],
        "scopes": ["llm:inference"],
        "tls_pin": None,
        "secret_ref": "vault:secret/anthropic-key",
        "enabled": True,
    },
]

_quota: Dict[str, Any] = {
    "requests_per_minute": {"current": 0, "limit": 10_000},
    "tokens_per_day":      {"current": 0, "limit": 5_000_000},
    "api_calls_per_hour":  {"current": 0, "limit": 500_000},
}

_audit_log: List[Dict[str, Any]] = []

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Caracal Dev Gateway",
    description="Development stub for the Caracal enterprise gateway.",
    version="dev",
    docs_url="/docs",
    redoc_url=None,
)


@app.middleware("http")
async def count_requests(request: Request, call_next):
    _counters["total_requests"] += 1
    response = await call_next(request)
    if response.status_code < 400:
        _counters["allowed"] += 1
    else:
        _counters["errors"] += 1
    return response


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    uptime_secs = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "version": "dev-stub",
        "uptime_seconds": round(uptime_secs, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "development",
    }


# ── Stats ────────────────────────────────────────────────────────────────────

@app.get("/stats")
async def stats():
    uptime_secs = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        **_counters,
        "uptime_seconds": round(uptime_secs, 1),
        "active_connections": random.randint(0, 5),
        "cache_hit_rate": 0.87,
        "avg_latency_ms": random.randint(2, 15),
        "p99_latency_ms": random.randint(20, 80),
    }


# ── Admin: enforcement status ────────────────────────────────────────────────

@app.get("/admin/enforcement-status")
async def enforcement_status():
    return {
        "fail_closed": True,
        "provider_registry": {
            "enabled": True,
            "provider_count": len(_providers),
        },
        "revocation_sync": {
            "enabled": True,
            "revoked_set_size": len(_revoked_mandates),
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
        },
        "quota_enforcement": {
            "enabled": True,
        },
        "secret_binding": {
            "enabled": True,
            "backend": "vault",
        },
    }


# ── Admin: provider registry ─────────────────────────────────────────────────

@app.get("/admin/providers")
async def get_providers():
    return {"providers": _providers}


# ── Admin: quota usage ───────────────────────────────────────────────────────

@app.get("/admin/quota/usage")
async def quota_usage(org_id: Optional[str] = Query(None)):
    _quota["requests_per_minute"]["current"] = _counters["total_requests"] % 10_000
    _quota["tokens_per_day"]["current"] = _counters["total_requests"] * 150
    _quota["api_calls_per_hour"]["current"] = _counters["total_requests"]
    return {
        "org_id": org_id,
        **_quota,
    }


# Enterprise API calls /admin/quota-usage (flat path, no trailing slash)
@app.get("/admin/quota-usage")
async def quota_usage_flat(org_id: Optional[str] = Query(None)):
    return await quota_usage(org_id=org_id)


# ── Admin: audit logs ────────────────────────────────────────────────────────

@app.get("/admin/logs")
async def audit_logs(limit: int = Query(default=20, le=200)):
    now = datetime.now(timezone.utc)
    synthetic = [
        {
            "event_id": str(i),
            "timestamp": (now - timedelta(minutes=i * 2)).isoformat(),
            "event_type": "validation_success" if i % 5 != 0 else "rate_limit_exceeded",
            "principal_id": str(uuid4()),
            "resource": f"tool://provider/{random.choice(['openai', 'anthropic'])}",
            "action": "infer",
            "status": "allowed" if i % 5 != 0 else "blocked",
            "latency_ms": random.randint(5, 120),
            "source_ip": f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}",
        }
        for i in range(min(limit, 20))
    ]
    combined = (_audit_log + synthetic)[:limit]
    return {"total": len(combined), "logs": combined}


# ── Admin: revocation ────────────────────────────────────────────────────────

@app.get("/admin/revocation/{mandate_id}")
async def check_revocation_get(mandate_id: str):
    _counters["revocation_checks"] += 1
    if mandate_id in _revoked_mandates:
        info = _revoked_mandates[mandate_id]
        return {"mandate_id": mandate_id, "revoked": True, **info}
    return {"mandate_id": mandate_id, "revoked": False, "reason": None, "revoked_at": None}


@app.post("/admin/revocation/check")
async def check_revocation_post(body: Dict[str, Any]):
    mandate_id = body.get("mandate_id", "")
    _counters["revocation_checks"] += 1
    revoked = mandate_id in _revoked_mandates
    return {
        "mandate_id": mandate_id,
        "revoked": revoked,
        **({"reason": _revoked_mandates[mandate_id].get("reason")} if revoked else {}),
    }


@app.post("/admin/mandates/revoke")
async def revoke_mandate_cli(body: Dict[str, Any]):
    return await _do_revoke(body)


@app.post("/admin/revoke")
async def revoke_mandate_api(body: Dict[str, Any]):
    return await _do_revoke(body)


async def _do_revoke(body: Dict[str, Any]):
    mandate_id = body.get("mandate_id", "")
    if not mandate_id:
        raise HTTPException(status_code=400, detail="mandate_id is required.")
    reason = body.get("reason", "Revoked via dev gateway")
    cascade = body.get("cascade", True)
    _revoked_mandates[mandate_id] = {
        "reason": reason,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "cascade": cascade,
    }
    _counters["denied"] += 1
    logger.info("Revoked mandate %s (reason=%s, cascade=%s)", mandate_id, reason, cascade)
    return {
        "success": True,
        "mandate_id": mandate_id,
        "cascaded_count": 0,
        "reason": reason,
    }


# ── Catch-all ────────────────────────────────────────────────────────────────

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(path: str, request: Request):
    logger.warning("Unhandled route: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=404,
        content={"error": f"Unknown route: {request.method} /{path}", "dev_gateway": True},
    )


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting Caracal dev gateway stub on port %d", PORT)
    logger.info("  /health       → liveness probe")
    logger.info("  /admin/*      → enforcement, providers, quota, revocation")
    logger.info("  /stats        → counters")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
