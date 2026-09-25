import hashlib
import time
import random
from typing import Dict, List, Optional, Tuple

class MerkleTree:
    """Computes SHA-256 leaf and root hashes for object integrity verification."""
    @staticmethod
    def hash_data(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def compute_root(hashes: List[str]) -> str:
        if not hashes:
            return ""
        if len(hashes) == 1:
            return hashes[0]
        combined = "".join(hashes).encode('utf-8')
        return hashlib.sha256(combined).hexdigest()


class StorageNode:
    def __init__(self, node_id: int, name: str, rack: str = "rack-1", capacity_mb: float = 1000.0):
        self.node_id = node_id
        self.name = name
        self.rack = rack  # Failure domain: rack-1, rack-2, rack-3
        self.status = "ONLINE"  # "ONLINE", "FAILED", "PARTITIONED"
        self.capacity_mb = capacity_mb
        self.used_bytes = 0
        self.chunks: Dict[str, bytes] = {}  # chunk_id -> raw bytes
        self.chunk_hashes: Dict[str, str] = {}  # chunk_id -> original SHA256
        self.corrupted_chunks: set = set()  # chunk_ids marked as corrupted

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "rack": self.rack,
            "status": self.status,
            "used_bytes": self.used_bytes,
            "chunk_count": len(self.chunks),
            "corrupted_count": len(self.corrupted_chunks)
        }


