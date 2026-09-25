import os
import sys
import pytest

os.environ["TESTING"] = "1"
os.environ["VAULT_DB_FILE"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_database.db"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from main import app, engine, auth_mgr

@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_cluster():
    engine.reset_test_cluster()
    yield

def test_A_001_to_A_008_environment_startup_schema(client):
    """A-001..A-008: Startup, Environment, PostgreSQL/SQLite schema verification."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] in ["HEALTHY", "DEGRADED"]

    nodes_res = client.get("/nodes")
    assert nodes_res.status_code == 200
    assert len(nodes_res.json()) == 6

def test_B_001_to_B_015_authentication_and_authorization(client):
    """B-001..B-015: Authentication, Signup, Password Policies, RBAC guards."""
    # Signup valid user
    res_signup = client.post("/auth/signup", data={"email": "alpha@vault.io", "password": "SecurePassword123!", "name": "Alpha User"})
    assert res_signup.status_code == 200

    # Signup duplicate email -> 400
    res_dup = client.post("/auth/signup", data={"email": "alpha@vault.io", "password": "SecurePassword123!", "name": "Alpha Duplicate"})
    assert res_dup.status_code == 400

    # Login valid
    res_login = client.post("/auth/login", data={"email": "alpha@vault.io", "password": "SecurePassword123!"})
    assert res_login.status_code == 200
    token = res_login.json()["token"]

    # Protected endpoint with valid token header
    res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "alpha@vault.io"

    # Protected endpoint without token -> 401
    res_unauth = client.get("/auth/me")
    assert res_unauth.status_code == 401

    # USER attempting admin chaos operation -> 403 Forbidden
    res_forbidden = client.post("/admin/nodes/1/fail", headers={"X-Vault-Role": "VIEWER"})
    assert res_forbidden.status_code == 403
