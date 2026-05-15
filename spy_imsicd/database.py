import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "spy_imsicd.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        # Log deteksi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mcc TEXT,
                mnc TEXT,
                lac INTEGER,
                cid INTEGER,
                network_type TEXT,
                rssi INTEGER,
                detection_type TEXT,
                severity TEXT,
                details TEXT
            )
        """)
        # Whitelist sel (trusted)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mcc TEXT,
                mnc TEXT,
                lac INTEGER,
                cid INTEGER,
                reason TEXT,
                added_at TEXT
            )
        """)
        # Blacklist sel (suspicious)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mcc TEXT,
                mnc TEXT,
                lac INTEGER,
                cid INTEGER,
                reason TEXT,
                first_seen TEXT,
                last_seen TEXT
            )
        """)
        self.conn.commit()

    def add_detection(self, detection: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO detections (timestamp, mcc, mnc, lac, cid, network_type, rssi, detection_type, severity, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detection.get("timestamp", datetime.utcnow().isoformat()),
            detection.get("mcc"),
            detection.get("mnc"),
            detection.get("lac"),
            detection.get("cid"),
            detection.get("network_type"),
            detection.get("rssi"),
            detection.get("detection_type"),
            detection.get("severity"),
            detection.get("details"),
        ))
        self.conn.commit()

    def is_whitelisted(self, mcc: str, mnc: str, lac: int, cid: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM whitelist WHERE mcc=? AND mnc=? AND lac=? AND cid=?", 
                       (mcc, mnc, lac, cid))
        return cursor.fetchone() is not None

    def add_to_whitelist(self, mcc, mnc, lac, cid, reason="manual"):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO whitelist (mcc, mnc, lac, cid, reason, added_at) VALUES (?,?,?,?,?,?)",
                       (mcc, mnc, lac, cid, reason, datetime.utcnow().isoformat()))
        self.conn.commit()

    def add_to_blacklist(self, mcc, mnc, lac, cid, reason):
        now = datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO blacklist (mcc, mnc, lac, cid, reason, first_seen, last_seen)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT DO UPDATE SET last_seen=?, reason=?
        """, (mcc, mnc, lac, cid, reason, now, now, now, reason))
        self.conn.commit()

    def get_recent_detections(self, limit=100) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    def close(self):
        self.conn.close()
