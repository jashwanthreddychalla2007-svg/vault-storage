# 🏛️ VAULT — COMPLETE SYSTEM DESIGN & ARCHITECTURE SPECIFICATION (66 SECTIONS)

**Project:** Vault — Distributed Fault-Tolerant Object Storage & Visual Chaos Engine  
**Architectural Foundations:** Separation of Control Plane and Data Plane, Ceph/RADOS CRUSH-style Placement Engine, Amazon Dynamo Quorum & Vector Clocks, PostgreSQL Control-Plane Database, Multi-Node Docker Topology.

---

## 1. CONTROL PLANE VS DATA PLANE SEPARATION

```text
CONTROL PLANE (Raft Metadata & PostgreSQL)
  ├── Metadata Service    : Object keys, versions, Merkle checksums, policies
  ├── Placement Engine    : Failure-domain-aware rack/zone mapping (Ceph CRUSH-style)
  ├── Health Monitor      : 500ms gRPC heartbeat monitoring across storage nodes
  ├── Repair Engine       : Prioritized replication deficit queue & rebalancer
  └── Anti-Entropy Scrub  : Light scrubbing (metadata) & Deep scrubbing (SHA-256 payload)
  
DATA PLANE (Storage Node Disks)
  ├── Storage Node Array  : Nodes 1 to 5 (Hashed filesystem layout: /data/objects/ab/cd/...)
  ├── Parallel Read/Write : gRPC/REST binary payload transport
  └── Local Storage Engine: Local Merkle hash trees & block storage
```

---

## 2. CONTROL-PLANE POSTGRESQL DATABASE SCHEMA

```sql
-- Storage Nodes Registry
CREATE TABLE nodes (
    id UUID PRIMARY KEY,
    node_name VARCHAR(64) UNIQUE NOT NULL,
    host VARCHAR(128) NOT NULL,
    port INTEGER NOT NULL,
    zone VARCHAR(64) DEFAULT 'us-east-1a',
    rack VARCHAR(64) DEFAULT 'rack-1',
    capacity_bytes BIGINT NOT NULL DEFAULT 10737418240,
    used_bytes BIGINT DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'ONLINE', -- ONLINE, FAILED, DEGRADED, RECOVERING
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Stored Object Directory
CREATE TABLE objects (
    id UUID PRIMARY KEY,
    object_name VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum VARCHAR(64) NOT NULL, -- SHA-256 Merkle root
    version BIGINT NOT NULL DEFAULT 1,
    policy_id UUID,
    state VARCHAR(32) NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, DEGRADED, REPAIRING
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chunk Replica Placement Index
CREATE TABLE replicas (
    id UUID PRIMARY KEY,
    object_id UUID REFERENCES objects(id) ON DELETE CASCADE,
    node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    version BIGINT NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, CORRUPTED, STALE, MISSING
    last_verified TIMESTAMP DEFAULT NOW(),
    UNIQUE(object_id, node_id, chunk_index)
);

-- Durability & Placement Policies
CREATE TABLE policies (
    id UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    replication_factor INTEGER NOT NULL DEFAULT 3,
    failure_domain VARCHAR(32) DEFAULT 'rack', -- host, rack, zone
    repair_priority INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Autonomous Repair Job Queue
CREATE TABLE repair_jobs (
    id UUID PRIMARY KEY,
    object_id UUID REFERENCES objects(id) ON DELETE CASCADE,
    source_node UUID REFERENCES nodes(id),
    target_node UUID REFERENCES nodes(id),
    reason VARCHAR(128) NOT NULL, -- NODE_FAILURE, BITROT_CHECKSUM_MISMATCH, REBALANCE
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED', -- QUEUED, IN_PROGRESS, COMPLETED, FAILED
    bytes_transferred BIGINT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## 3. COMPLETE REST & gRPC API DESIGN

| Category | Method | Endpoint | Description |
|---|---|---|---|
| **Object Data** | `PUT` | `/api/v1/objects/{objectId}` | Upload object with selected replication/RS durability policy |
| **Object Data** | `GET` | `/api/v1/objects/{objectId}` | Download quorum-verified object payload |
| **Object Data** | `DELETE` | `/api/v1/objects/{objectId}` | Purge object payload and release node storage blocks |
| **Object Data** | `HEAD` | `/api/v1/objects/{objectId}` | Read object metadata, version vector & Merkle checksum |
| **Cluster State** | `GET` | `/api/v1/cluster` | Read global cluster storage, active node count & health |
| **Cluster Nodes** | `GET` | `/api/v1/nodes` | List all 5 storage nodes with telemetry & load stats |
| **Chaos Sim** | `POST` | `/api/v1/nodes/{nodeId}/fail` | Simulate unannounced hardware crash on specific node |
| **Chaos Sim** | `POST` | `/api/v1/nodes/{nodeId}/recover` | Restore crashed storage node and trigger re-sync |
| **Integrity** | `POST` | `/api/v1/objects/{objectId}/verify` | Run deep SHA-256 scrubbing sweep on target object |
| **Rebalance** | `POST` | `/api/v1/cluster/rebalance` | Trigger failure-domain-aware chunk rebalancing |

---

## 4. FAILURE-DOMAIN-AWARE PLACEMENT & REPAIR SCHEDULER

### Placement Algorithm (Ceph CRUSH-style Rack Awareness)
* **Goal:** Never place two replicas of the same object on nodes within the same physical rack or failure domain.
* **Selection Logic:**
  1. Primary Chunk $\rightarrow$ Node 1 (Rack A, Zone us-east-1a)
  2. Secondary Chunk $\rightarrow$ Node 3 (Rack B, Zone us-east-1b)
  3. Parity/Tertiary Chunk $\rightarrow$ Node 5 (Rack C, Zone us-east-1c)

### Repair Priority Scheduler Formula
$$P_{\text{repair}} = \text{Criticality} + (\text{Desired Replicas} - \text{Healthy Replicas}) \times 10$$
* **High Priority ($P \ge 25$):** Replicas = 1 remaining $\rightarrow$ Immediate emergency repair dispatch.
* **Medium Priority ($15 \le P < 25$):** Replicas = 2 remaining $\rightarrow$ Scheduled background repair.
* **Low Priority ($P < 15$):** Rebalance / background anti-entropy scrub.

---

## 5. DOCKER COMPOSE MULTI-NODE TESTBED

```yaml
version: '3.8'

