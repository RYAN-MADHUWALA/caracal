<div align="center">
<picture>
<source media="(prefers-color-scheme: dark)" srcset="public/caracal_nobg_dark_mode.png">
<source media="(prefers-color-scheme: light)" srcset="public/caracal_nobg.png">
<img alt="Caracal Logo" src="public/caracal_nobg.png" width="300">
</picture>
</div>

<div align="center">

**Pre-execution authority enforcement for AI agents**

</div>

<div align="center">

[![License](https://img.shields.io/badge/License-Apache--2.0-blue?style=for-the-badge&logo=gnubash&logoColor=white)](LICENSE)
[![Version](https://img.shields.io/github/v/release/Garudex-Labs/caracal?style=for-the-badge&label=Release&color=orange)](https://github.com/Garudex-Labs/caracal/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![Repo Size](https://img.shields.io/github/repo-size/Garudex-Labs/caracal?style=for-the-badge&color=green)](https://github.com/Garudex-Labs/caracal)
[![Activity](https://img.shields.io/github/commit-activity/m/Garudex-Labs/caracal?style=for-the-badge&color=blueviolet)](https://github.com/Garudex-Labs/caracal/graphs/commit-activity)
[![Website](https://img.shields.io/badge/Website-garudexlabs.com-333333?style=for-the-badge&logo=google-chrome&logoColor=white)](https://garudexlabs.com)
[![PyPI](https://img.shields.io/pypi/v/caracal-core?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/caracal-core/)

</div>

-----

# Overview

**Caracal** is a pre-execution authority enforcement system for AI agents and automated software operating in production environments. It exists at the boundary where autonomous decisions turn into irreversible actions—such as API calls, database writes, or system triggers.

By enforcing the **principle of explicit authority**, Caracal ensures no action executes without a cryptographically verified, time-bound mandate issued under a governing policy.

-----

## Community

<div align="center">
<table>
<tr>
<td align="center">
<a href="https://www.youtube.com/live/tZ4FdO-zjeE" target="_blank" rel="noopener">
<img src="https://img.youtube.com/vi/tZ4FdO-zjeE/hqdefault.jpg" alt="Open Source Friday — Preview" height="180"><br>
<strong>GitHub's Open Source Friday</strong>
</a>
</td>
<td align="center">
<div style="width:320px;height:180px;display:flex;align-items:center;justify-content:center;border-radius:6px;border:1px solid #ddd;background:#f8f8f8;font-weight:600">
More coming soon
</div>
</td>
</tr>
</table>
</div>

</div>

<div align="center">
</div>

-----

## Technical Architecture

Caracal Core implements a robust enforcement engine using the following cryptographic and access control primitives:

| Component | Description |
| :--- | :--- |
| **Principals** | Identities (agents/users) with ECDSA P-256 cryptographic keys. |
| **Policies** | Fine-grained rules defining resource patterns and allowed actions. |
| **Mandates** | Short-lived, signed tokens granting the right to execute an action. |
| **Ledger** | High-performance audit trail of every authorization event. |

-----

## Installation & Setup

Caracal runtime is container-first.

- CLI and TUI run from the same runtime image.
- Both mount the same `.caracal` workspace volume.
- MCP API, CLI, TUI, and SDK clients all target the same runtime endpoint contract.

This gives identical behavior in local and cloud environments: same image, same environment variables, same volume-backed workspace semantics.

### 1\. Docker-Only (No Repository Required)

Use this when you want to start Caracal by pulling and running images directly.

```bash
# Runtime image used by API + CLI + TUI
export CARACAL_RUNTIME_IMAGE=ghcr.io/garudex-labs/caracal-runtime:latest
docker pull "$CARACAL_RUNTIME_IMAGE"

# Shared runtime network + persistent volumes
docker network create caracal-runtime || true
docker volume create caracal_state
docker volume create caracal_postgres_data
docker volume create caracal_redis_data

# Infrastructure services
docker run -d --name caracal-postgres \
  --network caracal-runtime \
  -e POSTGRES_DB=caracal \
  -e POSTGRES_USER=caracal \
  -e POSTGRES_PASSWORD=caracal \
  -v caracal_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine

docker run -d --name caracal-redis \
  --network caracal-runtime \
  -v caracal_redis_data:/data \
  redis:7-alpine redis-server --appendonly yes

# Runtime API
docker run -d --name caracal-mcp \
  --network caracal-runtime \
  -p 8000:8080 \
  -v caracal_state:/home/caracal/.caracal \
  -e CARACAL_RUNTIME_IN_CONTAINER=1 \
  -e CARACAL_WORKSPACE_ROOT=/home/caracal/.caracal \
  -e CARACAL_CONFIG_PATH=/home/caracal/.caracal/config.yaml \
  -e CARACAL_MCP_LISTEN_ADDRESS=0.0.0.0:8080 \
  -e CARACAL_DB_HOST=caracal-postgres \
  -e CARACAL_DB_PORT=5432 \
  -e CARACAL_DB_NAME=caracal \
  -e CARACAL_DB_USER=caracal \
  -e CARACAL_DB_PASSWORD=caracal \
  -e REDIS_HOST=caracal-redis \
  -e REDIS_PORT=6379 \
  -e CARACAL_ENV_MODE=dev \
  "$CARACAL_RUNTIME_IMAGE" python -m caracal.mcp.service
```

Run CLI and TUI against the same workspace volume:

```bash
# CLI
docker run --rm -it \
  --network caracal-runtime \
  -v caracal_state:/home/caracal/.caracal \
  -e CARACAL_RUNTIME_IN_CONTAINER=1 \
  -e CARACAL_WORKSPACE_ROOT=/home/caracal/.caracal \
  -e CARACAL_CONFIG_PATH=/home/caracal/.caracal/config.yaml \
  -e CARACAL_API_URL=http://caracal-mcp:8080 \
  "$CARACAL_RUNTIME_IMAGE" caracal

# TUI
docker run --rm -it \
  --network caracal-runtime \
  -v caracal_state:/home/caracal/.caracal \
  -e CARACAL_RUNTIME_IN_CONTAINER=1 \
  -e CARACAL_WORKSPACE_ROOT=/home/caracal/.caracal \
  -e CARACAL_CONFIG_PATH=/home/caracal/.caracal/config.yaml \
  -e CARACAL_API_URL=http://caracal-mcp:8080 \
  "$CARACAL_RUNTIME_IMAGE" caracal-flow
```

CLI and TUI now operate on one workspace (`caracal_state` volume), so switching between interfaces never duplicates or diverges state.

### 2\. Repository Compose Workflows (Optional)

If you do have the repository, use either compose file:

```bash
# Local build workflow
docker compose -f deploy/docker-compose.yml up -d mcp

# Image-only workflow (pulls CARACAL_RUNTIME_IMAGE)
docker compose -f deploy/docker-compose.image.yml pull
docker compose -f deploy/docker-compose.image.yml up -d mcp
```

### Environment Modes and Logging

Caracal supports three environment modes via `CARACAL_ENV_MODE`:

- `dev`: interactive logs, debug logging available only when `CARACAL_DEBUG_LOGS=true`
- `staging`: minimal structured JSON logs, sensitive field redaction enabled
- `prod`: minimal structured JSON logs, sensitive field redaction enabled

Additional controls:

- `CARACAL_JSON_LOGS=true` forces JSON logging in `dev`
- `LOG_LEVEL` sets requested level, but `DEBUG` is automatically downgraded outside `dev`

### Data Persistence, Migration, and Deletion

- Runtime workspace data persists in the mounted `.caracal` volume.
- Existing legacy workspace/runtime artifacts are migrated into workspace-local paths during initialization.
- Repository-to-package migration remains available via:

```bash
caracal migrate repo-to-package
```

- Workspace deletion is backup-first and schema-aware:

```bash
caracal workspace delete <workspace-name> --force
```

For full environment reset, remove runtime volumes explicitly.

### Enterprise Integration (Gateway + Web UI)

For enterprise mode, point runtime traffic through gateway:

```bash
export CARACAL_GATEWAY_URL=http://gateway:8443
export CARACAL_GATEWAY_ENDPOINT=http://gateway:8443
export CARACAL_GATEWAY_ENABLED=true
```

This ensures provider execution, policy enforcement, mandate checks, and credential-mediated calls route through the gateway path consistently.

In `caracalEnterprise`, backend and web UI integration should include:

- `GATEWAY_URL` for gateway admin/status routing
- shared `CARACAL_RUNTIME_NETWORK` so enterprise services can reach `caracal-mcp`
- `CARACAL_MODE` set to `dev`, `staging`, or `prod` for environment behavior parity

### SDK Runtime Contract

Node and Python SDKs both resolve endpoint consistently:

1. `CARACAL_API_URL`
2. fallback `http://localhost:8000`

This keeps SDK integrations stable across local runtime, broker mode, and gateway-backed deployments.

-----


> **Enterprise Features:** Advanced capabilities including Gateway Proxies, SSO Providers, and Compliance Extensions are available at [garudexlabs.com](https://garudexlabs.com).

-----

## Citation

**Caracal** is an open-source framework for *pre-execution authority enforcement for AI agents controlling delegated actions, with real-time revocation and immutable proof*.

If this project contributes to your research, product, or derivative systems, please consider citing it to help us advance trustworthy AI security research.

```bibtex
@software{madhuwala2026caracal,
  author    = {Madhuwala, Ryan and Garudex Labs},
  title     = {Caracal: Authority Enforcement Framework for AI Agents},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/garudex-labs/caracal}
}
```

-----

## License

Caracal is open-source software licensed under the **Apache-2.0** License. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

**Developed by Garudex Labs.**