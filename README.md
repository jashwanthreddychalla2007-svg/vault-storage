# 🛡️ VAULT — Enterprise Self-Healing 6-Node Distributed Object Storage Engine

> **Tagline:** Store data. Survive hardware crashes. Detect bitrot. Auto-repair instantly.  
> **A 100% working, zero-downtime distributed object storage platform with real 6-node physical chunk separation, 2-zone CRUSH placement, 9-table metadata DB, and automated anti-entropy healing.**

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-emerald.svg)
![SQLite/PostgreSQL](https://img.shields.io/badge/Database-9%20Tables-purple.svg)
![Nodes](https://img.shields.io/badge/Nodes-6%20Nodes%20(Zone%20A%20%2B%20B)-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-sky.svg)
![Build Status](https://img.shields.io/badge/CI%2FCD-Passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## 🌐 Live Web Console & Deployment Links

- **Live Web App Console:** [jashwanthreddychalla2007-svg.github.io/vault-storage/](https://jashwanthreddychalla2007-svg.github.io/vault-storage/)
- **Interactive Presentation Deck & PDF Report:** [jashwanthreddychalla2007-svg.github.io/vault-storage/VAULT_PRESENTATION_SLIDES.html](https://jashwanthreddychalla2007-svg.github.io/vault-storage/VAULT_PRESENTATION_SLIDES.html)
- **GitHub Source Repository:** [github.com/jashwanthreddychalla2007-svg/vault-storage](https://github.com/jashwanthreddychalla2007-svg/vault-storage)

---

## 🌟 Architecture & Core Concept

Vault is an enterprise-grade distributed object storage system built according to a 62-point master specification. Inspired by **Ceph RADOS**, **MinIO**, **AWS S3**, and **Google File System (GFS)**, Vault guarantees data durability across independently failing hardware nodes.

```
                              ┌──────────────────────────────┐
                              │          FRONTEND            │
                              │   Option B Dark Console UI   │
                              └──────────────┬───────────────┘
                                             │ HTTP / REST / WebSockets
                                             ▼
                              ┌──────────────────────────────┐
                              │     CONTROL & DATA PLANE     │
                              │  FastAPI / Engine / Scrubber │
                              └──────────────┬───────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          ┌─────────────────────────┐                 ┌─────────────────────────┐
          │   METADATA DB (9 TAB)   │                 │ PHYSICAL STORAGE ENGINE │
          │ Users, Buckets, Objects,│                 │ Chunking & Replicas     │
          │ Versions, Replicas,     │                 │ Zone A (Node 1, 2, 3)   │
          │ Nodes, Repairs, Events  │                 │ Zone B (Node 4, 5, 6)   │
          └─────────────────────────┘                 └─────────────────────────┘
```

### The Causal Life Cycle of an Object in Vault:
1. **Upload Payload:** File split into chunks, digested via cryptographic `SHA-256`, assigned version $v1$.
2. **Zone-Aware Placement:** Distributed across **Zone A** (`Node 1..3`) and **Zone B** (`Node 4..6`) based on available capacity.
3. **Quorum Write ($W \ge 2$):** Confirms success once quorum written across multi-zone physical disks.
4. **Chaos Injection:** Hardware node crashed (`FAIL`), disk block corrupted (`BITROT`), or network partitioned (`PARTITION`).
5. **Zero-Downtime Read ($R \ge 1$):** Client reads file smoothly from surviving replicas.
6. **5-Second Anti-Entropy Auto-Healing:** System detects missing/corrupted block, schedules repair job, copies healthy chunk to target node, verifies `SHA-256`, and updates metadata back to `HEALTHY`.

---

## ✨ Key Technical Capabilities & Innovation

- 🛡️ **Self-Healing Distributed Engine:** Background daemon scans cluster health every 5s, restoring degraded RF ($3/3$) automatically.
- 🏢 **Multi-Zone Fault Domains:** 6 physical node directories (`storage/node1/` .. `storage/node6/`) mapped to `ZONE_A` and `ZONE_B`.
- 🗄️ **9-Table Relational Schema:** SQLite/PostgreSQL schema tracking `users`, `buckets`, `objects`, `object_versions`, `object_replicas`, `storage_nodes`, `repair_jobs`, `events`, and `policies`.
- 🌳 **Merkle Tree & Bitrot Visualizer:** Inspects structural cryptographic hash roots down to byte offsets and displays real-time disk block corruption diffs.
- ⚡ **AWS S3 API & IAM Policy Gateway:** Compatible S3 REST API endpoint simulation with code generators for `boto3`, `AWS CLI`, `Node.js`, and `curl`.
- 🔐 **OWASP Role Guards (RBAC):** Server-side permissions enforcing `Platform Owner`, `DevOps Engineer`, and `Viewer` controls with `403 Forbidden` alerts.
- 📊 **Raft Consensus & Benchmarking:** Raft term election log viewer and latency micro-benchmarks ($\text{P50}$, $\text{P95}$, $\text{P99}$, throughput).

---

## 🎬 Step-by-Step Hackathon Judge Demonstration Flow

Follow this 9-step story to demonstrate Vault's complete resilience in under 2 minutes:

1. **Cluster Health Check:** Open the web console. Observe 6 nodes (Nodes 1–3 in Zone A, Nodes 4–6 in Zone B) in `HEALTHY` green state.
2. **Upload Payload:** In **MY STORAGE**, upload a sample file (`research.pdf`). Observe replica allocation across Zone A & B.
3. **Simulate Hardware Crash:** Switch to **ADMIN CHAOS LAB**, click `FAIL` on **Node 4**. Node 4 turns RED.
4. **Observe Degradation:** Check Object Status — flagged as `DEGRADED (2/3 Replicas)`.
5. **Zero-Downtime Download:** Return to **MY STORAGE** and click `Download`. The file downloads instantly from surviving nodes.
6. **Automatic 5s Repair:** Watch the **Auto-Repair Queue** in Chaos Lab. Vault transfers data to a healthy node and restores status to `HEALTHY`.
7. **Inject Silent Bitrot:** Click `BITROT` on Node 1 in Chaos Lab to flip magnetic bytes on disk.
8. **Inspect Merkle Healing:** Go to **MERKLE & BITROT** tab. Inspect the exact corrupted byte offset. Watch Vault silently heal the corrupted replica on the fly.
9. **Role Guard Test:** Change role at top right from `Platform Owner` to `Viewer` and attempt to fail a node — observe `403 Forbidden` protection.

---

## 🚀 Quick Start & Installation

### Option 1: One-Command Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/jashwanthreddychalla2007-svg/vault-storage.git
cd vault-storage

# 2. Launch 6-Node Cluster & FastAPI Control Plane
docker-compose up -d

# 3. Open Web UI
# Access http://localhost:8000 in your browser
```

### Option 2: Local Python Execution

```bash
# 1. Clone repository
git clone https://github.com/jashwanthreddychalla2007-svg/vault-storage.git
cd vault-storage

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Launch Backend Engine
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in any browser.

---

## 📄 API Reference Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Cluster status, healthy node count (`6 / 6`) & engine state |
| `GET` | `/api/v1/cluster/status` | Real-time status of all 6 nodes across Zone A & Zone B |
| `POST` | `/api/v1/objects/upload` | Upload payload with 2-zone CRUSH placement & SHA-256 hash |
| `GET` | `/api/v1/objects/{id}/download` | Quorum read download with fallback to healthy replicas |
| `DELETE`| `/api/v1/objects/{id}` | Tombstone soft-deletion with version increment |
| `POST` | `/api/v1/chaos/fail-node` | Simulate unannounced hardware node crash |
| `POST` | `/api/v1/chaos/bitrot` | Inject byte corruption into specific storage block |
| `POST` | `/api/v1/chaos/partition` | Simulate partial network partition on a node |
| `GET` | `/api/v1/merkle/inspect/{id}` | Structural SHA-256 Merkle tree breakdown |
| `GET` | `/api/v1/benchmark/run` | Run performance benchmarks (TTFB, P50/P95/P99 latency) |

---

## 🛠️ Technology Stack

- **Control Plane & API:** Python 3.12, FastAPI, Uvicorn, Asyncio, WebSockets
- **Metadata Database:** SQLite / PostgreSQL (9 Relational Tables)
- **Data Plane:** Multi-node physical disk chunk storage, SHA-256 Checksums
- **Frontend Console:** HTML5, React, Tailwind CSS (Dark Option B Theme), WebSockets
- **DevOps:** Docker, Docker Compose, GitHub Actions, GitHub Pages

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
