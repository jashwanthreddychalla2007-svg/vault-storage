import time
import random
from typing import Dict, Any, List

class RaftConsensusEngine:
    """Simulates Raft Consensus State Machine for Vault cluster metadata authority."""

    def __init__(self, node_ids: List[int]):
        self.node_ids = node_ids
        self.current_term = 1
        self.leader_id = node_ids[0] if node_ids else 1
        self.commit_index = 104
        self.last_log_index = 104
        self.last_heartbeat = time.time()
        self.log_entries = [
            {"index": 101, "term": 1, "cmd": "CREATE_BUCKET:primary-datasets"},
            {"index": 102, "term": 1, "cmd": "UPLOAD_OBJECT:system_firmware.bin"},
            {"index": 103, "term": 1, "cmd": "UPLOAD_OBJECT:dataset_sample.parquet"},
            {"index": 104, "term": 1, "cmd": "UPDATE_REPLICA_MAP:node_3_healthy"}
        ]

    def trigger_election(self) -> Dict[str, Any]:
        """Triggers a simulated Raft leader election."""
        self.current_term += 1
        self.leader_id = random.choice(self.node_ids)
        self.last_heartbeat = time.time()
        
        election_log = f"Raft Term {self.current_term}: Leader election won by Node-{self.leader_id} (Votes: 4/5)"
        self.log_entries.append({
            "index": len(self.log_entries) + 101,
            "term": self.current_term,
            "cmd": f"ELECTION_TERM_{self.current_term}_LEADER_NODE_{self.leader_id}"
        })
        self.commit_index += 1
        self.last_log_index += 1

        return {
            "term": self.current_term,
            "leader_id": self.leader_id,
            "commit_index": self.commit_index,
            "last_log_index": self.last_log_index,
            "event": election_log
        }

    def get_raft_state(self) -> Dict[str, Any]:
        return {
            "current_term": self.current_term,
            "leader_id": self.leader_id,
            "commit_index": self.commit_index,
            "last_log_index": self.last_log_index,
            "last_heartbeat": self.last_heartbeat,
            "consensus_status": "CONVERGED_QUORUM_OK",
            "log_entries": self.log_entries[-10:]
        }
