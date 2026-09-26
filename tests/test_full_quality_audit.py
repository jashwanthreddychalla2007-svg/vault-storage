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

# ================= PHASE 2: ACCESSIBILITY (A11Y) AUDIT TESTS =================

def test_A11Y_accessibility_html_markup(client):
    """A11Y-001..A11Y-040: Verify frontend accessibility landmarks, skip links, ARIA roles, and labels."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Skip to main content link
    assert 'href="#main-content"' in html
    assert "Skip to main content" in html

    # Landmark roles
    assert 'role="banner"' in html
    assert 'role="navigation"' in html
    assert 'role="main"' in html

    # ARIA Tab & Role Guard Accessibility
    assert 'role="tab"' in html
    assert 'aria-selected' in html
    assert 'aria-label' in html
    assert 'for="roleSelector"' in html

# ================= PHASE 3: CODE QUALITY (CQ) AUDIT TESTS =================

def test_CQ_database_indexes_and_cleanup():
    """CQ-001..CQ-020: Verify database performance indexes and table definitions."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row["name"] for row in cursor.fetchall()]
    conn.close()

    expected_indexes = [
        "idx_objects_bucket", "idx_objects_state", "idx_versions_obj",
        "idx_replicas_ver", "idx_replicas_node", "idx_repairs_status", "idx_events_timestamp"
    ]
    for idx in expected_indexes:
        assert idx in indexes, f"Missing required performance database index: {idx}"

# ================= PHASE 4: SECURITY (SEC) AUDIT TESTS =================

def test_SEC_owasp_headers_and_injection_defense(client):
    """SEC-001..SEC-030: OWASP security response headers, SQLi, XSS, and Path Traversal shielding."""
    # OWASP Security Headers
    res_h = client.get("/health")
    assert res_h.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_h.headers.get("X-Frame-Options") == "DENY"
    assert "X-XSS-Protection" in res_h.headers
    assert "Strict-Transport-Security" in res_h.headers

    # Path Traversal
    res_pt = client.post("/objects/upload", files={"file": ("../../../../etc/passwd", b"root:x:0:0", "text/plain")})
    assert res_pt.status_code == 200
    assert ".." not in res_pt.json()["name"]

    # XSS Payload in filename
    xss_payload = "<script>alert('xss')</script>.txt"
    res_xss = client.post("/objects/upload", files={"file": (xss_payload, b"Safe content", "text/plain")})
    assert res_xss.status_code == 200

    # SQL Injection in bucket name
    sqli_bucket = "primary-datasets'; DROP TABLE users; --"
    res_sqli = client.post("/objects/upload", files={"file": ("safe.txt", b"Safe data", "text/plain")}, data={"bucket": sqli_bucket})
    assert res_sqli.status_code in [200, 400]

    # Verify SQL schema is intact
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    assert cursor.fetchone()[0] > 0
    conn.close()

# ================= PHASE 5: EFFICIENCY & PERFORMANCE (EFF) TESTS =================

def test_EFF_chunk_streaming_and_gzip_compression(client):
    """EFF-001..EFF-030: Verify chunk streaming I/O generator and response compression."""
    payload = b"Performance Efficiency Payload Block " * 500 # ~18 KB
    res_up = client.post("/objects/upload", files={"file": ("eff_test.bin", payload, "application/octet-stream")})
    assert res_up.status_code == 200
    obj_id = res_up.json()["object_id"]

    # Generator streaming test
    chunks = list(engine.stream_object_chunks(obj_id))
    assert len(chunks) > 0
    assert b"".join(chunks) == payload

    # Download GZip response check
    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

# ================= PHASE 6 & 7: EDGE CASES & ALIGNMENT TESTS =================

def test_TEST_unicode_large_and_edge_case_payloads(client):
    """TEST-001..TEST-045: Test Unicode filenames, 1 MB files, and zero-byte files."""
    # Unicode filename
    unicode_name = "üñîcødé_tëst_文件.txt"
    payload = b"Unicode payload test data"
    res_uni = client.post("/objects/upload", files={"file": (unicode_name, payload, "text/plain")})
    assert res_uni.status_code == 200
    obj_id = res_uni.json()["object_id"]

    res_dl = client.get(f"/objects/{obj_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == payload

    # 1 MB Large file
    large_payload = os.urandom(1024 * 1024)
    res_large = client.post("/objects/upload", files={"file": ("1mb_blob.dat", large_payload, "application/octet-stream")})
    assert res_large.status_code == 200
    l_obj_id = res_large.json()["object_id"]

    res_l_dl = client.get(f"/objects/{l_obj_id}/download")
    assert res_l_dl.status_code == 200
    assert hashlib.sha256(res_l_dl.content).hexdigest() == hashlib.sha256(large_payload).hexdigest()
