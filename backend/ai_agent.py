import random
import time
from typing import Dict
from cluster import VaultCluster

class PredictiveNodeAIAgent:
    """
    AI Predictive Node Failure & Health Anomaly Detection Agent.
    Monitors node latency, S.M.A.R.T. disk telemetry, and read retries.
    Predicts hardware failure BEFORE it occurs and proactively evacuates chunks.
    """
    def __init__(self, cluster: VaultCluster):
        self.cluster = cluster
        self.node_health_scores: Dict[int, float] = {i: 100.0 for i in range(1, 6)}  # 0 to 100 health
        self.proactive_evacuations = 0

    def evaluate_node_telemetry(self) -> dict:
        """Evaluates telemetry metrics for all nodes and returns predictive risk scores."""
        risk_reports = []

        for node_id, node in self.cluster.nodes.items():
            if node.status != "ONLINE":
                continue

            # Simulate S.M.A.R.T telemetry metrics
            latency_ms = random.uniform(1.2, 45.0)
            read_retries = random.randint(0, 5)
            disk_temp_c = random.uniform(35.0, 72.0)

            # Anomaly Score Calculation
            anomaly_score = (latency_ms / 50.0) * 40.0 + (read_retries / 5.0) * 30.0 + (disk_temp_c / 75.0) * 30.0
            health_score = max(0.0, 100.0 - anomaly_score)
            self.node_health_scores[node_id] = round(health_score, 1)

            # Proactive Evacuation Condition (Health drops below 40%)
            if health_score < 40.0:
                self.cluster.log_event(
                    "AI_PREDICT",
                    f"🤖 AI AGENT WARNING: Node {node_id} Health at {health_score:.1f}% (Temp: {disk_temp_c:.1f}°C, Retries: {read_retries}). Proactively evacuating chunks!"
                )
                self.proactively_evacuate_node(node_id)

            risk_reports.append({
                "node_id": node_id,
                "name": node.name,
                "health_score": round(health_score, 1),
                "latency_ms": round(latency_ms, 2),
                "disk_temp_c": round(disk_temp_c, 1),
                "status": "AT_RISK" if health_score < 50.0 else "HEALTHY"
            })

        return {"ai_agent_status": "ACTIVE", "nodes": risk_reports}

    def proactively_evacuate_node(self, node_id: int):
        """Proactively relocates chunks off an at-risk node before it crashes."""
        source_node = self.cluster.nodes.get(node_id)
        if not source_node or not source_node.chunks:
            return

        healthy_nodes = [n for n in self.cluster.nodes.values() if n.node_id != node_id and n.status == "ONLINE"]
        if not healthy_nodes:
            return

        chunks_evacuated = 0
        for obj_id, obj in list(self.cluster.objects.items()):
            for meta in obj["chunks"]:
                if meta["node_id"] == node_id:
                    target = random.choice(healthy_nodes)
                    meta["node_id"] = target.node_id
                    target.chunks[meta["chunk_id"]] = source_node.chunks[meta["chunk_id"]]
                    target.chunk_hashes[meta["chunk_id"]] = source_node.chunk_hashes[meta["chunk_id"]]
                    chunks_evacuated += 1

        self.proactive_evacuations += chunks_evacuated
        self.cluster.log_event(
            "AI_EVACUATE",
            f"⚡ AI PROACTIVE EVACUATION COMPLETE: Moved {chunks_evacuated} chunks from Node {node_id} -> Healthy Cluster Nodes."
        )
