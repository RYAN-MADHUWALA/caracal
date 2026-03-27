"""Container-first command entrypoints for Caracal CLI and Flow.

Host invocations default to Docker Compose services to keep runtime state
inside container-managed volumes and avoid host-local drift.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

LOCAL_EXECUTION_ENV = "CARACAL_LOCAL_EXECUTION"
COMPOSE_FILE_ENV = "CARACAL_DOCKER_COMPOSE_FILE"
IN_CONTAINER_ENV = "CARACAL_RUNTIME_IN_CONTAINER"

_EMBEDDED_COMPOSE_FILE = Path.home() / ".caracal" / "runtime" / "docker-compose.image.yml"
_EMBEDDED_COMPOSE_CONTENT = """name: caracal

services:
    postgres:
        image: postgres:16-alpine
        environment:
            POSTGRES_DB: ${CARACAL_DB_NAME:-caracal}
            POSTGRES_USER: ${CARACAL_DB_USER:-caracal}
            POSTGRES_PASSWORD: ${CARACAL_DB_PASSWORD:-caracal}
            POSTGRES_INITDB_ARGS: --encoding=UTF8
        volumes:
            - postgres_data:/var/lib/postgresql/data
        ports:
            - ${CARACAL_DB_PORT:-5432}:5432
        healthcheck:
            test:
                - CMD-SHELL
                - pg_isready -U ${CARACAL_DB_USER:-caracal} -d ${CARACAL_DB_NAME:-caracal}
            interval: 10s
            timeout: 5s
            retries: 10
            start_period: 10s
        restart: unless-stopped
        networks:
            - caracal-runtime

    redis:
        image: redis:7-alpine
        command:
            - redis-server
            - --appendonly
            - "yes"
            - --save
            - "900"
            - "1"
            - --save
            - "300"
            - "10"
            - --save
            - "60"
            - "10000"
        volumes:
            - redis_data:/data
        ports:
            - ${REDIS_PORT:-6379}:6379
        healthcheck:
            test:
                - CMD
                - redis-cli
                - ping
            interval: 10s
            timeout: 5s
            retries: 10
            start_period: 5s
        restart: unless-stopped
        networks:
            - caracal-runtime

    mcp:
        image: ${CARACAL_RUNTIME_IMAGE:-ghcr.io/garudex-labs/caracal-runtime:latest}
        depends_on:
            postgres:
                condition: service_healthy
            redis:
                condition: service_healthy
        environment:
            HOME: /home/caracal
            CARACAL_RUNTIME_IN_CONTAINER: "1"
            CARACAL_WORKSPACE_ROOT: /home/caracal/.caracal
            CARACAL_API_URL: http://mcp:8080
            CARACAL_CONFIG_PATH: /home/caracal/.caracal/config.yaml
            CARACAL_MCP_LISTEN_ADDRESS: 0.0.0.0:8080
            CARACAL_GATEWAY_URL: ${CARACAL_GATEWAY_URL:-}
            CARACAL_ENV_MODE: ${CARACAL_ENV_MODE:-dev}
            CARACAL_DEBUG_LOGS: ${CARACAL_DEBUG_LOGS:-false}
            CARACAL_JSON_LOGS: ${CARACAL_JSON_LOGS:-false}
            CARACAL_DB_HOST: postgres
            CARACAL_DB_PORT: 5432
            CARACAL_DB_NAME: ${CARACAL_DB_NAME:-caracal}
            CARACAL_DB_USER: ${CARACAL_DB_USER:-caracal}
            CARACAL_DB_PASSWORD: ${CARACAL_DB_PASSWORD:-caracal}
            REDIS_HOST: redis
            REDIS_PORT: 6379
            REDIS_PASSWORD: ${REDIS_PASSWORD:-}
            LOG_LEVEL: ${LOG_LEVEL:-INFO}
        command:
            - python
            - -m
            - caracal.mcp.service
        volumes:
            - caracal_state:/home/caracal/.caracal
        ports:
            - ${MCP_ADAPTER_PORT:-8000}:8080
        healthcheck:
            test:
                - CMD
                - python
                - -c
                - import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health').read()
            interval: 30s
            timeout: 10s
            retries: 5
            start_period: 30s
        restart: unless-stopped
        networks:
            - caracal-runtime

    cli:
        profiles:
            - tools
        image: ${CARACAL_RUNTIME_IMAGE:-ghcr.io/garudex-labs/caracal-runtime:latest}
        depends_on:
            postgres:
                condition: service_healthy
            redis:
                condition: service_healthy
        environment:
            HOME: /home/caracal
            CARACAL_RUNTIME_IN_CONTAINER: "1"
            CARACAL_WORKSPACE_ROOT: /home/caracal/.caracal
            CARACAL_API_URL: http://mcp:8080
            CARACAL_CONFIG_PATH: /home/caracal/.caracal/config.yaml
            CARACAL_GATEWAY_URL: ${CARACAL_GATEWAY_URL:-}
            CARACAL_ENV_MODE: ${CARACAL_ENV_MODE:-dev}
            CARACAL_DEBUG_LOGS: ${CARACAL_DEBUG_LOGS:-false}
            CARACAL_JSON_LOGS: ${CARACAL_JSON_LOGS:-false}
            CARACAL_DB_HOST: postgres
            CARACAL_DB_PORT: 5432
            CARACAL_DB_NAME: ${CARACAL_DB_NAME:-caracal}
            CARACAL_DB_USER: ${CARACAL_DB_USER:-caracal}
            CARACAL_DB_PASSWORD: ${CARACAL_DB_PASSWORD:-caracal}
            REDIS_HOST: redis
            REDIS_PORT: 6379
            REDIS_PASSWORD: ${REDIS_PASSWORD:-}
            LOG_LEVEL: ${LOG_LEVEL:-INFO}
        command:
            - caracal
        volumes:
            - caracal_state:/home/caracal/.caracal
        stdin_open: true
        tty: true
        networks:
            - caracal-runtime

    flow:
        profiles:
            - tui
        image: ${CARACAL_RUNTIME_IMAGE:-ghcr.io/garudex-labs/caracal-runtime:latest}
        depends_on:
            postgres:
                condition: service_healthy
            redis:
                condition: service_healthy
        environment:
            HOME: /home/caracal
            CARACAL_RUNTIME_IN_CONTAINER: "1"
            CARACAL_WORKSPACE_ROOT: /home/caracal/.caracal
            CARACAL_API_URL: http://mcp:8080
            CARACAL_CONFIG_PATH: /home/caracal/.caracal/config.yaml
            CARACAL_GATEWAY_URL: ${CARACAL_GATEWAY_URL:-}
            CARACAL_ENV_MODE: ${CARACAL_ENV_MODE:-dev}
            CARACAL_DEBUG_LOGS: ${CARACAL_DEBUG_LOGS:-false}
            CARACAL_JSON_LOGS: ${CARACAL_JSON_LOGS:-false}
            TERM: xterm-256color
            COLORTERM: truecolor
            CARACAL_DB_HOST: postgres
            CARACAL_DB_PORT: 5432
            CARACAL_DB_NAME: ${CARACAL_DB_NAME:-caracal}
            CARACAL_DB_USER: ${CARACAL_DB_USER:-caracal}
            CARACAL_DB_PASSWORD: ${CARACAL_DB_PASSWORD:-caracal}
            REDIS_HOST: redis
            REDIS_PORT: 6379
            REDIS_PASSWORD: ${REDIS_PASSWORD:-}
            LOG_LEVEL: ${LOG_LEVEL:-INFO}
        command:
            - caracal-flow
        volumes:
            - caracal_state:/home/caracal/.caracal
        stdin_open: true
        tty: true
        networks:
            - caracal-runtime

