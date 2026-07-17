from datetime import datetime
from app.core.db import get_db_connection
from app.core.session import set_session, clear_session

def trigger_handover(sender: str, reason: str) -> str:
    """
    Triggers a human handover by:
    1. Updating user session state to 'handover_active'.
    2. Logging a pending handover escalation in the SQLite database.
    Returns the handover confirmation message.
    """
    timestamp = datetime.now().isoformat()
    
    # 1. Update session state
    set_session(sender, state="handover_active")
    
    # 2. Add to database handovers queue
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO handovers (phone, status, reason, assigned_agent, created_at)
        VALUES (?, 'pending', ?, NULL, ?)
    """, (sender, reason, timestamp))
    conn.commit()
    conn.close()
    
    return (
        "I am connecting you to a human agent who can help. "
        "A representative will review our conversation history and message you shortly."
    )

def get_pending_handovers():
    """
    Returns all pending handover tickets.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM handovers WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def claim_handover(handover_id: int, agent_name: str) -> bool:
    """
    Claims a pending handover ticket, assigning it to an agent.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE handovers SET status = 'claimed', assigned_agent = ? WHERE id = ? AND status = 'pending'",
        (agent_name, handover_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def resolve_handover(handover_id: int) -> bool:
    """
    Resolves a handover ticket, which clears the user session, allowing the bot to respond again.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM handovers WHERE id = ?", (handover_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    phone = row["phone"]
    
    # Resolve in database
    cursor.execute("UPDATE handovers SET status = 'resolved' WHERE id = ?", (handover_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    # Clear user session to resume bot operations
    clear_session(phone)
    return affected > 0
