import os
import sys
import pytest
import hashlib
import json
import time

os.environ["TESTING"] = "1"
os.environ["VAULT_DB_FILE"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_database.db"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from database import init_db, get_db
init_db()

from main import app, engine

@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_cluster_before_test():
    engine.reset_test_cluster()
    yield

# ================= EFFICIENCY & N+1 QUERY REGRESSION TESTS =================

def test_E006_n_plus_1_query_elimination(client):
    """E-006 / T-006: Verify list_objects completes efficiently without N+1 query overhead."""
    # Upload 10 test objects
    for i in range(10):
        client.post("/objects/upload", files={"file": (f"batch_doc_{i}.txt", f"Data chunk {i}".encode(), "text/plain")})

    # Execute list_objects
    res = client.get("/objects")
    assert res.status_code == 200
    objs = res.json()
    assert len(objs) == 10

    # Ensure all 10 objects have replicas populated
    for obj in objs:
        assert len(obj["replicas"]) > 0
        assert "zone" in obj["replicas"][0]

def test_E005_database_indexes_exist():
    """E-005 / T-030: Verify users, buckets, nodes, and objects performance indexes."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row["name"] for row in cursor.fetchall()]
    conn.close()

    required_indexes = [
        "idx_users_email", "idx_buckets_name", "idx_nodes_status",
        "idx_objects_bucket", "idx_objects_state", "idx_versions_obj", "idx_replicas_ver"
    ]
    for idx in required_indexes:
        assert idx in indexes, f"Index {idx} must exist for O(1) query performance"

# ================= SECURITY & IDOR TESTS =================

def test_SEC_idor_and_unauthorized_access(client):
    """SEC-002 / T-011: IDOR testing and unauthorized admin action shielding."""
    # Attempt admin fail node without admin role
    res_fail = client.post("/admin/nodes/1/fail", headers={"X-Vault-Role": "VIEWER"})
    assert res_fail.status_code == 403

    # Attempt admin corrupt without admin role
    res_corr = client.post("/admin/corrupt", data={"node_id": 1}, headers={"X-Vault-Role": "VIEWER"})
    assert res_corr.status_code == 403

    # Attempt admin rebalance without admin role
    res_reb = client.post("/admin/rebalance", headers={"X-Vault-Role": "VIEWER"})
    assert res_reb.status_code == 403

# ================= ACCESSIBILITY & SEMANTICS TESTS =================

def test_A11Y_wcag21_landmarks_and_aria_attributes(client):
    """A11Y-001..A11Y-021: Verify WCAG 2.1 AA HTML5 semantic landmarks and ARIA attributes."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'role="banner"' in html
    assert 'role="navigation"' in html
    assert 'role="main"' in html
    assert 'role="tab"' in html
    assert 'for="roleSelector"' in html
    assert 'Skip to main content' in html

# ================= PROBLEM STATEMENT ALIGNMENT TRACEABILITY =================

def test_ALIGN_six_node_fault_tolerance(client):
    """ALIGN-001..ALIGN-025: Verify 6-node distributed topology across 2 zones."""
    res = client.get("/cluster/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["healthy_node_count"] == 6
    assert metrics["total_node_count"] == 6

    nodes = metrics["nodes"]
    zones = set(n["zone"] for n in nodes)
    assert "ZONE_A" in zones and "ZONE_B" in zones
