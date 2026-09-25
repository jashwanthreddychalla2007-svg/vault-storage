import hashlib
import math
from typing import List, Dict, Any, Optional

class MerkleNode:
    def __init__(self, hash_val: str, left: Optional['MerkleNode'] = None, right: Optional['MerkleNode'] = None, chunk_index: Optional[int] = None, data_sample: Optional[str] = None):
        self.hash_val = hash_val
        self.left = left
        self.right = right
        self.chunk_index = chunk_index
        self.data_sample = data_sample

    def to_dict( me ) -> Dict[str, Any]:
        return {
            "hash": me.hash_val[:12] + "...",
            "full_hash": me.hash_val,
            "chunk_index": me.chunk_index,
            "data_sample": me.data_sample,
            "left": me.left.to_dict() if me.left else None,
            "right": me.right.to_dict() if me.right else None
        }

class MerkleTreeEngine:
    """Computes Merkle Trees for object payload byte blocks and provides byte-level bitrot diff inspection."""

    @staticmethod
    def build_tree(data: bytes, chunk_size: int = 16) -> Dict[str, Any]:
        if not data:
            data = b"EMPTY_PAYLOAD"

        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        leaf_nodes = []

        for idx, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk).hexdigest()
            sample = chunk.decode('utf-8', errors='replace')
            leaf_nodes.append(MerkleNode(hash_val=chunk_hash, chunk_index=idx, data_sample=sample))

        current_level = leaf_nodes
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                    combined_hash = hashlib.sha256((left.hash_val + right.hash_val).encode()).hexdigest()
                    parent = MerkleNode(hash_val=combined_hash, left=left, right=right)
                else:
                    parent = left
                next_level.append(parent)
            current_level = next_level

        root_node = current_level[0] if current_level else None
        return {
            "root_hash": root_node.hash_val if root_node else "",
            "chunk_count": len(chunks),
            "tree_structure": root_node.to_dict() if root_node else {}
        }

    @staticmethod
    def inspect_bitrot_diff(original_data: bytes, corrupted_data: bytes, chunk_size: int = 16) -> Dict[str, Any]:
        orig_chunks = [original_data[i:i + chunk_size] for i in range(0, len(original_data), chunk_size)]
        corr_chunks = [corrupted_data[i:i + chunk_size] for i in range(0, len(corrupted_data), chunk_size)]

        diffs = []
        for idx in range(max(len(orig_chunks), len(corr_chunks))):
            o_c = orig_chunks[idx] if idx < len(orig_chunks) else b""
            c_c = corr_chunks[idx] if idx < len(corr_chunks) else b""

            o_hash = hashlib.sha256(o_c).hexdigest()
            c_hash = hashlib.sha256(c_c).hexdigest()

            is_corrupt = (o_hash != c_hash)
            if is_corrupt:
                diffs.append({
                    "chunk_index": idx,
                    "byte_offset_start": idx * chunk_size,
                    "byte_offset_end": (idx * chunk_size) + len(o_c),
                    "expected_sha256": o_hash,
                    "actual_sha256": c_hash,
                    "expected_sample": o_c.decode('utf-8', errors='replace'),
                    "actual_sample": c_c.decode('utf-8', errors='replace'),
                    "status": "CORRUPTED_BITROT_DETECTED"
                })

        return {
            "total_chunks_scanned": max(len(orig_chunks), len(corr_chunks)),
            "corrupted_chunk_count": len(diffs),
            "diff_details": diffs
        }
