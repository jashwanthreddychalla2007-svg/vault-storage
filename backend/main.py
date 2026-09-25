import sys
import os

# Add backend directory to sys.path for clean import resolution on Render / Docker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from typing import List, Optional, Dict, Any

from database import init_db, get_db
from engine import StorageClusterEngine
from auth import VaultAuthManager, Role
from merkle_engine import MerkleTreeEngine
from s3_gateway import S3IAMGateway
from raft_consensus import RaftConsensusEngine
from benchmark_lab import PerformanceLabEngine

app = FastAPI(title="Vault 6-Node Self-Healing Distributed Object Storage System", version="3.0.0")

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
    """Periodically broadcasts 6-Node cluster state, Raft logs, auto-repairs, and events over WebSockets."""
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
    asyncio.create_task(broadcast_telemetry())
    
    # Seed sample object if database is empty
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM objects WHERE state != 'DELETED';")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        engine.upload_object("usr_admin_001", "primary-datasets", "architecture_spec.parquet",
                             b"COL1,COL2,COL3\n100,200,300\n400,500,600\n700,800,900\n",
                             "application/octet-stream", replication_factor=3)


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
        return {"user": user}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = auth_mgr.authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "user": user,
        "token": f"jwt_mock_token_{user.user_id}",
        "role": user.role if hasattr(user, 'role') else "ADMIN"
    }

@app.get("/auth/me")
def get_current_user():
    users = list(auth_mgr.users.values())
    return users[0] if users else {"name": "Admin", "role": "ADMIN"}

# ================= OBJECTS & VERSIONS APIS =================

@app.get("/objects")
def list_objects():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM objects WHERE state != 'DELETED' ORDER BY updated_at DESC;")
    objs = [dict(r) for r in cursor.fetchall()]
    
    # Attach replica info
    for obj in objs:
        cursor.execute("""
        SELECT r.node_id, r.state, n.zone 
        FROM object_replicas r 
        JOIN object_versions v ON r.object_version_id = v.id 
        JOIN storage_nodes n ON r.node_id = n.id 
        WHERE v.object_id = ? AND v.version_number = ?;
        """, (obj["id"], obj["latest_version"]))
        obj["replicas"] = [dict(r) for r in cursor.fetchall()]
    
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
async def upload_object(
    file: UploadFile = File(...), 
    bucket: str = Form("primary-datasets"),
    replication_factor: int = Form(3)
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File cannot be empty")
    try:
        res = engine.upload_object("usr_admin_001", bucket, file.filename, contents, file.content_type or "application/octet-stream", replication_factor)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/objects/{object_id}/download")
def download_object(object_id: str, version: Optional[int] = None):
    try:
        data, repaired = engine.download_object(object_id, version)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM objects WHERE id = ?;", (object_id,))
        row = cursor.fetchone()
        filename = row["name"] if row else "download.bin"
        conn.close()

        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Vault-Repaired": str(repaired)
        }
        return Response(content=data, media_type="application/octet-stream", headers=headers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Object not found or deleted")
    except RuntimeError as r:
        raise HTTPException(status_code=503, detail=str(r))

@app.delete("/objects/{object_id}")
def delete_object(object_id: str):
    try:
        return engine.delete_object(object_id, "usr_admin_001")
    except KeyError:
        raise HTTPException(status_code=404, detail="Object not found")

@app.get("/objects/{object_id}/versions")
def get_object_versions(object_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM object_versions WHERE object_id = ? ORDER BY version_number DESC;", (object_id,))
    versions = [dict(v) for v in cursor.fetchall()]
    conn.close()
    return versions

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
def admin_fail_node(node_id: int):
    return engine.fail_node(node_id)

@app.post("/admin/nodes/{node_id}/restore")
def admin_restore_node(node_id: int):
    return engine.restore_node(node_id)

@app.post("/admin/nodes/{node_id}/partition")
def admin_partition_node(node_id: int):
    return engine.partition_node(node_id)

@app.post("/admin/nodes/{node_id}/network-restore")
def admin_network_restore_node(node_id: int):
    return engine.restore_node(node_id)

@app.post("/admin/corrupt")
def admin_corrupt_replica(node_id: int = Form(...)):
    return engine.corrupt_replica_on_node(node_id)

@app.post("/admin/rebalance")
def admin_trigger_rebalance():
    return engine.trigger_rebalance()

@app.post("/admin/integrity-scan")
@app.get("/integrity/status")
def admin_integrity_scan():
    return engine.run_integrity_scan()

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
    
    # Compute Merkle tree over payload
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