volumes:
    postgres_data:
    redis_data:
    caracal_state:

networks:
    caracal-runtime:
        name: ${CARACAL_RUNTIME_NETWORK:-caracal-runtime}
"""


def caracal_entrypoint() -> None:
    """Entrypoint for the `caracal` command."""
    _dispatch(
        command_name="caracal",
        service_name="cli",
        local_runner=_run_local_caracal,
        service_ports=False,
    )


def caracal_flow_entrypoint() -> None:
    """Entrypoint for the `caracal-flow` command."""
    _dispatch(
        command_name="caracal-flow",
        service_name="flow",
        local_runner=_run_local_flow,
        service_ports=True,
    )


def _dispatch(
    command_name: str,
    service_name: str,
    local_runner: Callable[[Sequence[str]], None],
    service_ports: bool,
) -> None:
    args = tuple(sys.argv[1:])

    if _should_delegate_to_docker():
        exit_code = _run_in_docker(
            service_name=service_name,
            command_name=command_name,
            args=args,
            service_ports=service_ports,
        )
        raise SystemExit(exit_code)

    local_runner(args)


def _should_delegate_to_docker() -> bool:
    if _is_truthy(os.environ.get(LOCAL_EXECUTION_ENV)):
        return False

    if _is_truthy(os.environ.get(IN_CONTAINER_ENV)):
        return False

    if Path("/.dockerenv").exists():
        return False

    return True


def _run_in_docker(
    service_name: str,
    command_name: str,
    args: Sequence[str],
    service_ports: bool,
) -> int:
    compose_file = _resolve_compose_file()
    compose_cmd = _resolve_compose_command()

    boot_cmd = compose_cmd + ["-f", str(compose_file), "up", "-d", "mcp"]
    boot = subprocess.run(boot_cmd, check=False)
    if boot.returncode != 0:
        return boot.returncode

    run_cmd = compose_cmd + ["-f", str(compose_file), "run", "--rm"]
    if service_ports:
        run_cmd.append("--service-ports")
    run_cmd.extend([service_name, command_name, *args])

    run_result = subprocess.run(run_cmd, check=False)
    return run_result.returncode


def _resolve_compose_file() -> Path:
    env_path = os.environ.get(COMPOSE_FILE_ENV)
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.exists():
            return candidate
        raise RuntimeError(
            f"{COMPOSE_FILE_ENV} points to a missing file: {candidate}"
        )

    candidates: list[Path] = []

    # Also search up from this installed package location.
    package_root = Path(__file__).resolve()
    for root in (package_root, *package_root.parents):
        candidates.append(root / "deploy" / "docker-compose.yml")
        candidates.append(root / "docker-compose.yml")

    # Search up from current working directory second.
    current = Path.cwd().resolve()
    for root in (current, *current.parents):
        candidates.append(root / "deploy" / "docker-compose.yml")
        candidates.append(root / "docker-compose.yml")

    for candidate in candidates:
        if candidate.exists() and _compose_supports_runtime_services(candidate):
            return candidate

    embedded = _ensure_embedded_compose_file()
    if embedded.exists():
        return embedded

    raise RuntimeError(
        "Unable to locate Docker Compose file for Caracal runtime. "
        "Set CARACAL_DOCKER_COMPOSE_FILE to a valid compose path."
    )


def _ensure_embedded_compose_file() -> Path:
    _EMBEDDED_COMPOSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _EMBEDDED_COMPOSE_FILE.exists():
        _EMBEDDED_COMPOSE_FILE.write_text(_EMBEDDED_COMPOSE_CONTENT, encoding="utf-8")
    return _EMBEDDED_COMPOSE_FILE


def _compose_supports_runtime_services(compose_file: Path) -> bool:
    try:
        data = compose_file.read_text(encoding="utf-8")
    except OSError:
        return False

    return all(marker in data for marker in ("mcp:", "cli:", "flow:"))


def _resolve_compose_command() -> list[str]:
    docker = shutil.which("docker")
    if docker is not None:
        probe = subprocess.run(
            [docker, "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if probe.returncode == 0:
            return [docker, "compose"]

    legacy = shutil.which("docker-compose")
    if legacy is not None:
        return [legacy]

    raise RuntimeError(
        "Docker Compose is required but not available. Install Docker Compose or "
        "set CARACAL_LOCAL_EXECUTION=1 to run directly on the host."
    )


def _run_local_caracal(args: Sequence[str]) -> None:
    from caracal.cli.main import cli

    cli.main(args=list(args), prog_name="caracal", standalone_mode=True)


def _run_local_flow(args: Sequence[str]) -> None:
    from caracal.flow.main import main

    main.main(args=list(args), prog_name="caracal-flow", standalone_mode=True)


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
