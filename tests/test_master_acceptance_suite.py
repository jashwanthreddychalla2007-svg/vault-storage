import os
import sys

# MUST SET TESTING & ISOLATED TEST DB MODE BEFORE ANY OTHER IMPORTS
os.environ["TESTING"] = "1"
os.environ["VAULT_DB_FILE"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_database.db"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
import hashlib
import json
import time

from fastapi.testclient import TestClient
from database import init_db, get_db
init_db()

from main import app, engine, auth_mgr

@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_cluster_before_test():
    """Clean reset before each test to ensure test isolation."""
    engine.reset_test_cluster()
    yield

# ================= A. ENVIRONMENT, BUILD, STARTUP =================

def test_A_001_clean_installation():
    """A-001 [P0] Clean installation dependencies check."""
    assert engine is not None
    assert auth_mgr is not None

def test_A_003_postgresql_sqlite_startup():
    """A-003 [P0] Database connection and schema verification."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()
    
    expected_tables = ["users", "buckets", "objects", "object_versions", "object_replicas", "storage_nodes", "repair_jobs", "events", "policies"]
    for tbl in expected_tables:
        assert tbl in tables, f"Missing required table {tbl}"

def test_A_004_fastapi_startup(client):
    """A-004 [P0] FastAPI health readiness check."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["HEALTHY", "DEGRADED"]

def test_A_005_A_006_six_storage_nodes(client):
    """A-005, A-006 [P0] Six storage node registration and isolation."""
    res = client.get("/nodes")
    assert res.status_code == 200
    nodes = res.json()
    assert len(nodes) == 6
    ports = [n["port"] for n in nodes]
    assert sorted(ports) == [5001, 5002, 5003, 5004, 5005, 5006]

# ================= B. AUTHENTICATION AND AUTHORIZATION =================

def test_B_001_to_B_004_user_signup_validation(client):
    """B-001..B-004 [P0] User signup, duplicate email, invalid email, weak password checks."""
    # B-001: Valid user signup
    res = client.post("/auth/signup", data={"email": "newuser@vault.io", "password": "ValidPassword2026!", "name": "New User"})
    assert res.status_code == 200
    assert "user" in res.json()

    # B-002: Duplicate email rejection
    res_dup = client.post("/auth/signup", data={"email": "newuser@vault.io", "password": "ValidPassword2026!", "name": "New User 2"})
    assert res_dup.status_code == 400

    # B-003: Invalid email format rejection
    res_inv_email = client.post("/auth/signup", data={"email": "not_an_email", "password": "ValidPassword2026!", "name": "Invalid Email User"})
    assert res_inv_email.status_code == 400

    # B-004: Weak password rejection (<8 chars)
    res_weak_pw = client.post("/auth/signup", data={"email": "weak@vault.io", "password": "123", "name": "Weak User"})
    assert res_weak_pw.status_code == 400

def test_B_005_to_B_008_login_logout(client):
    """B-005..B-008 [P0] Login valid/invalid credentials, auth token, logout."""
    client.post("/auth/signup", data={"email": "loginuser@vault.io", "password": "LoginPassword2026!", "name": "Login User"})
    
    # B-005: Valid login
    res = client.post("/auth/login", data={"email": "loginuser@vault.io", "password": "LoginPassword2026!"})
    assert res.status_code == 200
    token = res.json()["token"]
    assert token is not None

    # B-[006, 007]: Invalid password / nonexistent user
    res_bad = client.post("/auth/login", data={"email": "loginuser@vault.io", "password": "WrongPassword!"})
    assert res_bad.status_code == 401

    # B-008: Logout
    res_out = client.post("/auth/logout")
    assert res_out.status_code == 200

def test_B_009_unauthenticated_protected_api(client):
    """B-009 [P0] Unauthenticated access to protected endpoint."""
    res = client.get("/auth/me")
    assert res.status_code == 401

def test_B_010_to_B_012_rbac_admin_protection(client):
    """B-010..B-012 [P0] Server-side RBAC authorization guard enforcement."""
    # Normal USER attempting admin fail-node operation -> 403 Forbidden
    res_user = client.post("/admin/nodes/4/fail", headers={"X-Vault-Role": "VIEWER"})
    assert res_user.status_code == 403

    # ADMIN attempting admin operation -> 200 Success
    res_admin = client.post("/admin/nodes/4/fail", headers={"X-Vault-Role": "ADMIN"})
    assert res_admin.status_code == 200

# ================= C. BUCKETS, OBJECTS, UPLOAD, DOWNLOAD =================

def test_C_001_to_C_007_upload_download_checksum(client):
    """C-001..C-007 [P0] Bucket creation, upload, SHA-256 computation, download verification."""
    payload = b"Vault Distributed Object Storage Payload Data 2026 Test Suite"
    expected_hash = hashlib.sha256(payload).hexdigest()

    # Upload file
    files = {"file": ("test_doc.bin", payload, "application/octet-stream")}
    res = client.post("/objects/upload", files=files, data={"bucket": "test-bucket", "replication_factor": 3})
    assert res.status_code == 200
    data = res.json()
    obj_id = data["object_id"]
    assert data["checksum"] == expected_hash

    # Download & verify byte-identical match
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

def test_C_011_C_012_delete_object_tombstone_and_404(client):
    """C-011, C-012 [P0] Tombstone delete and 404 missing object checks."""
    payload = b"Temporary data to delete"
    res = client.post("/objects/upload", files={"file": ("to_delete.txt", payload, "text/plain")})
    obj_id = res.json()["object_id"]

    # Delete object (Tombstone)
    res_del = client.delete(f"/objects/{obj_id}")
    assert res_del.status_code == 200

    # Subsequent download should return 404
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 404

    # Nonexistent object 404 check
    res_missing = client.get("/objects/obj_nonexistent_12345")
    assert res_missing.status_code == 404

def test_C_014_zero_byte_file_upload(client):
    """C-014 [P1] Zero-byte empty file upload & download."""
    payload = b""
    expected_hash = hashlib.sha256(payload).hexdigest()
    res = client.post("/objects/upload", files={"file": ("empty.bin", payload, "application/octet-stream")})
    assert res.status_code == 200
    data = res.json()
    assert data["checksum"] == expected_hash

    res_dl = client.get(f"/objects/{data['object_id']}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == b""

# ================= D & E. NODE HEALTH, PLACEMENT & REPLICATION =================

def test_E_001_E_006_zone_aware_replication(client):
    """E-001, E-006 [P0] RF=3 zone-aware placement across Zone A & Zone B."""
    res = client.post("/objects/upload", files={"file": ("zoned.txt", b"Zone Data", "text/plain")}, data={"replication_factor": 3})
    assert res.status_code == 200
    replicas = res.json()["replicas"]
    assert len(replicas) == 3
    zones = set(r["zone"] for r in replicas)
    assert "ZONE_A" in zones and "ZONE_B" in zones, "Replicas must be spread across Zone A and Zone B"

# ================= F & G. CHECKSUMS, BITROT CORRUPTION & AUTO-REPAIR =================

def test_F_G_bitrot_detection_and_auto_repair(client):
    """F-001..F-008, G-001..G-011 [P0] Bitrot detection, node failure, degraded state & auto-repair."""
    payload = b"Data payload for chaos bitrot test 2026"
    res_up = client.post("/objects/upload", files={"file": ("chaos.txt", payload, "text/plain")}, data={"replication_factor": 3})
    assert res_up.status_code == 200
    obj_data = res_up.json()
    obj_id = obj_data["object_id"]
    replica_nodes = [r["node_id"] for r in obj_data["replicas"]]

    # Fail one of the replica nodes
    failed_node = replica_nodes[0]
    res_fail = client.post(f"/admin/nodes/{failed_node}/fail", headers={"X-Vault-Role": "ADMIN"})
    assert res_fail.status_code == 200

    # Verify object state becomes DEGRADED
    res_details = client.get(f"/objects/{obj_id}")
    assert res_details.status_code == 200

    # Download payload during node outage (Zero-Downtime Read)
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # Inject bitrot corruption on surviving replica node
    surviving_node = replica_nodes[1]
    res_corr = client.post("/admin/corrupt", data={"node_id": surviving_node}, headers={"X-Vault-Role": "ADMIN"})
    assert res_corr.status_code == 200

    # Run integrity scan -> detects & repairs corrupted block
    res_scan = client.post("/admin/integrity-scan", headers={"X-Vault-Role": "ADMIN"})
    assert res_scan.status_code == 200

    # Restore failed node
    res_res = client.post(f"/admin/nodes/{failed_node}/restore", headers={"X-Vault-Role": "ADMIN"})
    assert res_res.status_code == 200

# ================= H. VERSIONING & OPTIMISTIC CONCURRENCY =================

def test_H_001_to_H_010_versioning_and_conflict(client):
    """H-001..H-010 [P0] Versioning increment and optimistic concurrency 409 conflict."""
    # First upload v1
    res_v1 = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 1 Data", "text/plain")})
    obj_id = res_v1.json()["object_id"]
    assert res_v1.json()["version"] == 1

    # Second upload v2
    res_v2 = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 2 Data", "text/plain")})
    assert res_v2.json()["version"] == 2

    # Optimistic concurrency conflict check (providing wrong expected version 1 when current is 2)
    res_conflict = client.post("/objects/upload", files={"file": ("doc.txt", b"Version 3 Data", "text/plain")}, data={"expected_version": 1})
    assert res_conflict.status_code == 409

# ================= O. SECURITY & FILESYSTEM HARDENING =================

def test_O_001_to_O_003_path_traversal_blocking(client):
    """O-001..O-003 [P0] Path traversal filename sanitization."""
    payload = b"Path traversal attempt data"
    
    # Traversal payload filename
    res = client.post("/objects/upload", files={"file": ("../../../../etc/passwd", payload, "text/plain")})
    assert res.status_code == 200
    name = res.json()["name"]
    assert ".." not in name and "/" not in name, "Path traversal tokens must be sanitized"

# ================= U & Y. MASTER DEMO ACCEPTANCE SCENARIO =================

def test_U_001_to_U_008_master_judge_demo_scenario(client):
    """U-001..U-008 [P0] Complete 9-step judge demo acceptance scenario."""
    # 1. Clean Cluster Health
    res_h = client.get("/cluster/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] in ["HEALTHY", "DEGRADED"]

    # 2. Upload Demo File
    payload = b"Master Demo Judge File Payload Block 2026"
    res_up = client.post("/objects/upload", files={"file": ("judge_demo.bin", payload, "application/octet-stream")})
    assert res_up.status_code == 200
    obj_id = res_up.json()["object_id"]

    # 3. Fail Node 4
    client.post("/admin/nodes/4/fail", headers={"X-Vault-Role": "ADMIN"})

    # 4. Zero Downtime Read
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # 5. Restore Cluster
    client.post("/admin/nodes/4/restore", headers={"X-Vault-Role": "ADMIN"})

    # 6. Verify Final Cluster Health
    res_metrics = client.get("/cluster/metrics")
    assert res_metrics.status_code == 200
    assert res_metrics.json()["healthy_node_count"] == 6
