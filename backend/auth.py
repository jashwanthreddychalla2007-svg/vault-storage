import time
import json
import hmac
import hashlib
import base64
import secrets
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel

class Role(str, Enum):
    PLATFORM_OWNER = "platform_owner"
    ORGANIZATION_OWNER = "organization_owner"
    ORGANIZATION_ADMIN = "organization_admin"
    STORAGE_OPERATOR = "storage_operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    mfa_enabled: bool = False
    created_at: float

class Organization(BaseModel):
    org_id: str
    name: str
    slug: str
    owner_id: str
    created_at: float

class OrganizationMember(BaseModel):
    org_id: str
    user_id: str
    role: Role
    joined_at: float

class Project(BaseModel):
    project_id: str
    org_id: str
    name: str
    slug: str
    created_by: str
    created_at: float

class Bucket(BaseModel):
    bucket_id: str
    project_id: str
    name: str
    slug: str
    storage_policy: str = "REED_SOLOMON_2_1"
    created_by: str
    created_at: float

class ApiKey(BaseModel):
    key_id: str
    name: str
    org_id: str
    prefix: str
    hash_secret: str
    scopes: List[str]
    created_at: float
    last_used: Optional[float] = None

class AuditLog(BaseModel):
    log_id: str
    actor_id: str
    org_id: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: float
    status: str = "SUCCESS"

# Standalone JWT encoder/decoder using standard Python hmac & base64
def create_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature_input = f"{b64_header}.{b64_payload}".encode()
    signature = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{b64_header}.{b64_payload}.{b64_sig}"

