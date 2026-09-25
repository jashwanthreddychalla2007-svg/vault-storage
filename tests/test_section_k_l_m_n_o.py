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

def test_K_L_M_events_metrics_api_contracts(client):
    """K-001..M-026: Events logging, telemetry metrics, API contract verification."""
    # Events listing
    res_ev = client.get("/events")
    assert res_ev.status_code == 200

    # Cluster metrics
    res_met = client.get("/cluster/metrics")
    assert res_met.status_code == 200
    assert "healthy_node_count" in res_met.json()
    assert "logical_storage_bytes" in res_met.json()

    # Repairs listing
    res_rep = client.get("/repairs")
    assert res_rep.status_code == 200

    # Node detail 404 on invalid node
    res_node_404 = client.get("/nodes/999")
    assert res_node_404.status_code == 404

def test_N_O_error_handling_security_path_traversal(client):
    """N-001..O-012: Error handling contracts, security hardening & path traversal blocking."""
    # 404 Missing Object
    res_404 = client.get("/objects/obj_missing_99999")
    assert res_404.status_code == 404

    # Path traversal attack filename: ../../../../etc/passwd
    payload = b"root:x:0:0:root:/root:/bin/bash"
    res_trav = client.post("/objects/upload", files={"file": ("../../../../etc/passwd", payload, "text/plain")})
    assert res_trav.status_code == 200
    name = res_trav.json()["name"]
    assert ".." not in name and "/" not in name, "Path traversal tokens must be stripped"

    # Traversal in download object id -> 404 safe handling
    res_id_trav = client.get("/objects/../../../../etc/passwd/download")
    assert res_id_trav.status_code in [404, 422]
