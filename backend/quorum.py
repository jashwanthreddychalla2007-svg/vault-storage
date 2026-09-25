import time
from typing import Dict, List, Tuple, Optional

class VectorClock:
    def __init__(self, node_id: str, sequence: int = 1):
        self.clocks: Dict[str, int] = {node_id: sequence}
        self.timestamp = int(time.time() * 1000)

    def increment(self, node_id: str):
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
        self.timestamp = int(time.time() * 1000)

    def is_newer_than(self, other: 'VectorClock') -> bool:
        """Returns True if self dominates other in vector clock ordering."""
        if not other:
            return True
        greater_or_equal = True
        strictly_greater = False
        all_keys = set(self.clocks.keys()).union(set(other.clocks.keys()))
        
        for k in all_keys:
            v1 = self.clocks.get(k, 0)
            v2 = other.clocks.get(k, 0)
            if v1 < v2:
                greater_or_equal = False
            if v1 > v2:
                strictly_greater = True
                
        return greater_or_equal and strictly_greater

    def to_dict(self) -> dict:
        return {
            "clock_vector": self.clocks,
            "timestamp": self.timestamp
        }


class QuorumCoordinator:
    """
    Enforces Quorum Consensus (N, R, W) and 12-Point Failure Mitigations.
    Ensures R + W > N to prevent stale reads and split-brain states.
    """
    def __init__(self, n: int = 5, r: int = 2, w: int = 2):
        self.N = n  # Total Nodes
        self.R = r  # Read Quorum
        self.W = w  # Write Quorum
        
        if self.R + self.W <= self.N:
            raise ValueError(f"Invalid Quorum config: R({r}) + W({w}) must be > N({n})")

    def check_partition_quorum(self, active_nodes_count: int) -> bool:
        """Rule 3 Mitigation: Partial Network Partition Majority Check."""
        majority_threshold = (self.N // 2) + 1
        return active_nodes_count >= majority_threshold

    def resolve_concurrent_conflict(self, clock_a: VectorClock, clock_b: VectorClock) -> VectorClock:
        """Rule 4 Mitigation: Concurrent Write Conflict Resolution using Vector Clocks."""
        if clock_a.is_newer_than(clock_b):
            return clock_a
        elif clock_b.is_newer_than(clock_a):
            return clock_b
        else:
            # Concurrent tie-break by timestamp
            return clock_a if clock_a.timestamp >= clock_b.timestamp else clock_b

    def validate_quorum_write(self, successful_acks: int, active_nodes: int) -> bool:
        """Rule 2 & Rule 6 Mitigation: Write Quorum Validation."""
        if not self.check_partition_quorum(active_nodes):
            raise RuntimeError("Split-Brain Protection: Minority partition cannot accept writes.")
        return successful_acks >= self.W

    def validate_quorum_read(self, read_responses: List[dict]) -> dict:
        """Rule 5 & Rule 10 Mitigation: Read Quorum Version Consensus."""
        if len(read_responses) < self.R:
            raise RuntimeError(f"Read Quorum Failed: Got {len(read_responses)} ACKs, expected R={self.R}")

        # Pick response with highest Vector Clock
        highest_resp = None
        highest_clock = None

        for resp in read_responses:
            if resp.get("is_corrupted"):
                continue
            clock = resp.get("version")
            if highest_clock is None or (clock and clock.is_newer_than(highest_clock)):
                highest_clock = clock
                highest_resp = resp

        if not highest_resp:
            raise RuntimeError("Read Quorum Failed: All replica responses corrupted.")

        return highest_resp
