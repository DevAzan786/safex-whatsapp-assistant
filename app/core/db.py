import sqlite3
import os
from datetime import datetime
from app.config import settings

def get_db_connection():
    db_path = settings.sqlite_db_path
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Leads table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        name TEXT,
        email TEXT,
        requirements TEXT,
        updated_at TEXT
    )
    """)
    
    # Handovers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS handovers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        status TEXT, -- 'pending', 'claimed', 'resolved'
        reason TEXT,
        assigned_agent TEXT,
        created_at TEXT
    )
    """)
    
    # Analytics logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        phone TEXT,
        message TEXT,
        intent TEXT,
        language TEXT,
        is_faq_hit BOOLEAN,
        is_lead BOOLEAN,
        is_handover BOOLEAN,
        confidence REAL,
        response TEXT
    )
    """)
    
    conn.commit()
    conn.close()
