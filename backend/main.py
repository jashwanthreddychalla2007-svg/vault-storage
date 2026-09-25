import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse
from typing import List, Optional, Dict, Any

from cluster import VaultCluster
from scrubber import AntiEntropyScrubber
from ai_agent import PredictiveNodeAIAgent
from auth import VaultAuthManager, Role
from merkle_engine import MerkleTreeEngine
from s3_gateway import S3IAMGateway
from raft_consensus import RaftConsensusEngine
from benchmark_lab import PerformanceLabEngine

app = FastAPI(title="Vault Enterprise Multi-Tenant Distributed Storage Platform", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cluster = VaultCluster(node_count=5)
scrubber = AntiEntropyScrubber(cluster, interval_seconds=5)
ai_agent = PredictiveNodeAIAgent(cluster)
auth_mgr = VaultAuthManager()
raft_engine = RaftConsensusEngine(node_ids=[1, 2, 3, 4, 5])

active_connections: List[WebSocket] = []


async def broadcast_telemetry():
    """Periodically broadcasts cluster state, Raft consensus logs, AI risk scores, and scrubber metrics."""
    while True:
        if active_connections:
            ai_eval = ai_agent.evaluate_node_telemetry()
            raft_state = raft_engine.get_raft_state()
            state = {
                "nodes": [n.to_dict() for n in cluster.nodes.values()],
                "object_count": len(cluster.objects),
                "ai_telemetry": ai_eval,
                "raft_state": raft_state,
                "scrubber_metrics": {
                    "scrub_count": scrubber.scrub_count,
                    "repaired_total": scrubber.repaired_chunks_total
                },
                "logs": cluster.event_log[-15:],
                "audit_logs": [a.dict() for a in auth_mgr.audit_logs[-10:]]
            }
            message = json.dumps(state)
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
    asyncio.create_task(scrubber.start_scrubbing_loop())
    
    # Populate initial sample seed objects
    cluster.upload_object("system_firmware.bin", b"BOOT_LOADER_SECURE_KEY_9921_OK_VERIFIED_CHECKSUM_OK", "REED_SOLOMON_2_1")
    cluster.upload_object("dataset_sample.parquet", b"COL1,COL2,COL3\n100,200,300\n400,500,600\n700,800,900\n", "REPLICATION_3X")


# Authorization helper
def verify_role_permission(user_role: str, required_perm: str, actor_id: str, org_id: str):
    try:
        r = Role(user_role)
    except ValueError:
        r = Role.VIEWER
    
    if not auth_mgr.check_authorization(r, required_perm):
        auth_mgr.log_audit_event(actor_id, org_id, f"DENIED_{required_perm.upper()}", "SECURITY", "403_FORBIDDEN", "FAILED")
        raise HTTPException(
            status_code=403, 
            detail=f"403 Forbidden: Role '{user_role}' lacks permission '{required_perm}'"
        )


@app.get("/health")
def health_check():
    return {
        "status": "ONLINE", 
        "cluster": "HEALTHY", 
        "nodes": len(cluster.nodes), 
        "ai_agent": "ACTIVE",
        "raft_consensus": "CONVERGED",
        "auth_engine": "SUPABASE_NIST_RBAC_ONLINE"
    }

# ================= AUTHENTICATION & IAM ENDPOINTS =================

@app.post("/api/v1/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = auth_mgr.authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    orgs = list(auth_mgr.organizations.values())
    default_org = orgs[0] if orgs else None
    role = auth_mgr.get_user_role(user.user_id, default_org.org_id if default_org else "")
    
    auth_mgr.log_audit_event(user.user_id, default_org.org_id if default_org else "sys", "LOGIN_SUCCESS", "USER", user.user_id)
    return {
        "user": user,
        "token": f"jwt_mock_token_{user.user_id}",
        "organizations": orgs,
        "current_role": role,
        "current_org": default_org
    }

@app.post("/api/v1/auth/signup")
def signup(email: str = Form(...), password: str = Form(...), display_name: str = Form(...)):
    try:
        user = auth_mgr.create_user(email, password, display_name)
        org = auth_mgr.create_organization(f"{display_name}'s Workspace", f"workspace-{user.user_id[:6]}", user.user_id)
        auth_mgr.log_audit_event(user.user_id, org.org_id, "USER_SIGNUP", "USER", user.user_id)
        return {"user": user, "org": org}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@app.get("/api/v1/organizations")
def list_organizations():
    return list(auth_mgr.organizations.values())

@app.get("/api/v1/projects")
def list_projects(org_id: Optional[str] = None):
    if org_id:
        return [p for p in auth_mgr.projects.values() if p.org_id == org_id]
    return list(auth_mgr.projects.values())

@app.get("/api/v1/buckets")
def list_buckets():
    return list(auth_mgr.buckets.values())

@app.post("/api/v1/buckets")
def create_bucket(
    name: str = Form(...), 
    project_id: str = Form(...), 
    policy: str = Form("REED_SOLOMON_2_1"),
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "bucket:create", x_user_id, "org_default")
    bkt = auth_mgr.create_bucket(project_id, name, name.lower().replace(" ", "-"), policy, x_user_id)
    auth_mgr.log_audit_event(x_user_id, "org_default", "BUCKET_CREATE", "BUCKET", bkt.bucket_id)
    return bkt

@app.get("/api/v1/api-keys")
def list_api_keys():
    return list(auth_mgr.api_keys.values())

@app.post("/api/v1/api-keys")
def create_api_key(
    name: str = Form(...), 
    scopes: str = Form("objects:read,objects:write"),
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "api_key:create", x_user_id, "org_default")
    scope_list = [s.strip() for s in scopes.split(",")]
    res = auth_mgr.create_api_key("org_default", name, scope_list)
    auth_mgr.log_audit_event(x_user_id, "org_default", "API_KEY_CREATE", "API_KEY", res["key_id"])
    return res

@app.get("/api/v1/audit-logs")
def list_audit_logs():
    return [a.dict() for a in auth_mgr.audit_logs]

# ================= ADVANCED ENGINES: MERKLE, S3 SDK, RAFT & BENCHMARKS =================

@app.get("/api/v1/merkle/inspect/{object_id}")
def inspect_merkle_tree(object_id: str):
    if object_id not in cluster.objects:
        raise HTTPException(status_code=404, detail="Object not found")
    obj = cluster.objects[object_id]
    tree = MerkleTreeEngine.build_tree(obj["payload_sample"])
    return {
        "object_id": object_id,
        "filename": obj["filename"],
        "size_bytes": obj["size_bytes"],
        "merkle_root": obj["merkle_root"],
        "merkle_tree": tree
    }

@app.get("/api/v1/merkle/bitrot-diff/{object_id}")
def inspect_bitrot_diff(object_id: str):
    if object_id not in cluster.objects:
        raise HTTPException(status_code=404, detail="Object not found")
    obj = cluster.objects[object_id]
    original = obj["payload_sample"]
    # Create simulated corrupt payload for diff inspection
    corrupted = bytearray(original)
    if len(corrupted) > 4:
        corrupted[3] = (corrupted[3] + 1) % 256

    diff = MerkleTreeEngine.inspect_bitrot_diff(original, bytes(corrupted))
    return {
        "object_id": object_id,
        "filename": obj["filename"],
        "diff_inspection": diff
    }

@app.get("/api/v1/s3/snippets")
def get_s3_snippets(bucket: str = "primary-datasets", object_key: str = "system_firmware.bin"):
    return S3IAMGateway.generate_sdk_snippets(bucket, object_key)

@app.post("/api/v1/iam/evaluate")
def evaluate_iam_policy(policy_json: str = Form(...), action: str = Form(...), resource: str = Form(...)):
    try:
        p_data = json.loads(policy_json)
        return S3IAMGateway.evaluate_iam_policy(p_data, action, resource)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid IAM JSON format: {str(e)}")

@app.get("/api/v1/raft/status")
def get_raft_status():
    return raft_engine.get_raft_state()

@app.post("/api/v1/raft/election")
def trigger_raft_election():
    res = raft_engine.trigger_election()
    auth_mgr.log_audit_event("usr_owner", "org_default", "RAFT_ELECTION_TRIGGERED", "CONSENSUS", f"term_{res['term']}")
    return res

@app.get("/api/v1/benchmark/run")
def run_benchmark():
    return PerformanceLabEngine.run_benchmark_suite()

# ================= CORE CLUSTER & OBJECT APIS WITH RBAC =================

@app.get("/api/v1/cluster/status")
def get_cluster_status():
    return {
        "nodes": [n.to_dict() for n in cluster.nodes.values()],
        "object_count": len(cluster.objects),
        "total_used_bytes": sum(n.used_bytes for n in cluster.nodes.values()),
        "ai_telemetry": ai_agent.evaluate_node_telemetry(),
        "raft_state": raft_engine.get_raft_state(),
        "scrubber_metrics": {
            "scrub_count": scrubber.scrub_count,
            "repaired_total": scrubber.repaired_chunks_total
        },
        "event_logs": cluster.event_log[-20:],
        "audit_logs": [a.dict() for a in auth_mgr.audit_logs[-15:]]
    }


@app.get("/api/v1/objects")
def list_objects():
    return list(cluster.objects.values())


@app.post("/api/v1/objects/upload")
async def upload_object(
    file: UploadFile = File(...), 
    policy: str = Form("REED_SOLOMON_2_1"),
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "object:write", x_user_id, "org_default")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File cannot be empty")
    try:
        result = cluster.upload_object(file.filename, contents, policy)
        auth_mgr.log_audit_event(x_user_id, "org_default", "OBJECT_UPLOAD", "OBJECT", file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/objects/{object_id}/download")
def download_object(
    object_id: str,
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "object:read", x_user_id, "org_default")
    try:
        data, checked = cluster.download_object(object_id)
        obj_meta = cluster.objects[object_id]
        headers = {
            "Content-Disposition": f"attachment; filename={obj_meta['filename']}",
            "X-Vault-Repaired": str(checked)
        }
        auth_mgr.log_audit_event(x_user_id, "org_default", "OBJECT_DOWNLOAD", "OBJECT", object_id)
        return Response(content=data, media_type="application/octet-stream", headers=headers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Object not found")
    except RuntimeError as r:
        raise HTTPException(status_code=503, detail=str(r))


@app.post("/api/v1/chaos/kill-node")
def kill_node(
    node_id: int = Form(...),
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "chaos:kill_node", x_user_id, "org_default")
    res = cluster.kill_node(node_id)
    auth_mgr.log_audit_event(x_user_id, "org_default", "NODE_FAIL_SIMULATION", "NODE", f"node-{node_id}")
    return res


@app.post("/api/v1/chaos/bitrot")
def inject_bitrot(
    node_id: int = Form(...),
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "chaos:bitrot", x_user_id, "org_default")
    res = cluster.inject_bitrot(node_id)
    auth_mgr.log_audit_event(x_user_id, "org_default", "BITROT_INJECTION", "NODE", f"node-{node_id}")
    return res


@app.post("/api/v1/chaos/recover")
def recover_cluster(
    x_user_role: str = Header("platform_owner"),
    x_user_id: str = Header("usr_owner")
):
    verify_role_permission(x_user_role, "chaos:recover", x_user_id, "org_default")
    res = cluster.recover_all()
    auth_mgr.log_audit_event(x_user_id, "org_default", "CLUSTER_RECOVERY", "CLUSTER", "all_nodes")
    return res


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
