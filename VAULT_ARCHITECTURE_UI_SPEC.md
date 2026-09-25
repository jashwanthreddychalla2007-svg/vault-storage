# VAULT — SYSTEM ARCHITECTURE, API & v0 PROMPT SPECIFICATION
**Project:** Vault — Distributed Fault-Tolerant Object Storage & Visual Chaos Engine  

---

## PHASE 9 — SCREEN ARCHITECTURE

### Key Screens Specification

#### 1. Cluster Command Center & Live Topology Canvas (`/dashboard`)
* **Purpose:** Real-time visual monitoring of cluster nodes, active data chunks, quorum health, and throughput metrics.
* **Target User:** Judges, Devs, Infra Ops.
* **Components:**
  * **Top Navigation:** Cluster status badge (Healthy / Degraded / Rebalancing), Total Storage Capacity indicator, Active Nodes count (e.g. 5/5), Quick Action buttons ("Upload Object", "Inject Chaos").
  * **Center Canvas (Interactive Graph):** Visual node layout (Node 1..5) with active pulses showing data replication streams, Merkle tree status indicators, and health rings.
  * **Side Control Panel (Chaos Suite):** Single-click chaos triggers:
    * `⚡ Kill Random Node`
    * `🧬 Inject Silent Bitrot`
    * `✂️ Partition Cluster (3 vs 2)`
    * `🔄 Trigger Rebalance`
  * **Bottom Activity Console:** Real-time logging stream of WebSocket events (`[INFO] Chunk 3 written to Node 1`, `[WARNING] Bitrot detected on Node 2 chunk 0x4f2a`, `[ACTION] Self-healing started from Node 3...`).

#### 2. Storage Explorer & Integrity Inspector (`/objects`)
* **Purpose:** Inspect stored objects, split chunks, parity blocks, Merkle root hashes, and trigger object downloads with integrity verification.
* **Components:** Object list table, chunk distribution map, Merkle root tree viewer, download button with checksum validation status.

---

## PHASE 18 — v0.dev READY-TO-USE UI GENERATION PROMPTS

### Prompt 1: High-Conversion Modern Infra Dashboard Layout
```text
Build a high-performance, dark-themed enterprise cloud infrastructure dashboard for a fault-tolerant distributed storage system called 'Vault'.

Design Aesthetic:
- Ultra-clean dark obsidian theme (#0B0F17 background, #111827 card background, fine subtle borders #1F2937).
- Accent colors: Electric Cyan (#06B6D4) for active operations, Emerald Green (#10B981) for healthy nodes, Crimson Red (#EF4444) for node failure / bitrot alert, Amber Gold (#F59E0B) for rebalancing.
- Typography: Inter font for body, JetBrains Mono for hashes and IDs.

Layout Structure:
1. Header Bar:
   - Left: Vault logo with glowing cyan shield icon, status pill "CLUSTER ONLINE (5/5 NODES HEALTHY)".
   - Center: Quick stats metrics: "Total Objects: 42", "Storage Efficiency: 67% (Reed-Solomon 2+1)", "Read Quorum: 2/3", "Write Latency: 4.2ms".
   - Right: "Upload New Object" button (cyan glow) and "Chaos Studio" toggle button.

2. Main Canvas Grid (2 Columns):
   - Left Column (65% width): Interactive Visual Cluster Canvas showing 5 node cards positioned in an arcade ring array (Node 1 to Node 5). Each node card displays: CPU usage %, Storage used/total, Node status badge, disk read/write sparkline, and action buttons ("Simulate Crash", "Inject Bitrot").
   - Right Column (35% width):
     - Top Panel: "Chaos Control Panel" with prominent red danger buttons ("Kill Active Node", "Corrupt Random Chunk", "Simulate Split-Brain Partition", "Trigger Self-Healing").
     - Bottom Panel: "Live Audit Log" with streaming dark terminal logs, timestamped color-coded events (Green for Quorum Write, Red for Bitrot, Cyan for Auto-Repair).

3. Footer Status Bar: Real-time WebSocket connection indicator (Active 100ms heartbeat), API latency metric.

Use Tailwind CSS, Lucide-react icons, and Shadcn UI components. Ensure mobile and desktop responsive layout.
```

