from datetime import datetime
from app.core.db import get_db_connection

def sync_lead(phone: str, name: str, email: str, requirements: str) -> dict:
    """
    Syncs a captured lead to the SQLite leads table.
    If the lead exists (matched by phone), it updates the existing lead and
    appends the new requirements instead of duplicating.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    # Check for existing lead by phone
    cursor.execute("SELECT * FROM leads WHERE phone = ?", (phone,))
    existing_by_phone = cursor.fetchone()
    
    if not existing_by_phone:
        # Also check by email to be safe
        cursor.execute("SELECT * FROM leads WHERE email = ?", (email,))
        existing_by_phone = cursor.fetchone()
        
    if existing_by_phone:
        lead_id = existing_by_phone["id"]
        old_reqs = existing_by_phone["requirements"]
        
        # Append requirements
        updated_reqs = f"{old_reqs} | [Update {timestamp}]: {requirements}"
        
        cursor.execute("""
            UPDATE leads
            SET name = ?, email = ?, requirements = ?, updated_at = ?
            WHERE id = ?
        """, (name, email, updated_reqs, timestamp, lead_id))
        
        action = "updated"
    else:
        cursor.execute("""
            INSERT INTO leads (phone, name, email, requirements, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (phone, name, email, requirements, timestamp))
        
        action = "created"
        
    conn.commit()
    conn.close()
    
    return {"status": "success", "action": action}

def get_all_leads():
    """
    Retrieves all leads from the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
