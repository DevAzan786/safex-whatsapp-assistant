import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.core.db import get_db_connection
from app.services.redis_client import get_redis_client

def main():
    print(f"Connecting to SQLite database at {settings.sqlite_db_path}...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete from tables
        print("Clearing 'leads' table...")
        cursor.execute("DELETE FROM leads")
        
        print("Clearing 'handovers' table...")
        cursor.execute("DELETE FROM handovers")
        
        print("Clearing 'analytics_logs' table...")
        cursor.execute("DELETE FROM analytics_logs")
        
        conn.commit()
        conn.close()
        print("SQLite database tables successfully cleared!")
    except Exception as e:
        print(f"Error clearing SQLite database: {e}")

    # Clear Redis sessions if Redis is configured
    redis_client = get_redis_client()
    if redis_client:
        print("Redis client found, clearing session keys...")
        try:
            keys = redis_client.keys("session:*")
            if keys:
                redis_client.delete(*keys)
                print(f"Cleared {len(keys)} session keys from Redis.")
            else:
                print("No session keys found in Redis.")
        except Exception as e:
            print(f"Error clearing Redis: {e}")
    else:
        print("Redis is not configured/active. In-memory sessions will be reset upon restarting the FastAPI server.")

    print("\nData clearing complete. Please restart the FastAPI server to ensure all in-memory state is also reset.")

if __name__ == "__main__":
    main()
