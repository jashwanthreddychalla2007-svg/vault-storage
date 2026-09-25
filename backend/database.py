import os
import sqlite3
import time
import json
import secrets
import hashlib
from typing import Dict, List, Any, Optional

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database.db"))

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'USER',
        created_at REAL NOT NULL
    );
    """)

    # 2. Buckets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS buckets (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT UNIQUE NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # 3. Objects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS objects (
        id TEXT PRIMARY KEY,
        bucket_id TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        name TEXT NOT NULL,
        size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        latest_version INTEGER NOT NULL DEFAULT 1,
        state TEXT NOT NULL DEFAULT 'HEALTHY',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY(bucket_id) REFERENCES buckets(id),
        FOREIGN KEY(owner_id) REFERENCES users(id)
    );
    """)

    # 4. Object Versions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS object_versions (
        id TEXT PRIMARY KEY,
        object_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        checksum TEXT NOT NULL,
        size INTEGER NOT NULL,
        is_tombstone INTEGER NOT NULL DEFAULT 0,
        created_at REAL NOT NULL,
        FOREIGN KEY(object_id) REFERENCES objects(id)
    );
    """)

    # 5. Object Replicas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS object_replicas (
        id TEXT PRIMARY KEY,
        object_version_id TEXT NOT NULL,
        node_id INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'HEALTHY',
        checksum TEXT NOT NULL,
        created_at REAL NOT NULL,
        verified_at REAL NOT NULL,
        FOREIGN KEY(object_version_id) REFERENCES object_versions(id)
    );
    """)

    # 6. Storage Nodes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS storage_nodes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        host TEXT NOT NULL,
        port INTEGER NOT NULL,
        zone TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'HEALTHY',
        capacity INTEGER NOT NULL DEFAULT 10737418240, -- 10 GB
        used_storage INTEGER NOT NULL DEFAULT 0,
        last_heartbeat REAL NOT NULL,
        created_at REAL NOT NULL
    );
    """)

    # 7. Repair Jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repair_jobs (
        id TEXT PRIMARY KEY,
        object_id TEXT NOT NULL,
        source_node INTEGER NOT NULL,
        target_node INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        progress INTEGER NOT NULL DEFAULT 0,
        bytes_recovered INTEGER NOT NULL DEFAULT 0,
        started_at REAL NOT NULL,
        completed_at REAL
    );
    """)

    # 8. Events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        timestamp REAL NOT NULL,
        severity TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        node_id INTEGER,
        object_id TEXT,
        metadata TEXT
    );
    """)

    # 9. Policies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        replication_factor INTEGER NOT NULL DEFAULT 3,
        availability_policy TEXT NOT NULL DEFAULT 'HIGH_DURABILITY',
        rebalance_threshold REAL NOT NULL DEFAULT 0.3,
        created_at REAL NOT NULL
    );
    """)

    conn.commit()

    # Seed Default 6 Storage Nodes (Zone A: Nodes 1..3, Zone B: Nodes 4..6)
    cursor.execute("SELECT COUNT(*) FROM storage_nodes;")
    if cursor.fetchone()[0] == 0:
        now = time.time()
        nodes_data = [
            (1, "Node 01", "localhost", 5001, "ZONE_A", "HEALTHY", 10737418240, 104857600, now, now),
            (2, "Node 02", "localhost", 5002, "ZONE_A", "HEALTHY", 10737418240, 94371840, now, now),
            (3, "Node 03", "localhost", 5003, "ZONE_A", "HEALTHY", 10737418240, 115343360, now, now),
            (4, "Node 04", "localhost", 5004, "ZONE_B", "HEALTHY", 10737418240, 83886080, now, now),
            (5, "Node 05", "localhost", 5005, "ZONE_B", "HEALTHY", 10737418240, 89128960, now, now),
            (6, "Node 06", "localhost", 5006, "ZONE_B", "HEALTHY", 10737418240, 15728640, now, now)
        ]
        cursor.executemany("""
        INSERT INTO storage_nodes (id, name, host, port, zone, status, capacity, used_storage, last_heartbeat, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, nodes_data)
        conn.commit()

    # Seed Default Users & Buckets
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        now = time.time()
        pw_hash = hashlib.sha256("AdminVault2026!Secure".encode()).hexdigest()
        admin_id = "usr_admin_001"
        user_id = "usr_dev_002"
        cursor.execute("INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?);",
                       (admin_id, "System Administrator", "admin@vault.io", pw_hash, "ADMIN", now))
        cursor.execute("INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?);",
                       (user_id, "Developer User", "dev@vault.io", pw_hash, "USER", now))
        
        cursor.execute("INSERT INTO buckets (id, user_id, name, created_at) VALUES (?, ?, ?, ?);",
                       ("bkt_primary_datasets", admin_id, "primary-datasets", now))
        cursor.execute("INSERT INTO buckets (id, user_id, name, created_at) VALUES (?, ?, ?, ?);",
                       ("bkt_backup_blobs", admin_id, "backup-blobs", now))
        conn.commit()

    # Seed Default Policy
    cursor.execute("SELECT COUNT(*) FROM policies;")
    if cursor.fetchone()[0] == 0:
        now = time.time()
        cursor.execute("INSERT INTO policies (id, name, replication_factor, availability_policy, rebalance_threshold, created_at) VALUES (?, ?, ?, ?, ?, ?);",
                       ("pol_default_rf3", "Standard Replication x3", 3, "HIGH_DURABILITY", 0.3, now))
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully.")
