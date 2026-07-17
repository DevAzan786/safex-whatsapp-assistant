from datetime import datetime
from app.core.db import get_db_connection

def log_message(phone: str, message: str, intent: str, language: str, 
                is_faq_hit: bool, is_lead: bool, is_handover: bool, 
                confidence: float, response: str):
    """
    Logs an interaction in the SQLite analytics database.
    """
    timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analytics_logs (
            timestamp, phone, message, intent, language, 
            is_faq_hit, is_lead, is_handover, confidence, response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, phone, message, intent, language, 
        1 if is_faq_hit else 0, 
        1 if is_lead else 0, 
        1 if is_handover else 0, 
        confidence, response
    ))
    conn.commit()
    conn.close()

def get_analytics_metrics() -> dict:
    """
    Aggregates metrics for the dashboard view.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Basic counts
    cursor.execute("SELECT COUNT(*) FROM analytics_logs")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analytics_logs WHERE is_faq_hit = 1")
    faq_hits = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analytics_logs WHERE is_handover = 1")
    handovers_triggered = cursor.fetchone()[0]
    
    # Leads count from leads table
    cursor.execute("SELECT COUNT(*) FROM leads")
    leads_collected = cursor.fetchone()[0]
    
    # 2. Language distribution
    cursor.execute("SELECT language, COUNT(*) as count FROM analytics_logs GROUP BY language")
    lang_rows = cursor.fetchall()
    language_distribution = {row["language"]: row["count"] for row in lang_rows}
    
    # 3. Intent distribution
    cursor.execute("SELECT intent, COUNT(*) as count FROM analytics_logs GROUP BY intent")
    intent_rows = cursor.fetchall()
    intent_distribution = {row["intent"]: row["count"] for row in intent_rows}
    
    # 4. Recent logs
    cursor.execute("SELECT * FROM analytics_logs ORDER BY timestamp DESC LIMIT 20")
    log_rows = cursor.fetchall()
    recent_messages = [dict(row) for row in log_rows]
    
    conn.close()
    
    return {
        "total_messages": total_messages,
        "faq_hits": faq_hits,
        "leads_collected": leads_collected,
        "handovers_triggered": handovers_triggered,
        "language_distribution": language_distribution,
        "intent_distribution": intent_distribution,
        "recent_messages": recent_messages
    }