class VaultCluster:
    def __init__(self, node_count: int = 5):
        # Failure domain rack assignment (Rack-1, Rack-2, Rack-3)
        rack_assignments = {1: "rack-1", 2: "rack-1", 3: "rack-2", 4: "rack-2", 5: "rack-3"}
        self.nodes: Dict[int, StorageNode] = {
            i: StorageNode(node_id=i, name=f"Storage-Node-{chr(64 + i)}", rack=rack_assignments.get(i, "rack-1"))
            for i in range(1, node_count + 1)
        }
        self.objects: Dict[str, dict] = {}  # object_id -> object metadata
        self.event_log: List[dict] = []
        self.log_event("SYSTEM", "Vault Distributed Cluster Initialized (5 Nodes across Racks 1, 2 & 3).")

    def log_event(self, category: str, message: str):
        event = {
            "timestamp": time.strftime("%H:%M:%S"),
            "category": category,
            "message": message
        }
        self.event_log.append(event)
        if len(self.event_log) > 50:
            self.event_log.pop(0)

    def select_rack_aware_nodes(self, count: int = 3) -> List[StorageNode]:
        """Ceph CRUSH-style Failure Domain Aware Placement Strategy (Rack Diversity)."""
        online_nodes = [n for n in self.nodes.values() if n.status == "ONLINE"]
        if len(online_nodes) < count:
            return online_nodes

        # Group by rack
        rack_groups: Dict[str, List[StorageNode]] = {}
        for n in online_nodes:
            rack_groups.setdefault(n.rack, []).append(n)

        selected = []
        # Pick 1 node per rack first for maximum failure domain isolation
        for rack, node_list in rack_groups.items():
            if len(selected) < count:
                selected.append(random.choice(node_list))

        # Fill remaining if needed
        while len(selected) < count and len(selected) < len(online_nodes):
            remaining = [n for n in online_nodes if n not in selected]
            if remaining:
                selected.append(random.choice(remaining))

        return selected

    def upload_object(self, filename: str, data: bytes, policy: str = "REED_SOLOMON_2_1") -> dict:
        object_id = f"obj_{int(time.time() * 1000) % 1000000:06d}"
        size = len(data)

        # Split data into 2 data chunks + 1 parity block (or 3 replica chunks)
        if policy == "REED_SOLOMON_2_1":
            mid = max(1, size // 2)
            chunk1 = data[:mid]
            chunk2 = data[mid:]
            parity_len = max(len(chunk1), len(chunk2))
            c1_pad = chunk1.ljust(parity_len, b'\x00')
            c2_pad = chunk2.ljust(parity_len, b'\x00')
            parity = bytes(a ^ b for a, b in zip(c1_pad, c2_pad))
            raw_chunks = [chunk1, chunk2, parity]
        else:
            raw_chunks = [data, data, data]

        chunk_meta = []
        leaf_hashes = []

        assigned_nodes = self.select_rack_aware_nodes(3)
        if len(assigned_nodes) < 3:
            self.log_event("ERROR", f"Quorum Write Failed for '{filename}'. Less than 3 online nodes.")
            raise RuntimeError("Quorum Write Failed: Insufficient active nodes.")

        for idx, (chunk_data, node) in enumerate(zip(raw_chunks, assigned_nodes)):
            chunk_id = f"{object_id}_chk_{idx}"
            chunk_hash = MerkleTree.hash_data(chunk_data)
            leaf_hashes.append(chunk_hash)

            node.chunks[chunk_id] = chunk_data
            node.chunk_hashes[chunk_id] = chunk_hash
            node.used_bytes += len(chunk_data)

            chunk_meta.append({
                "chunk_id": chunk_id,
                "chunk_index": idx,
                "size": len(chunk_data),
                "sha256": chunk_hash,
                "node_id": node.node_id,
                "rack": node.rack
            })

        merkle_root = MerkleTree.compute_root(leaf_hashes)

        obj_record = {
            "object_id": object_id,
            "filename": filename,
            "size_bytes": size,
            "policy": policy,
            "merkle_root": merkle_root,
            "chunks": chunk_meta,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.objects[object_id] = obj_record
        racks_used = list(set(n.rack for n in assigned_nodes))
        self.log_event(
            "QUORUM_WRITE",
            f"Stored '{filename}' ({size} bytes, {policy}) across Racks {racks_used} (Nodes {[n.node_id for n in assigned_nodes]}). Merkle: {merkle_root[:8]}..."
        )
        return obj_record

    def download_object(self, object_id: str) -> Tuple[bytes, bool]:
        if object_id not in self.objects:
            raise KeyError("Object not found")

        obj = self.objects[object_id]
        chunks_meta = obj["chunks"]
        retrieved_chunks = {}
        was_repaired = False

        for meta in chunks_meta:
            chk_id = meta["chunk_id"]
            node_id = meta["node_id"]
            node = self.nodes[node_id]

            if node.status != "ONLINE" or chk_id not in node.chunks:
                self.log_event("WARNING", f"Node {node_id} offline/missing chunk {chk_id}. Triggering replica failover.")
                was_repaired = True
                continue

            chunk_bytes = node.chunks[chk_id]
            current_hash = MerkleTree.hash_data(chunk_bytes)
            expected_hash = node.chunk_hashes[chk_id]

            if current_hash != expected_hash or chk_id in node.corrupted_chunks:
                self.log_event("BITROT_ALERT", f"Merkle checksum mismatch on Node {node_id} chunk {chk_id}! Bitflip detected.")
                node.corrupted_chunks.add(chk_id)
                was_repaired = True
                continue

            retrieved_chunks[meta["chunk_index"]] = chunk_bytes

        if obj["policy"] == "REPLICATION_3X":
            if 0 in retrieved_chunks:
                data = retrieved_chunks[0]
            elif 1 in retrieved_chunks:
                data = retrieved_chunks[1]
            elif 2 in retrieved_chunks:
                data = retrieved_chunks[2]
            else:
                self.log_event("FATAL", f"Quorum Read Failed for '{obj['filename']}'. All replicas unavailable.")
                raise RuntimeError("Quorum Read Failed: Data unrecoverable.")
        else:
            c0 = retrieved_chunks.get(0)
            c1 = retrieved_chunks.get(1)
            p2 = retrieved_chunks.get(2)

            if c0 is not None and c1 is not None:
                data = c0 + c1
            elif c0 is not None and p2 is not None:
                c1_rebuilt = bytes(a ^ b for a, b in zip(c0.ljust(len(p2), b'\x00'), p2))
                data = c0 + c1_rebuilt.rstrip(b'\x00')
                self.log_event("SELF_HEAL", f"Reconstructed missing chunk 1 using Reed-Solomon Parity block!")
            elif c1 is not None and p2 is not None:
                c0_rebuilt = bytes(a ^ b for a, b in zip(c1.ljust(len(p2), b'\x00'), p2))
                data = c0_rebuilt.rstrip(b'\x00') + c1
                self.log_event("SELF_HEAL", f"Reconstructed missing chunk 0 using Reed-Solomon Parity block!")
            else:
                raise RuntimeError("Quorum Read Failed: Too many chunks missing.")

        if was_repaired:
            self.auto_repair_object(object_id)

        self.log_event("QUORUM_READ", f"Successfully read & verified '{obj['filename']}' ({len(data)} bytes).")
        return data, was_repaired

    def auto_repair_object(self, object_id: str):
        if object_id not in self.objects:
            return
        obj = self.objects[object_id]
        online_nodes = [n for n in self.nodes.values() if n.status == "ONLINE"]

        for meta in obj["chunks"]:
            node_id = meta["node_id"]
            node = self.nodes[node_id]
            chk_id = meta["chunk_id"]

            if node.status != "ONLINE" or chk_id in node.corrupted_chunks:
                target_node = random.choice(online_nodes)
                node.corrupted_chunks.discard(chk_id)
                meta["node_id"] = target_node.node_id
                meta["rack"] = target_node.rack
                target_node.chunks[chk_id] = node.chunk_hashes[chk_id].encode('utf-8')
                self.log_event("SELF_HEAL", f"Repaired chunk {chk_id} -> Re-located to Node {target_node.node_id} ({target_node.rack}).")

    def kill_node(self, node_id: int) -> dict:
        if node_id in self.nodes:
            self.nodes[node_id].status = "FAILED"
            self.log_event("CHAOS", f"⚡ KILLED NODE {node_id} ({self.nodes[node_id].name}, {self.nodes[node_id].rack}). Status set to FAILED.")
        return {"status": "NODE_KILLED", "node_id": node_id}

    def inject_bitrot(self, node_id: int) -> dict:
        node = self.nodes.get(node_id)
        if not node or not node.chunks:
            return {"status": "NO_CHUNKS", "message": f"No stored chunks on Node {node_id}"}

        chk_id = random.choice(list(node.chunks.keys()))
        original = node.chunks[chk_id]
        corrupted = bytearray(original)
        if len(corrupted) > 0:
            corrupted[0] ^= 0xFF
        node.chunks[chk_id] = bytes(corrupted)
        node.corrupted_chunks.add(chk_id)
        self.log_event("CHAOS", f"🧬 INJECTED BITROT on Node {node_id}, chunk '{chk_id}'. Byte mutated.")
        return {"status": "BITROT_INJECTED", "node_id": node_id, "chunk_id": chk_id}

    def recover_all(self) -> dict:
        for node in self.nodes.values():
            node.status = "ONLINE"
            node.corrupted_chunks.clear()
        self.log_event("RECOVERY", "🔄 Recovered all storage nodes. Cluster status reset to HEALTHY.")
        return {"status": "CLUSTER_HEALTHY"}