### Prompt 2: Interactive Object Chunk & Merkle Tree Inspection Modal
```text
Create a detail modal for inspect object chunks and Merkle tree verification in a distributed storage system.

Modal Features:
- Title: "Object Inspection: dataset_2026.parquet (ID: obj_98a72b)"
- File metadata header: Size (12.4 MB), Policy (Reed-Solomon 2+1 Parity), Merkle Root: `0x7f8a92b...`
- Interactive Visual Chunk Pipeline:
  - Visual diagram showing Original File -> Split into Data Chunks (Chunk 1, Chunk 2) + Parity Chunk (Parity 1).
  - Node Mapping Grid showing which server node stores each chunk.
  - Merkle Tree Breakdown showing root hash, branch hashes, and leaf chunk hashes.
- Highlight Status: If a chunk is corrupted, color it Crimson Red with a warning label "BITROT DETECTED - CHECKSUM MISMATCH", and show an animated arrow from healthy Node 1 & Node 3 rebuilding the missing chunk back into Node 2.
- Action Buttons: "Download & Verify Hash", "Trigger Manual Repair", "Close".

Dark mode design matching Vault obsidian infra style with crisp badges and monospace font for hashes.
```

---

## PHASE 19 — TECHNICAL ARCHITECTURE

```mermaid
graph TD
    User([User / Browser]) <--> Frontend[React Next.js UI on Vercel]
    Frontend <-->|REST API| API Gateway[FastAPI Router Engine]
    Frontend <-->|WebSocket| WS Telemetry[Real-Time State Stream]
    
    subgraph "Vault Storage Engine Core"
        API Gateway --> MetadataEngine[Metadata & Quorum Coordinator]
        MetadataEngine --> Chunker[Object Chunker & RS Encoder]
        Chunker --> MerkleEngine[Merkle Tree Hash Generator]
        MerkleEngine --> NodeManager[Virtual Node Manager]
        
        subgraph "Virtual Storage Node Array"
            NodeManager --> Node1[(Node 1: Disk/RAM)]
            NodeManager --> Node2[(Node 2: Disk/RAM)]
            NodeManager --> Node3[(Node 3: Disk/RAM)]
            NodeManager --> Node4[(Node 4: Disk/RAM)]
            NodeManager --> Node5[(Node 5: Disk/RAM)]
        end
        
        NodeManager --> RepairEngine[Background Self-Healing Daemon]
        NodeManager --> ChaosEngine[Chaos Injection Simulator]
    end
```

---

## PHASE 20 — DATABASE & DATA STRUCTURE SPECIFICATION

### In-Memory Metadata Schemas & Entities

#### 1. Object Metadata Table (`objects`)
```json
{
  "object_id": "obj_01h9x7a2",
  "filename": "firmware_v2.bin",
  "size_bytes": 1048576,
  "content_type": "application/octet-stream",
  "durability_policy": "REPLICATION_3X" // or "REED_SOLOMON_2_1",
  "merkle_root": "a4f8e912b7c6...",
  "created_at": "2026-09-26T00:45:00Z",
  "chunks": [
    {
      "chunk_index": 0,
      "chunk_id": "chk_001",
      "size": 524288,
      "sha256_hash": "c1f7a2...",
      "node_locations": [1, 2, 3]
    },
    {
      "chunk_index": 1,
      "chunk_id": "chk_002",
      "size": 524288,
      "sha256_hash": "d2e8b3...",
      "node_locations": [1, 3, 5]
    }
  ]
}
```

#### 2. Node Status Table (`nodes`)
```json
{
  "node_id": 1,
  "name": "Storage-Node-Alpha",
  "status": "ONLINE", // "ONLINE", "FAILED", "DEGRADED", "PARTITIONED"
  "capacity_bytes": 10737418240,
  "used_bytes": 2147483648,
  "chunk_count": 14,
  "last_heartbeat": "2026-09-26T00:45:10Z"
}
```

---

## PHASE 21 — API SPECIFICATION

| Method | Endpoint | Description | Request Payload | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/objects/upload` | Upload new object with replication/RS policy | Form Data (`file`, `policy`) | `{ "object_id": "obj_123", "status": "STORED", "merkle_root": "0x4f..." }` |
| `GET` | `/api/v1/objects/{id}/download` | Quorum read & integrity verified download | None | Binary Stream + Header Hash |
| `GET` | `/api/v1/cluster/status` | Current cluster health & node status | None | `{ "nodes": [...], "quorum": "HEALTHY" }` |
| `POST` | `/api/v1/chaos/kill-node` | Kill specified node ID | `{ "node_id": 2 }` | `{ "status": "NODE_KILLED", "active_nodes": 4 }` |
| `POST` | `/api/v1/chaos/bitrot` | Corrupt 1 byte in random chunk | `{ "node_id": 2 }` | `{ "status": "BITROT_INJECTED", "chunk_id": "chk_001" }` |
| `POST` | `/api/v1/chaos/repair` | Trigger background self-healing | None | `{ "status": "REPAIR_COMPLETE", "healed_chunks": 1 }` |
| `WS` | `/ws/telemetry` | WebSocket live event & metrics stream | None | Real-time JSON log events & state updates |
