---
sidebar_position: 1
title: Caracal Core
---

# Caracal Core

Caracal Core is the **execution authority enforcement engine** for AI agents. It validates mandates, enforces policies, and records every authority decision in a cryptographically verifiable ledger.

## Components

| Component | Description |
|-----------|-------------|
| **Broker Runtime** | Executes provider actions directly using local provider configuration |
| **Authority Policy Engine** | Evaluates whether mandates can be issued based on principal policies |
| **Authority Ledger** | Immutable, Merkle tree-backed log of all authority events |
| **CLI Tools** | Command-line interface for operations and automation |
| **SDK** | Python client for direct authority integration |

---

## Quick Navigation

### Getting Started

1. **[Introduction](./gettingStarted/introduction)** -- Core concepts
2. **[Installation](./gettingStarted/installation)** -- Set up your environment
3. **[Quickstart](./gettingStarted/quickstart)** -- Deploy in 5 minutes

### Operations

- **[CLI Reference](./cliReference/)** -- Full command documentation
- **[Agent Commands](./cliReference/agent)** -- Register and manage principals
- **[Policy Commands](./cliReference/policy)** -- Create authority policies
- **[Ledger Commands](./cliReference/ledger)** -- Query authority events

### Advanced

- **[Architecture](./concepts/architecture)** -- System design
- **[Core vs Flow](./concepts/coreVsFlow)** -- When to use each tool
- **[Merkle Commands](./cliReference/merkle)** -- Cryptographic integrity verification
- **[Delegation Commands](./cliReference/delegation)** -- Authority delegation

### Integration

- **[SDK Reference](./apiReference/sdkClient)** -- Python SDK
- **[MCP Integration](./apiReference/mcpIntegration)** -- Model Context Protocol

## Architecture Overview

```
+-----------------------------------------------------------------+
|                     AI AGENT APPLICATION                         |
+-------------------------------+---------------------------------+
                                |
                                | Authority request
                                v
+-----------------------------------------------------------------+
|                       CARACAL BROKER                             |
|  +----------------+  +--------------------+  +---------------+  |
|  | Validate       |--| Record Authority   |--| Execute       |  |
|  | Mandate Scope  |  | Event              |  | Provider Call |  |
|  +----------------+  +--------------------+  +---------------+  |
+-------------------------------+---------------------------------+
                                |
              +-----------------+-----------------+
              v                 v                 v
     +--------------+  +---------------+  +--------------+
     |  AUTHORITY   |  |  AUTHORITY    |  |   MERKLE     |
     |   POLICY     |  |   LEDGER     |  |    TREE      |
     +--------------+  +---------------+  +--------------+
              |                 |                 |
              +-----------------+-----------------+
                                |
                                v
                       +--------------+
                       |  PostgreSQL  |
                       +--------------+
```

---

## Key Capabilities

### Network-Level Enforcement

The broker validates mandates and provider-scoped resource/action pairs before
any provider request executes.

### Immutable Audit Trail

Every authority event (issued, validated, denied, revoked) is recorded in an append-only ledger with Merkle tree integrity proofs.

### Fail-Closed Design

If the authority engine or ledger is unavailable, all requests are **denied by default**. No unchecked execution.

### Hierarchical Delegation

Principals can delegate scoped authority to other principals. Delegation chains are validated end-to-end.

---

## Next Steps

import Link from '@docusaurus/Link';

<div className="row">
  <div className="col col--4">
    <div className="card">
      <div className="card__header">
        <h3>Quickstart</h3>
      </div>
      <div className="card__body">
        Get Caracal running in 5 minutes
      </div>
      <div className="card__footer">
        <Link className="button button--primary button--block" to="./gettingStarted/quickstart">
          Start Now
        </Link>
      </div>
    </div>
  </div>
  <div className="col col--4">
    <div className="card">
      <div className="card__header">
        <h3>CLI Reference</h3>
      </div>
      <div className="card__body">
        Complete command documentation
      </div>
      <div className="card__footer">
        <Link className="button button--secondary button--block" to="./cliReference/">
          Explore
        </Link>
      </div>
    </div>
  </div>
  <div className="col col--4">
    <div className="card">
      <div className="card__header">
        <h3>SDK</h3>
      </div>
      <div className="card__body">
        Python integration guide
      </div>
      <div className="card__footer">
        <Link className="button button--secondary button--block" to="./apiReference/sdkClient">
          Learn
        </Link>
      </div>
    </div>
  </div>
</div>