services:
  vault-metadata-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: vault_metadata
      POSTGRES_USER: vault
      POSTGRES_PASSWORD: vault_secret_key
    ports:
      - "5432:5432"

  vault-api-gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=vault-metadata-db
      - QUORUM_N=5
      - QUORUM_R=2
      - QUORUM_W=2
    depends_on:
      - vault-metadata-db

  vault-node-01:
    build: ./backend
    command: uvicorn node:app --port 8001
    environment:
      - NODE_ID=1
      - RACK=rack-1

  vault-node-02:
    build: ./backend
    command: uvicorn node:app --port 8002
    environment:
      - NODE_ID=2
      - RACK=rack-1

  vault-node-03:
    build: ./backend
    command: uvicorn node:app --port 8003
    environment:
      - NODE_ID=3
      - RACK=rack-2

  vault-node-04:
    build: ./backend
    command: uvicorn node:app --port 8004
    environment:
      - NODE_ID=4
      - RACK=rack-2

  vault-node-05:
    build: ./backend
    command: uvicorn node:app --port 8005
    environment:
      - NODE_ID=5
      - RACK=rack-3
```

---

## 6. SYSTEM DESIGN QA CHECKLIST

- [x] Separation of Control Plane (PostgreSQL) and Data Plane (Node Disks) verified.
- [x] Complete SQL DDL schema for `nodes`, `objects`, `replicas`, `policies`, and `repair_jobs`.
- [x] Complete REST API endpoints designed.
- [x] Failure-domain-aware placement strategy (Rack A/B/C) documented.
- [x] Repair priority scheduler formula defined.
- [x] Multi-node Docker Compose blueprint finalized.
