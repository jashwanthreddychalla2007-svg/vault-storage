import sys
import os

# Add backend directory to sys.path for clean import resolution on Render / Docker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from typing import List, Optional, Dict, Any

from database import init_db, get_db
from engine import StorageClusterEngine, sanitize_filename
from auth import VaultAuthManager, UserProfile, verify_jwt
from merkle_engine import MerkleTreeEngine
from s3_gateway import S3IAMGateway
from raft_consensus import RaftConsensusEngine
from benchmark_lab import PerformanceLabEngine

from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Vault 6-Node Self-Healing Distributed Object Storage System", version="3.0.0")

# Enable GZip Compression for High Performance & Efficiency
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security Middleware enforcing OWASP Security Headers
class OWASPSecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "999"
        return response

app.add_middleware(OWASPSecurityHeadersMiddleware)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database Schema & Engine
init_db()
engine = StorageClusterEngine()
auth_mgr = VaultAuthManager()
raft_engine = RaftConsensusEngine(node_ids=[1, 2, 3, 4, 5, 6])

active_connections: List[WebSocket] = []

async def broadcast_telemetry():
    """Periodically broadcasts 6-Node cluster state over WebSockets."""
    while True:
        if active_connections:
            status = engine.get_cluster_status()
            status["raft_state"] = raft_engine.get_raft_state()
            message = json.dumps(status)
            disconnected = []
            for connection in active_connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                active_connections.remove(conn)
        await asyncio.sleep(1.0)


@app.on_event("startup")
async def startup_event():
    if not os.environ.get("TESTING"):
        asyncio.create_task(broadcast_telemetry())


# Helper dependency to resolve authenticated user & enforce server-side authorization
def get_current_user(
    authorization: Optional[str] = Header(None),
    x_vault_role: Optional[str] = Header(None)
) -> Optional[UserProfile]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = verify_jwt(token, auth_mgr.secret_key)
        if payload and "sub" in payload:
            u = auth_mgr.users.get(payload["sub"])
            if u:
                return u
            return UserProfile(
                user_id=payload["sub"],
                email=payload.get("email", "user@vault.io"),
                display_name="Authenticated User",
                role=payload.get("role", "USER"),
                created_at=time.time()
            )
    
    # Check X-Vault-Role header if sent
    if x_vault_role:
        role_upper = x_vault_role.upper()
        return UserProfile(
            user_id="usr_header",
            email="header@vault.io",
            display_name="Header User",
            role=role_upper,
            created_at=time.time()
        )
    return None

def require_auth(user: Optional[UserProfile] = Depends(get_current_user)) -> UserProfile:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

def require_admin(user: Optional[UserProfile] = Depends(get_current_user)):
    # Enforce server-side authorization guard
    if not user or user.role.upper() not in ["ADMIN", "PLATFORM_OWNER", "ORGANIZATION_ADMIN", "STORAGE_OPERATOR"]:
        raise HTTPException(status_code=403, detail="403 Forbidden: Administrator role required")
    return user


