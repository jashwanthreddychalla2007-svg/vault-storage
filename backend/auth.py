import time
import json
import hmac
import hashlib
import base64
import secrets
import re
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from database import get_db

class Role(str, Enum):
    PLATFORM_OWNER = "platform_owner"
    ORGANIZATION_OWNER = "organization_owner"
    ORGANIZATION_ADMIN = "organization_admin"
    STORAGE_OPERATOR = "storage_operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    ADMIN = "ADMIN"
    USER = "USER"

class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str = "USER"
    avatar_url: Optional[str] = None
    mfa_enabled: bool = False
    created_at: float

def create_jwt(payload: dict, secret: str = "vault_super_secret_jwt_signing_key_hackathon") -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature_input = f"{b64_header}.{b64_payload}".encode()
    signature = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{b64_header}.{b64_payload}.{b64_sig}"

def verify_jwt(token: str, secret: str = "vault_super_secret_jwt_signing_key_hackathon") -> Optional[dict]:
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

class VaultAuthManager:
    def __init__(self):
        self.secret_key = "vault_super_secret_jwt_signing_key_hackathon"
        self.users: Dict[str, UserProfile] = {}
        self.passwords: Dict[str, str] = {}
        self._seed_default_data()

    def _seed_default_data(self):
        # Admin user seed
        try:
            self.create_user("admin@vault.io", "AdminVault2026!Secure", "Platform Admin", role="ADMIN", user_id_override="usr_admin_001")
        except ValueError:
            pass

        # Standard user seed
        try:
            self.create_user("user@vault.io", "StandardUser2026!Pass", "Standard Developer", role="USER", user_id_override="usr_user_001")
        except ValueError:
            pass

    def hash_password(self, password: str) -> str:
        return hashlib.sha256((password + "vault_salt_2026").encode()).hexdigest()

    def validate_email(self, email: str) -> bool:
        regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(regex, email))

    def create_user(self, email: str, password: str, display_name: str, role: str = "USER", user_id_override: Optional[str] = None) -> UserProfile:
        if not self.validate_email(email):
            raise ValueError("Invalid email format")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?;", (email,))
        if cursor.fetchone() or email in self.passwords:
            conn.close()
            raise ValueError("User with this email already exists")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        user_id = user_id_override or f"usr_{secrets.token_hex(6)}"
        pw_hash = self.hash_password(password)
        now = time.time()

        cursor.execute("""
        INSERT INTO users (id, name, email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (user_id, display_name, email, pw_hash, role, now))
        conn.commit()
        conn.close()

        profile = UserProfile(
            user_id=user_id,
            email=email,
            display_name=display_name,
            role=role,
            created_at=now
        )
        self.users[user_id] = profile
        self.passwords[email] = pw_hash
        return profile

    def authenticate_user(self, email: str, password: str) -> Optional[UserProfile]:
        pw_hash = self.hash_password(password)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        conn.close()

        if row and row["password_hash"] == pw_hash:
            return UserProfile(
                user_id=row["id"],
                email=row["email"],
                display_name=row["name"],
                role=row["role"],
                created_at=row["created_at"]
            )
        return None

    def generate_token(self, user: UserProfile) -> str:
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "role": user.role,
            "exp": time.time() + 86400
        }
        return create_jwt(payload, self.secret_key)
