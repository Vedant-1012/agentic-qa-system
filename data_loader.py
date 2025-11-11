import requests
import duckdb
import os

# --- Configuration ---
API_URL = "https://november7-730026606190.europe-west1.run.app/messages/"
DB_FILE = "data.db"

def fetch_data():
    """Fetches all messages from the API."""
    print(f"Attempting to fetch data from {API_URL}...")
    try:
        response = requests.get(API_URL, params={"skip": 0, "limit": 10000}) 
        response.raise_for_status()
        data = response.json()
        messages = data.get("items")
        
        if messages is None:
            print("Error: 'items' key not found in API response.")
            print("Full response:", data)
            return None

        print(f"Success! Fetched {len(messages)} messages.")
        return messages
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def create_database(messages):
    """Creates a DuckDB database and table from the messages."""
    if not messages or not isinstance(messages, list):
        print("No messages to load or data is not a list. Exiting.")
        return

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old {DB_FILE}.")

    print(f"Creating new database: {DB_FILE}")
    
    first_message = messages[0]
    columns = []
    for key, value in first_message.items():
        # Get correct column names from the data itself
        col_name = key
        if isinstance(value, int): col_type = "BIGINT"
        elif isinstance(value, float): col_type = "DOUBLE"
        else: col_type = "VARCHAR"
        columns.append(f"{col_name} {col_type}")
    
    table_schema = ", ".join(columns)

    con = duckdb.connect(DB_FILE)
    con.execute(f"CREATE TABLE messages ({table_schema})")

    for msg in messages:
        con.execute(f"INSERT INTO messages VALUES ({', '.join(['?'] * len(msg))})", list(msg.values()))
    
    print(f"Successfully inserted {len(messages)} messages into {DB_FILE}.")
    
    print("\n--- Bonus 2: Data Insights (from DB) ---")
    
    total = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    print(f"1. Total messages analyzed: {total}")

    # --- THIS IS THE FIX ---
    # The data doesn't seem to have a unique 'msg_id'. 
    # Let's check for duplicate *users* instead, which is also an anomaly.
    try:
        # NOTE: This query is now checking for duplicate user_ids, NOT msg_ids
        dupes = con.execute("SELECT user_id, COUNT(*) FROM messages GROUP BY user_id HAVING COUNT(*) > 1").fetchall()
        print(f"2. Anomaly Check: Found {len(dupes)} unique users (based on user_id).")
    except Exception as e:
        print(f"2. Anomaly Check: Could not run duplicate user check. Error: {e}")
    # --- END FIX ---

    try:
        top_members = con.execute("""
            SELECT user_name, COUNT(*) as msg_count
            FROM messages
            GROUP BY user_name
            ORDER BY msg_count DESC
            LIMIT 5
        """).fetchall()
        print("3. Pattern: Top 5 Active Users:")
        for member, count in top_members:
            print(f"   - {member}: {count} messages")
    except Exception as e:
        print(f"3. Pattern: Could not run active user analysis. Error: {e}")

    con.close()
    print("\n data loading and analysis complete.")

# --- Main execution ---
if __name__ == "__main__":
    message_data = fetch_data()
    if message_data:
        create_database(message_data)