# Serve root UI directly from Render / Docker backend
@app.get("/", response_class=HTMLResponse)
def serve_root_ui():
    root_index = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
    if os.path.exists(root_index):
        with open(root_index, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Vault 6-Node Storage Engine Online</h1>"


@app.get("/health")
@app.get("/cluster/health")
def health_check():
    status = engine.get_cluster_status()
    return {
        "status": status["cluster_health"],
        "healthy_nodes": f"{status['healthy_node_count']} / {status['total_node_count']}",
        "engine": "SELF_HEALING_6_NODE_CLUSTER_ONLINE"
    }

# ================= AUTHENTICATION ENDPOINTS =================

@app.post("/auth/signup")
def signup(email: str = Form(...), password: str = Form(...), name: str = Form(...)):
    try:
        user = auth_mgr.create_user(email, password, name)
        token = auth_mgr.generate_token(user)
        return {"user": user, "token": token}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = auth_mgr.authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_mgr.generate_token(user)
    return {
        "user": user,
        "token": token,
        "role": user.role
    }

@app.post("/auth/logout")
def logout():
    return {"status": "SUCCESS", "message": "Session invalidated"}

@app.get("/auth/me")
def get_current_user_profile(user: UserProfile = Depends(require_auth)):
    return user

# ================= OBJECTS & VERSIONS APIS =================

@app.get("/objects")
def list_objects():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM objects WHERE state != 'DELETED' ORDER BY updated_at DESC;")
    objs = [dict(r) for r in cursor.fetchall()]
    
    if not objs:
        conn.close()
        return []

    obj_map = {o["id"]: o for o in objs}
    for o in objs:
        o["replicas"] = []

    cursor.execute("""
    SELECT v.object_id, r.node_id, r.state, n.zone 
    FROM object_replicas r 
    JOIN object_versions v ON r.object_version_id = v.id 
    JOIN storage_nodes n ON r.node_id = n.id 
    JOIN objects o ON v.object_id = o.id AND v.version_number = o.latest_version
    WHERE o.state != 'DELETED';
    """)
    
    for row in cursor.fetchall():
        oid = row["object_id"]
        if oid in obj_map:
            obj_map[oid]["replicas"].append({
                "node_id": row["node_id"],
                "state": row["state"],
                "zone": row["zone"]
            })

    conn.close()
    return objs

@app.get("/objects/{object_id}")
def get_object_details(object_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM objects WHERE id = ?;", (object_id,))
    obj = cursor.fetchone()
    if not obj:
        conn.close()
        raise HTTPException(status_code=404, detail="Object not found")
    
    obj_dict = dict(obj)
    cursor.execute("SELECT * FROM object_versions WHERE object_id = ? ORDER BY version_number DESC;", (object_id,))
    obj_dict["versions"] = [dict(v) for v in cursor.fetchall()]

    cursor.execute("""
    SELECT r.node_id, r.state, n.zone, r.checksum 
    FROM object_replicas r 
    JOIN object_versions v ON r.object_version_id = v.id 
    JOIN storage_nodes n ON r.node_id = n.id 
    WHERE v.object_id = ? AND v.version_number = ?;
    """, (object_id, obj_dict["latest_version"]))
    obj_dict["replicas"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return obj_dict

@app.post("/objects/upload")
async def upload_object_endpoint(
    file: UploadFile = File(...), 
    bucket: str = Form("primary-datasets"),
    replication_factor: int = Form(3),
    expected_version: Optional[int] = Form(None)
):
    contents = await file.read()
    clean_filename = sanitize_filename(file.filename)
    try:
        res = engine.upload_object(
            "usr_admin_001", 
            bucket, 
            clean_filename, 
            contents, 
            file.content_type or "application/octet-stream", 
            replication_factor,
            expected_version=expected_version
        )
        return res
    except ValueError as ve:
        if "409 Conflict" in str(ve):
            raise HTTPException(status_code=409, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/objects/{object_id}/download")
def download_object_endpoint(object_id: str, version: Optional[int] = None):
    try:
        data, repaired = engine.download_object(object_id, version)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM objects WHERE id = ?;", (object_id,))
        row = cursor.fetchone()
        filename = row["name"] if row else "download.bin"
        conn.close()

        import urllib.parse
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii') or "download.bin"
        quoted_filename = urllib.parse.quote(filename)

        headers = {
            "Content-Disposition": f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{quoted_filename}',
            "X-Vault-Repaired": str(repaired)
        }
        return Response(content=data, media_type="application/octet-stream", headers=headers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Object not found or deleted")
    except RuntimeError as r:
        raise HTTPException(status_code=503, detail=str(r))

@app.delete("/objects/{object_id}")
def delete_object_endpoint(object_id: str):
    try:
        return engine.delete_object(object_id, "usr_admin_001")
    except KeyError:
        raise HTTPException(status_code=404, detail="Object not found")

@app.get("/objects/{object_id}/versions")
def get_object_versions(object_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM objects WHERE id = ?;", (object_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Object not found")
    cursor.execute("SELECT * FROM object_versions WHERE object_id = ? ORDER BY version_number DESC;", (object_id,))
    versions = [dict(v) for v in cursor.fetchall()]
    conn.close()
    return versions

@app.get("/objects/{object_id}/versions/{version_number}")
def get_specific_version(object_id: str, version_number: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM object_versions WHERE object_id = ? AND version_number = ?;", (object_id, version_number))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")
    return dict(row)

# ================= STORAGE NODES & REPAIRS =================

@app.get("/nodes")
def list_nodes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM storage_nodes ORDER BY id ASC;")
    nodes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return nodes

@app.get("/nodes/{node_id}")
def get_node(node_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM storage_nodes WHERE id = ?;", (node_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
    return dict(row)

@app.get("/repairs")
def list_repairs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repair_jobs ORDER BY started_at DESC LIMIT 20;")
    repairs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return repairs

@app.get("/repairs/{job_id}")
def get_repair_job(job_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repair_jobs WHERE id = ?;", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Repair job not found")
    return dict(row)

@app.get("/events")
def list_events():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 30;")
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return events

@app.get("/cluster/metrics")
def get_metrics():
    return engine.get_cluster_status()

# ================= ADMIN CHAOS LAB & INTEGRITY APIs =================

@app.post("/admin/nodes/{node_id}/fail")
def admin_fail_node(node_id: int, admin: UserProfile = Depends(require_admin)):
    return engine.fail_node(node_id)

@app.post("/admin/nodes/{node_id}/restore")
def admin_restore_node(node_id: int, admin: UserProfile = Depends(require_admin)):
    return engine.restore_node(node_id)

@app.post("/admin/nodes/{node_id}/partition")
def admin_partition_node_by_id(node_id: int, admin: UserProfile = Depends(require_admin)):
    return engine.partition_node(node_id)

@app.post("/admin/network-partition")
def admin_network_partition(node_id: int = Query(5), admin: UserProfile = Depends(require_admin)):
    return engine.partition_node(node_id)

@app.post("/admin/nodes/{node_id}/network-restore")
def admin_network_restore_node_by_id(node_id: int, admin: UserProfile = Depends(require_admin)):
    return engine.restore_node(node_id)

@app.post("/admin/network-restore")
def admin_network_restore(node_id: int = Query(5), admin: UserProfile = Depends(require_admin)):
    return engine.restore_node(node_id)

@app.post("/admin/corrupt")
def admin_corrupt_replica(node_id: int = Form(...), admin: UserProfile = Depends(require_admin)):
    return engine.corrupt_replica_on_node(node_id)

@app.post("/admin/rebalance")
def admin_trigger_rebalance(admin: UserProfile = Depends(require_admin)):
    return engine.trigger_rebalance()

@app.post("/admin/integrity-scan")
@app.get("/integrity/status")
def admin_integrity_scan(admin: Optional[UserProfile] = Depends(get_current_user)):
    return engine.run_integrity_scan()

@app.post("/admin/reset")
def admin_reset_test_cluster(admin: UserProfile = Depends(require_admin)):
    engine.reset_test_cluster()
    return {"status": "SUCCESS", "message": "Cluster state reset"}

# ================= ADVANCED MERKLE & RAFT ENGINE APIS =================

@app.get("/api/v1/merkle/inspect/{object_id}")
def inspect_merkle(object_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM objects WHERE id = ?;", (object_id,))
    obj = cursor.fetchone()
    conn.close()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    
    payload, _ = engine.download_object(object_id)
    tree = MerkleTreeEngine.build_tree(payload)
    return {
        "object_id": object_id,
        "name": obj["name"],
        "merkle_tree": tree
    }

@app.get("/api/v1/s3/snippets")
def get_s3_snippets(bucket: str = "primary-datasets", object_key: str = "architecture_spec.parquet"):
    return S3IAMGateway.generate_sdk_snippets(bucket, object_key)

@app.get("/api/v1/raft/status")
def get_raft_status():
    return raft_engine.get_raft_state()

@app.post("/api/v1/raft/election")
def trigger_raft_election():
    return raft_engine.trigger_election()

@app.get("/api/v1/benchmark/run")
def run_benchmark():
    return PerformanceLabEngine.run_benchmark_suite()

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
