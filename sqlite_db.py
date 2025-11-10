# services/sqlite_db.py
import sqlite3
from typing import Optional, Dict, Any,List

DB_FILE = "leads.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        email TEXT,
        job_title TEXT,
        website TEXT,
        phone TEXT,
        enriched_lead TEXT,
        icp_score INTEGER,
        assigned_rep TEXT,
        error TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_lead(lead: Dict[str, Any]) -> int:
    """
    Insert a new lead record. `lead` dict should contain keys:
    company, email, job_title, website, phone, enriched_lead (JSON string),
    icp_score, assigned_rep, error
    Returns inserted row id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO leads (company, email, job_title, website, phone, enriched_lead, icp_score, assigned_rep, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead.get("company"),
        lead.get("email"),
        lead.get("job_title"),
        lead.get("website"),
        lead.get("phone"),
        lead.get("enriched_lead"),
        lead.get("icp_score"),
        lead.get("assigned_rep"),
        lead.get("error"),
    ))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

def get_lead_by_id(lead_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_leads() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
