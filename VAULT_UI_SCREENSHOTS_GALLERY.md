# 📸 VAULT — OFFICIAL ENTERPRISE UI SCREENSHOTS (OPTION B DARK THEME)

Below are the high-resolution visual previews of the **Vault Storage Console** and **Live Chaos Resilience Studio** built using Option B Premium Dark Tokens (`#080B12` background, `#111827` surface, `#263244` borders, `#38BDF8` sky blue accent).

---

## 1. Vault Storage Console — Main Enterprise Dashboard

![Vault Storage Console Option B Preview](C:\Users\lenovo\.gemini\antigravity\brain\215969c9-a25d-44d3-a04b-aa869d97ec14\vault_optionb_console_1790366881928.jpg)

### Key Interface Highlights:
* **Metric Overview Blocks:** Real-time replicated capacity, data ingress/egress, active node health count, and total object metrics.
* **Storage Node Telemetry:** 5-node cluster state cards showing CPU/RAM usage graphs, disk I/O, and status indicators.
* **Object Storage Inventory:** Table displaying bucket keys, regions, sizes, replication policies, and SHA-256 Merkle root hashes.
* **Resilience Simulation Controls:** Quick action buttons (`Run Stress Test`, `Simulate Node Failure`, `Check Parity Consistency`, `Recover Data`).
* **Streaming Terminal Console:** Streaming dark log window tracking cluster telemetry and background rebalancing events in real time.

---

## 2. Live Chaos Resilience & Merkle Tree Self-Healing View

![Vault Chaos Simulation Option B Preview](C:\Users\lenovo\.gemini\antigravity\brain\215969c9-a25d-44d3-a04b-aa869d97ec14\vault_optionb_chaos_1790366900587.jpg)

### Key Interface Highlights:
* **Hardware Failure Alert:** Storage Node 04 highlighted in **Rose Red** (`CRASHED`) simulating an unannounced node crash.
* **Silent Bitrot Detection:** Storage Node 07 highlighted in **Amber Gold** (`BITROT DETECTED`) showing disk block corruption.
* **Merkle Tree Integrity Breakdown Modal:** Interactive diagram showing leaf node SHA-256 checksum validation and Reed-Solomon parity chunk reconstruction (`1f3a2...ce`).
* **Self-Healing Log Stream:** Terminal output streaming `[BITROT_ALERT]`, `[SELF_HEAL]`, and `[QUORUM_READ]` events in real time.
