# 🛡️ VAULT — Enterprise Fault-Tolerant Distributed Object Storage Engine

> **Tagline:** Store data. Survive failures. Repair automatically.  
> **Tagline 2:** Fault-tolerant distributed object storage engineered for unreliable and independently failing nodes.

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-emerald.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-sky.svg)
![Build Status](https://img.shields.io/badge/CI%2FCD-Passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## 🌟 Overview & Product Vision

Vault is an enterprise-grade distributed object storage engine inspired by **Ceph RADOS**, **MinIO**, **AWS S3**, and **Google File System (GFS)**. It handles unannounced hardware node failures, silent bitrot data corruption, and concurrent write collisions with zero human intervention.

```
                  +-----------------------------------+
                  |      VAULT CLIENT / CONSOLE       |
                  |  (Storage vs Operations Dual UI)  |
                  +-----------------+-----------------+
                                    | HTTPS / REST / WebSockets
                                    v
                  +-----------------+-----------------+
                  |     VAULT CONTROL & DATA API      |
                  |    (FastAPI / RBAC / S3 Gateway)  |
                  +--------+----------------+---------+
                           |                |
             +-------------+                +-------------+
             |                                            |
             v                                            v
+------------------------+                    +------------------------+
|   RAFT METADATA ENGINE |                    | ANTI-ENTROPY SCRUBBER  |
| - Term Election Logs   |                    | - Merkle Tree Verification|
| - Vector Clock Ordering|                    | - Silent Bitrot Healing|
+------------+-----------+                    +------------+-----------+
             |                                             |
             +--------------------+------------------------+
                                  |
                                  v
              +-------------------+-------------------+
              |  5 DISTRIBUTED STORAGE NODE DAEMONS   |
              |  [Rack 1]   [Rack 2]   [Rack 3]       |
              +---------------------------------------+
```

---

## ✨ Key Features & Technical Innovation

- 🛡️ **Causal Auto-Healing Pipeline:** `Upload` $\rightarrow$ `CRUSH Rack Placement` $\rightarrow$ `Chaos Node Kill` $\rightarrow$ `Quorum Read ($R \ge 2$)` $\rightarrow$ `Anti-Entropy Repair Sweep` $\rightarrow$ `Restored ($N = 3$)`.
- 🌳 **Interactive Merkle Tree Graph Visualizer:** Structural SHA-256 tree breakdown down to the 16-byte leaf level with a byte-offset bitrot diff inspector.
- ⚡ **AWS S3 SDK Gateway & IAM Simulator:** Executable code snippets for **Python (`boto3`)**, **AWS CLI**, **Node.js (`@aws-sdk`)**, **Go**, and **Curl**, plus AWS IAM JSON policy evaluation (`Effect: Allow/Deny`).
- 🔐 **Multi-Tenant OWASP RBAC Identity Engine:** 6 granular roles (`platform_owner`, `organization_owner`, `organization_admin`, `storage_operator`, `developer`, `viewer`) with server-side authorization guards returning `403 Forbidden`.
- 📊 **Performance & Benchmarking Lab:** Real-time **TTFB**, **P50/P95/P99 latency percentiles**, and sequential throughput ($\text{MB/s}$).
- 🤖 **Predictive S.M.A.R.T Machine Learning Evacuation:** Monitors hardware metrics (reallocated sectors, temperature, errors) and auto-evacuates at-risk nodes ($<40\%$ health) before hardware crash.

---

## 🚀 Quick Start Guide

### Option 1: Docker Compose (Recommended One-Command Start)

```bash
# Clone repository
git clone https://github.com/your-username/vault-storage.git
cd vault-storage

# Start full multi-node storage cluster and control plane
docker-compose up -d

# Open browser to access frontend console
open frontend/index.html
```

### Option 2: Local Python Runtime Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Launch Vault FastAPI Storage Engine
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Access API health at: `http://localhost:8000/health`  
Open [index.html](./frontend/index.html) in any web browser.

---

## 📄 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Cluster health status, node count & engine status |
| `GET` | `/api/v1/cluster/status` | Full telemetry state of all 5 storage nodes & Raft consensus |
| `POST` | `/api/v1/objects/upload` | Upload payload with CRUSH rack allocation & SHA-256 hashing |
| `GET` | `/api/v1/objects/{id}/download` | Quorum read download ($R \ge 2$) with auto-repair fallback |
| `POST` | `/api/v1/chaos/kill-node` | Simulate node hardware crash |
| `POST` | `/api/v1/chaos/bitrot` | Inject bitrot corruption into specific node storage block |
| `GET` | `/api/v1/merkle/inspect/{id}` | Structural Merkle tree digest inspection |
| `GET` | `/api/v1/benchmark/run` | Execute micro-benchmarks measuring TTFB & P50/P95/P99 latency |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Asyncio, WebSockets, Pydantic, gRPC Proto
- **Frontend Console:** HTML5, React, Tailwind CSS (Option B Dark Theme), WebSockets
- **Integrity & Consensus:** Merkle Trees, SHA-256, Raft Consensus State Machine, Vector Clocks
- **DevOps:** Docker, Docker Compose, GitHub Actions CI/CD

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
