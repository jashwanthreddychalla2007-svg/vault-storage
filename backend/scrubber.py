import time
import asyncio
from typing import Dict, List
from cluster import VaultCluster, MerkleTree

class AntiEntropyScrubber:
    """
    Background Anti-Entropy Scrubbing Engine.
    Periodically sweeps all storage node blocks, validates SHA-256 Merkle hashes,
    and automatically repairs corrupted chunks before client reads.
    """
    def __init__(self, cluster: VaultCluster, interval_seconds: int = 5):
        self.cluster = cluster
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.scrub_count = 0
        self.repaired_chunks_total = 0

    async def start_scrubbing_loop(self):
        self.is_running = True
        self.cluster.log_event("SCRUBBER", "🛡️ Anti-Entropy Background Scrubbing Daemon Started (Interval: 5s).")
        
        while self.is_running:
            await asyncio.sleep(self.interval_seconds)
            self.scrub_count += 1
            await self.perform_scrub_sweep()

    async def perform_scrub_sweep(self):
        corrupted_found = 0
        healed_count = 0

        for obj_id, obj in list(self.cluster.objects.items()):
            for chunk_meta in obj["chunks"]:
                chk_id = chunk_meta["chunk_id"]
                node_id = chunk_meta["node_id"]
                node = self.cluster.nodes.get(node_id)

                if not node or node.status != "ONLINE":
                    continue

                if chk_id in node.chunks:
                    actual_data = node.chunks[chk_id]
                    actual_hash = MerkleTree.hash_data(actual_data)
                    expected_hash = node.chunk_hashes[chk_id]

                    # Detect silent bitrot
                    if actual_hash != expected_hash or chk_id in node.corrupted_chunks:
                        corrupted_found += 1
                        node.corrupted_chunks.add(chk_id)
                        self.cluster.log_event(
                            "SCRUB_ALERT",
                            f"🔍 Scrubber detected bitrot on Node {node_id}, Chunk '{chk_id}'. Initiating auto-healing."
                        )
                        # Trigger background repair
                        self.cluster.auto_repair_object(obj_id)
                        healed_count += 1

        self.repaired_chunks_total += healed_count
        if corrupted_found > 0:
            self.cluster.log_event(
                "SCRUB_SUMMARY",
                f"✅ Scrub Sweep #{self.scrub_count}: Detected {corrupted_found} bitrot chunks. Auto-repaired {healed_count} chunks."
            )