def verify_jwt(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        b64_header, b64_payload, b64_sig = parts
        signature_input = f"{b64_header}.{b64_payload}".encode()
        expected_sig = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
        b64_expected_sig = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if hmac.compare_digest(b64_sig, b64_expected_sig):
            padded_payload = b64_payload + "=" * (-len(b64_payload) % 4)
            payload_data = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
            return payload_data
    except Exception:
        pass
    return None

# Auth & Identity Manager
class VaultAuthManager:
    def __init__(self):
        self.secret_key = "vault_super_secret_jwt_signing_key_hackathon"
        self.users: Dict[str, UserProfile] = {}
        self.passwords: Dict[str, str] = {} # email -> password hash
        self.organizations: Dict[str, Organization] = {}
        self.members: List[OrganizationMember] = []
        self.projects: Dict[str, Project] = {}
        self.buckets: Dict[str, Bucket] = {}
        self.api_keys: Dict[str, ApiKey] = {}
        self.audit_logs: List[AuditLog] = []

        self._seed_default_data()

    def _seed_default_data(self):
        # Default Platform Owner / Storage Operator / Developer / Viewer
        user_owner = self.create_user("owner@vault.io", "VaultPlatform2026!Secure", "Jashwanth (Platform Owner)")
        user_op = self.create_user("operator@vault.io", "OperatorVault2026!", "Rahul (Storage Operator)")
        user_dev = self.create_user("dev@vault.io", "DeveloperVault2026!", "Ananya (Developer)")
        user_viewer = self.create_user("viewer@vault.io", "ViewerVault2026!", "Sam (Viewer)")

        # Organizations
        org1 = self.create_organization("Vault Labs Enterprise", "vault-labs", user_owner.user_id)
        org2 = self.create_organization("Academic Research Cluster", "academic-cluster", user_owner.user_id)

        # Memberships
        self.members.append(OrganizationMember(org_id=org1.org_id, user_id=user_owner.user_id, role=Role.PLATFORM_OWNER, joined_at=time.time()))
        self.members.append(OrganizationMember(org_id=org1.org_id, user_id=user_op.user_id, role=Role.STORAGE_OPERATOR, joined_at=time.time()))
        self.members.append(OrganizationMember(org_id=org1.org_id, user_id=user_dev.user_id, role=Role.DEVELOPER, joined_at=time.time()))
        self.members.append(OrganizationMember(org_id=org1.org_id, user_id=user_viewer.user_id, role=Role.VIEWER, joined_at=time.time()))

        # Default Project & Bucket
        proj = self.create_project(org1.org_id, "Hackathon Demo", "hackathon-demo", user_owner.user_id)
        self.create_bucket(proj.project_id, "primary-datasets", "datasets", "REED_SOLOMON_2_1", user_owner.user_id)
        self.create_bucket(proj.project_id, "backup-blobs", "backups", "REPLICATION_3X", user_owner.user_id)

        # Initial API Key
        self.create_api_key(org1.org_id, "CLI Producer Key", ["objects:read", "objects:write"])

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, email: str, password: str, display_name: str) -> UserProfile:
        if email in self.passwords:
            raise ValueError("User with this email already exists")
        if len(password) < 15:
            raise ValueError("Password must be at least 15 characters long per NIST guidance")
        
        user_id = f"usr_{secrets.token_hex(6)}"
        profile = UserProfile(
            user_id=user_id,
            email=email,
            display_name=display_name,
            created_at=time.time()
        )
        self.users[user_id] = profile
        self.passwords[email] = self.hash_password(password)
        return profile

    def authenticate_user(self, email: str, password: str) -> Optional[UserProfile]:
        pw_hash = self.hash_password(password)
        if email in self.passwords and self.passwords[email] == pw_hash:
            for u in self.users.values():
                if u.email == email:
                    return u
        return None

    def create_organization(self, name: str, slug: str, owner_id: str) -> Organization:
        org_id = f"org_{secrets.token_hex(6)}"
        org = Organization(org_id=org_id, name=name, slug=slug, owner_id=owner_id, created_at=time.time())
        self.organizations[org_id] = org
        self.members.append(OrganizationMember(org_id=org_id, user_id=owner_id, role=Role.ORGANIZATION_OWNER, joined_at=time.time()))
        return org

    def create_project(self, org_id: str, name: str, slug: str, creator_id: str) -> Project:
        proj_id = f"prj_{secrets.token_hex(6)}"
        proj = Project(project_id=proj_id, org_id=org_id, name=name, slug=slug, created_by=creator_id, created_at=time.time())
        self.projects[proj_id] = proj
        return proj

    def create_bucket(self, project_id: str, name: str, slug: str, storage_policy: str, creator_id: str) -> Bucket:
        bkt_id = f"bkt_{secrets.token_hex(6)}"
        bkt = Bucket(bucket_id=bkt_id, project_id=project_id, name=name, slug=slug, storage_policy=storage_policy, created_by=creator_id, created_at=time.time())
        self.buckets[bkt_id] = bkt
        return bkt

    def create_api_key(self, org_id: str, name: str, scopes: List[str]) -> Dict[str, str]:
        raw_secret = f"vault_live_{secrets.token_hex(16)}"
        key_hash = hashlib.sha256(raw_secret.encode()).hexdigest()
        key_id = f"key_{secrets.token_hex(6)}"
        prefix = raw_secret[:12] + "..."
        api_key = ApiKey(
            key_id=key_id,
            name=name,
            org_id=org_id,
            prefix=prefix,
            hash_secret=key_hash,
            scopes=scopes,
            created_at=time.time()
        )
        self.api_keys[key_id] = api_key
        return {"key_id": key_id, "raw_secret": raw_secret, "name": name, "prefix": prefix}

    def log_audit_event(self, actor_id: str, org_id: str, action: str, resource_type: str, resource_id: str, status: str = "SUCCESS"):
        entry = AuditLog(
            log_id=f"aud_{secrets.token_hex(6)}",
            actor_id=actor_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=time.time(),
            status=status
        )
        self.audit_logs.append(entry)
        if len(self.audit_logs) > 100:
            self.audit_logs.pop(0)

    def get_user_role(self, user_id: str, org_id: str) -> Role:
        for m in self.members:
            if m.user_id == user_id and m.org_id == org_id:
                return m.role
        return Role.VIEWER

    def check_authorization(self, role: Role, required_permission: str) -> bool:
        permissions = {
            Role.PLATFORM_OWNER: ["*"],
            Role.ORGANIZATION_OWNER: ["org:*", "project:*", "bucket:*", "object:*", "node:read", "node:operate", "chaos:*", "api_key:*", "audit:read"],
            Role.ORGANIZATION_ADMIN: ["org:members", "project:*", "bucket:*", "object:*", "node:read", "node:operate", "chaos:*", "api_key:*", "audit:read"],
            Role.STORAGE_OPERATOR: ["node:read", "node:operate", "chaos:*", "object:read", "audit:read"],
            Role.DEVELOPER: ["bucket:read", "bucket:create", "object:read", "object:write", "object:delete", "api_key:create"],
            Role.VIEWER: ["object:read", "node:read", "audit:read"]
        }

        user_perms = permissions.get(role, [])
        if "*" in user_perms:
            return True
        for perm in user_perms:
            if perm == required_permission or (perm.endswith(":*") and required_permission.startswith(perm[:-1])):
                return True
        return False
