# 🎨 VAULT — OFFICIAL ENTERPRISE SAAS UI PROMPT GUIDE (v0.dev)

This guide provides an **Official Enterprise SaaS UI Prompt** engineered specifically for **v0.dev** to generate a clean, non-AI-looking, production-quality cloud console for **Vault** matching the design language of Cloudflare, Vercel, and Datadog.

---

## 🏛️ OFFICIAL ENTERPRISE INFRASTRUCTURE DESIGN RULES

* **Color Palette:** Slate & Zinc Dark (`#090D16` primary background, `#0F172A` surface cards, `#1E293B` borders, `#6366F1` Indigo accents, `#10B981` Emerald healthy status, `#F43F5E` Rose danger status).
* **Typography:** `Inter` for clean sans-serif text, `JetBrains Mono` strictly for hashes, IPs, and event log streams.
* **Layout:** Functional 12-column grid layout with high data density, 1px subtle borders, clean 4px border radius, and zero unnecessary decorative glowing animations.

---

## 🚀 OFFICIAL PROMPT 1: ENTERPRISE CLOUD STORAGE CONSOLE (`VaultConsole.jsx`)

Copy and paste this prompt into [v0.dev](https://v0.dev):

```text
Build an official, production-grade enterprise cloud storage console for a fault-tolerant distributed storage engine named 'Vault Storage Console'. 

Design Language & Aesthetic (IMPORTANT - DO NOT LOOK LIKE A GENERIC AI DEMO):
- Clean, functional enterprise infrastructure styling similar to Cloudflare, Datadog, or AWS Management Console.
- Color Palette: Deep Slate background (#090D16), surface containers (#0F172A), border lines (#1E293B), Indigo brand action buttons (#6366F1), Emerald green (#10B981) for online status, Muted Rose (#F43F5E) for crashed nodes, Muted Amber (#F59E0B) for bitrot warnings.
- Fonts: Inter for clean sans-serif interface, JetBrains Mono strictly for technical metrics, hashes, and terminal logs.
- Avoid all generic AI tropes: NO purple/pink glowing radial background blobs, NO heavy glassmorphism blurs, NO oversized rounded cards. Keep border-radius crisp (4px to 8px).

Layout Architecture:

1. Top Navigation Bar:
   - Left: Vault logo (Indigo square with white 'V'), title "Vault Storage Console", version badge "v1.2.0-prod", region text "Region: us-east-1 (Quorum N=5, R=2, W=2)".
   - Right: Cluster status pill ("5/5 Nodes Healthy" with emerald dot) and Indigo button "+ Upload Object".

2. Metrics Summary Header (4 Metric Cards Grid):
   - Card 1: Total Cluster Storage ("50.0 GB / 50.0 GB")
   - Card 2: Active Storage Policy ("Reed-Solomon 2+1 Erasure Coding")
   - Card 3: Anti-Entropy Scrubber ("Active - 5s Sweep Loop")
   - Card 4: Mean Recovery Latency ("< 140 ms")

3. Main Dashboard Grid (2 Columns - 7 cols / 5 cols):

   - Left Column (7 cols):
     - "Storage Nodes Telemetry & Health": 
       Compact 5-node status grid (Node 1 to Node 5). Each node card contains:
       - Node Name (e.g., Storage-Node-A) in monospace font
       - Status badge ("ONLINE" in emerald, "CRASHED" in rose, "BITROT" in amber)
       - Stored Blocks count & Storage Used (KB)
     - "Object Storage Inventory": 
       Table displaying Object ID, Key filename, Durability Policy tag, SHA-256 Merkle Root hash (monospace), and a "Download" button.

   - Right Column (5 cols):
     - "Resilience Simulation Controls": 
       Action panel with clean buttons:
       - "Simulate Node Death" (rose tinted button)
       - "Inject Disk Bitrot" (amber tinted button)
       - "Reset Cluster State" (slate secondary button)
     - "System Event Stream": 
       Dark terminal log (#090D16) displaying streaming timestamped log entries with subtle indigo/emerald timestamps.

Use React 18, Tailwind CSS, Lucide-react icons, and Shadcn UI components. Ensure crisp 1px borders, subtle hover highlights, and compact information density.
```
