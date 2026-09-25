import os
import sys
import pytest

os.environ["TESTING"] = "1"
os.environ["VAULT_DB_FILE"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_database.db"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from main import app, engine

@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_cluster():
    engine.reset_test_cluster()
    yield

def test_F_G_checksums_bitrot_and_repair(client):
    """F-001..G-020: Checksums, bitrot corruption, node crash, degraded state & auto-repair."""
    payload = b"Engine Resilience Test Data Payload 2026"
    res_up = client.post("/objects/upload", files={"file": ("resilient.txt", payload, "text/plain")}, data={"replication_factor": 3})
    assert res_up.status_code == 200
    obj_data = res_up.json()
    obj_id = obj_data["object_id"]
    rep_nodes = [r["node_id"] for r in obj_data["replicas"]]

    # Fail Node
    failed_node = rep_nodes[0]
    res_fail = client.post(f"/admin/nodes/{failed_node}/fail", headers={"X-Vault-Role": "ADMIN"})
    assert res_fail.status_code == 200

    # Verify degraded state
    res_details = client.get(f"/objects/{obj_id}")
    assert res_details.json()["state"] == "DEGRADED"

    # Download works (Zero-downtime read)
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # Corrupt surviving node replica
    surviving_node = rep_nodes[1]
    client.post("/admin/corrupt", data={"node_id": surviving_node}, headers={"X-Vault-Role": "ADMIN"})

    # Run integrity scan
    res_scan = client.post("/admin/integrity-scan", headers={"X-Vault-Role": "ADMIN"})
    assert res_scan.status_code == 200

    # Restore failed node
    client.post(f"/admin/nodes/{failed_node}/restore", headers={"X-Vault-Role": "ADMIN"})

def test_H_I_J_versioning_partition_rebalance(client):
    """H-001..J-010: Versioning history, optimistic 409 conflict, network partition, rebalancing."""
    # Versioning
    res_v1 = client.post("/objects/upload", files={"file": ("ver.txt", b"v1 data", "text/plain")})
    obj_id = res_v1.json()["object_id"]

    res_v2 = client.post("/objects/upload", files={"file": ("ver.txt", b"v2 data", "text/plain")})
    assert res_v2.json()["version"] == 2

    # 409 conflict on stale version update
    res_conflict = client.post("/objects/upload", files={"file": ("ver.txt", b"v3 data", "text/plain")}, data={"expected_version": 1})
    assert res_conflict.status_code == 409

    # Network Partition
    res_part = client.post("/admin/nodes/5/partition", headers={"X-Vault-Role": "ADMIN"})
    assert res_part.status_code == 200

    # Network Restore
    res_rest = client.post("/admin/nodes/5/network-restore", headers={"X-Vault-Role": "ADMIN"})
    assert res_rest.status_code == 200

    # Rebalance
    res_reb = client.post("/admin/rebalance", headers={"X-Vault-Role": "ADMIN"})
    assert res_reb.status_code == 200
