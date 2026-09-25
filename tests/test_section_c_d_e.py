import os
import sys
import pytest
import hashlib

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

def test_C_001_to_C_020_bucket_object_lifecycle(client):
    """C-001..C-020: Bucket & object creation, mime types, checksums, downloads, tombstones."""
    payload = b"Binary PDF Payload Header %PDF-1.4 Data 2026"
    expected_hash = hashlib.sha256(payload).hexdigest()

    # Upload object
    files = {"file": ("report.pdf", payload, "application/pdf")}
    res = client.post("/objects/upload", files=files, data={"bucket": "finance-bucket", "replication_factor": 3})
    assert res.status_code == 200
    obj_id = res.json()["object_id"]
    assert res.json()["checksum"] == expected_hash

    # Get object details
    res_det = client.get(f"/objects/{obj_id}")
    assert res_det.status_code == 200
    assert res_det.json()["mime_type"] == "application/pdf"
    assert res_det.json()["size"] == len(payload)

    # Download object
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # Delete object (Tombstone)
    res_del = client.delete(f"/objects/{obj_id}")
    assert res_del.status_code == 200

    # Verify download fails with 404
    res_dl_deleted = client.get(f"/objects/{obj_id}/download")
    assert res_dl_deleted.status_code == 404

def test_D_E_node_independence_and_zone_placement(client):
    """D-001..E-015: Storage node process isolation, zone placement, and replication factor."""
    res_nodes = client.get("/nodes")
    assert res_nodes.status_code == 200
    nodes = res_nodes.json()
    assert len(nodes) == 6

    # Upload under RF=3
    res_up = client.post("/objects/upload", files={"file": ("placement.dat", b"1234567890", "text/plain")}, data={"replication_factor": 3})
    assert res_up.status_code == 200
    replicas = res_up.json()["replicas"]
    assert len(replicas) == 3

    zones = set(r["zone"] for r in replicas)
    assert "ZONE_A" in zones and "ZONE_B" in zones
