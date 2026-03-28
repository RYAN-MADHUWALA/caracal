# Caracal SDK Monorepo Layout

Canonical SDK implementations now live under this directory:

- `python-sdk/`: Python SDK (`caracal_sdk`)
- `node-sdk/`: Node/TypeScript SDK (`@caracal/core`)

Both SDKs keep a parallel structure:

- Default package surface is open-source
- `enterprise/` contains enterprise extensions

## Runtime Endpoint Contract

Both SDKs resolve the runtime endpoint with the same rule:

1. `CARACAL_API_URL` environment variable, when present
2. Fallback to `http://localhost:${CARACAL_API_PORT:-8000}`

This keeps client code unchanged across broker and enterprise gateway modes.
