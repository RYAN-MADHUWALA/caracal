# Caracal Python SDK

This directory contains the canonical Python SDK implementation.

## Installation

```bash
pip install caracal-sdk
```

Optional extras:

```bash
# Async helpers
pip install "caracal-sdk[async]"

# Integration with caracal-core runtime
pip install "caracal-sdk[core]"
```

## Layout

- `src/caracal_sdk/`: Open-source SDK surface and transport adapters
- `src/caracal_sdk/enterprise/`: Enterprise-only extension points

## Goals

- Keep SDK surface area minimal and explicit
- Preserve parity with the Node SDK in `sdk/node-sdk/`
- Support CLI/TUI integrations with stable core abstractions
- Ship as a standalone package independent of core internals

## Runtime Endpoint

By default, the SDK targets `http://localhost:8000`.

To target a different containerized runtime endpoint (broker or enterprise),
set:

```bash
export CARACAL_API_URL=http://localhost:8000
```

or pass `base_url` directly when constructing `CaracalClient`.
