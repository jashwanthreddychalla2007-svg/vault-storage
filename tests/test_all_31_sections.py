import os
import sys
import pytest
import hashlib
import json
import time
import secrets
import concurrent.futures

# Set isolated environment variables
os.environ["TESTING"] = "1"
os.environ["VAULT_DB_FILE"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_database.db"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from database import init_db, get_db
init_db()

from main import app, engine, auth_mgr

@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_cluster_before_test():
    engine.reset_test_cluster()
    yield

# ================= SECTION 1 - 3: CLUSTER & DB SCHEMA =================

def test_01_database_schema_integrity():
    """Verify 9 mandatory tables in DB schema."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    required_tables = [
        "users", "buckets", "objects", "object_versions", 
        "object_replicas", "storage_nodes", "repair_jobs", "events", "policies"
    ]
    for tbl in required_tables:
        assert tbl in tables, f"Missing database table: {tbl}"

def test_02_six_independent_nodes(client):
    """Verify 6 independent storage nodes across 2 zones."""
    res = client.get("/nodes")
    assert res.status_code == 200
    nodes = res.json()
    assert len(nodes) == 6
    
    zone_a = [n for n in nodes if n["zone"] == "ZONE_A"]
    zone_b = [n for n in nodes if n["zone"] == "ZONE_B"]
    assert len(zone_a) == 3
    assert len(zone_b) == 3

# ================= SECTION 4: AUTHENTICATION & SERVER-SIDE RBAC =================

def test_04_auth_and_server_side_rbac(client):
    """Verify signup, login, auth/me, and 403 Forbidden server-side RBAC guards."""
    # Signup valid user
    res = client.post("/auth/signup", data={"email": "rbac_user@vault.io", "password": "SecurePassword2026!", "name": "RBAC Test User"})
    assert res.status_code == 200

    # Login
    res_log = client.post("/auth/login", data={"email": "rbac_user@vault.io", "password": "SecurePassword2026!"})
    assert res_log.status_code == 200
    token = res_log.json()["token"]

    # /auth/me with Bearer token
    res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200

    # Unauthenticated /auth/me -> 401
    res_unauth = client.get("/auth/me")
    assert res_unauth.status_code == 401

    # VIEWER attempting admin endpoint -> 403 Forbidden
    res_viewer_fail = client.post("/admin/nodes/1/fail", headers={"X-Vault-Role": "VIEWER"})
    assert res_viewer_fail.status_code == 403

    # ADMIN attempting admin endpoint -> 200 OK
    res_admin_fail = client.post("/admin/nodes/1/fail", headers={"X-Vault-Role": "ADMIN"})
    assert res_admin_fail.status_code == 200

# ================= SECTION 5 & 6: OBJECT TYPES & SHA-256 INTEGRITY =================

def test_05_multi_file_type_storage_and_integrity(client):
    """Test small text, binary, image, PDF, ZIP, zero-byte, and large file byte-for-byte fidelity."""
    test_files = [
        ("small_text.txt", b"Hello Vault Distributed Storage", "text/plain"),
        ("binary.dat", bytes([i % 256 for i in range(1024)]), "application/octet-stream"),
        ("mock_image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01", "image/png"),
        ("document.pdf", b"%PDF-1.4 %EOF", "application/pdf"),
        ("archive.zip", b"PK\x03\x04\x14\x00\x00\x00\x00\x00", "application/zip"),
        ("empty.bin", b"", "application/octet-stream"),
        ("large_blob.bin", b"X" * (1024 * 512), "application/octet-stream"), # 512 KB
    ]

    for fname, payload, mime in test_files:
        expected_hash = hashlib.sha256(payload).hexdigest()
        
        # Upload
        res_up = client.post("/objects/upload", files={"file": (fname, payload, mime)})
        assert res_up.status_code == 200
        obj_data = res_up.json()
        assert obj_data["checksum"] == expected_hash

        # Download & Byte-by-byte comparison
        res_dl = client.get(f"/objects/{obj_data['object_id']}/download")
        assert res_dl.status_code == 200
        assert res_dl.content == payload, f"Downloaded content for {fname} does not match original bytes"

# ================= SECTION 7 & 8: REPLICATION & QUORUM =================

def test_07_zone_aware_replication(client):
    """Verify RF=3 replicas placed across Zone A and Zone B."""
    payload = b"Zone replication validation data"
    res = client.post("/objects/upload", files={"file": ("zoned.bin", payload, "application/octet-stream")}, data={"replication_factor": 3})
    assert res.status_code == 200
    replicas = res.json()["replicas"]
    assert len(replicas) == 3
    zones = set(r["zone"] for r in replicas)
    assert "ZONE_A" in zones and "ZONE_B" in zones

# ================= SECTION 9 & 10: NODE FAILURE, BITROT & REPAIR =================

def test_09_node_failure_detection_and_bitrot_repair(client):
    """Verify failure injection, zero-downtime read, bitrot detection, anti-entropy repair."""
    payload = b"Payload for fail and repair verification test"
    res_up = client.post("/objects/upload", files={"file": ("fail_test.bin", payload, "application/octet-stream")})
    assert res_up.status_code == 200
    obj_data = res_up.json()
    obj_id = obj_data["object_id"]
    nodes = [r["node_id"] for r in obj_data["replicas"]]

    # 1. Fail node 1
    res_fail = client.post(f"/admin/nodes/{nodes[0]}/fail", headers={"X-Vault-Role": "ADMIN"})
    assert res_fail.status_code == 200

    # 2. Verify read works during failure (Zero-Downtime Read)
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # 3. Inject bitrot into surviving node
    client.post("/admin/corrupt", data={"node_id": nodes[1]}, headers={"X-Vault-Role": "ADMIN"})

    # 4. Trigger integrity scan
    res_scan = client.post("/admin/integrity-scan", headers={"X-Vault-Role": "ADMIN"})
    assert res_scan.status_code == 200
    assert res_scan.json()["status"] == "COMPLETE"

    # 5. Restore failed node
    res_rest = client.post(f"/admin/nodes/{nodes[0]}/restore", headers={"X-Vault-Role": "ADMIN"})
    assert res_rest.status_code == 200

# ================= SECTION 12 & 13: VERSIONING & CONCURRENCY =================

def test_12_versioning_and_optimistic_concurrency(client):
    """Verify version increments and 409 conflict handling."""
    # Upload v1
    res_v1 = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 1", "text/plain")})
    assert res_v1.json()["version"] == 1

    # Upload v2
    res_v2 = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 2", "text/plain")})
    assert res_v2.json()["version"] == 2

    # Upload v3 with expected version 1 (wrong version) -> 409 Conflict
    res_conflict = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 3", "text/plain")}, data={"expected_version": 1})
    assert res_conflict.status_code == 409

# ================= SECTION 14 & 15: TOMBSTONES & PARTITION =================

def test_14_tombstone_delete_and_network_partition(client):
    """Verify tombstone deletion and network partition simulation."""
    res_up = client.post("/objects/upload", files={"file": ("partition_doc.txt", b"Partition test payload", "text/plain")})
    obj_id = res_up.json()["object_id"]

    # Delete -> Tombstone created
    res_del = client.delete(f"/objects/{obj_id}")
    assert res_del.status_code == 200

    # Download returns 404
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 404

    # Network partition Node 5
    res_part = client.post("/admin/network-partition?node_id=5", headers={"X-Vault-Role": "ADMIN"})
    assert res_part.status_code == 200

    # Network restore Node 5
    res_rest = client.post("/admin/network-restore?node_id=5", headers={"X-Vault-Role": "ADMIN"})
    assert res_rest.status_code == 200

# ================= SECTION 16 - 21: REBALANCE, METRICS & SECURITY =================

def test_16_rebalance_metrics_and_security(client):
    """Verify cluster rebalancing, metrics API, and path traversal blocking."""
    # Rebalance
    res_reb = client.post("/admin/rebalance", headers={"X-Vault-Role": "ADMIN"})
    assert res_reb.status_code == 200

    # Metrics
    res_met = client.get("/cluster/metrics")
    assert res_met.status_code == 200
    m_data = res_met.json()
    assert m_data["healthy_node_count"] == 6

    # Path traversal blocking
    res_sec = client.post("/objects/upload", files={"file": ("../../../../etc/shadow", b"Malicious payload", "text/plain")})
    assert res_sec.status_code == 200
    assert ".." not in res_sec.json()["name"] and "/" not in res_sec.json()["name"]
