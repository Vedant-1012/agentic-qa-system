import requests
import duckdb
import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional

# --- 1. SET UP PROFESSIONAL LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
API_URL = "https://november7-730026606190.europe-west1.run.app/messages/"
DB_FILE = "data.db"
BATCH_SIZE = 500  # How many messages to fetch per API call

# --- 2. ROBUST, PAGINATED FETCHER ---
def fetch_data() -> Optional[List[Dict[str, Any]]]:
    """
    Fetches all messages from the API using robust pagination.
    """
    logging.info(f"Starting data fetch from {API_URL}")
    
    all_messages = []
    skip = 0
    
    while True:
        try:
            logging.info(f"Fetching batch: skip={skip}, limit={BATCH_SIZE}")
            response = requests.get(
                API_URL, 
                params={"skip": skip, "limit": BATCH_SIZE},
                timeout=10  # Set a timeout
            )
            response.raise_for_status()  # Check for HTTP errors (4xx, 5xx)
            
            data = response.json()
            messages = data.get("items")
            
            if messages is None:
                logging.error("API Error: 'items' key not found in response.")
                return None
            
            if not messages:
                # This is the normal exit condition
                logging.info("No more messages found. Pagination complete.")
                break
            
            all_messages.extend(messages)
            skip += BATCH_SIZE 

        # --- 3. SPECIFIC ERROR HANDLING ---
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Network Error: Could not connect to API. {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout Error: The request to the API timed out. {e}")
            return None
        except requests.exceptions.JSONDecodeError as e:
            logging.error(f"JSON Error: Could not decode response from API. {e}")
            return None
        except requests.exceptions.RequestException as e:
            if e.response:
                if e.response.status_code == 402:
                    logging.warning("API returned 402 Payment Required. Stopping fetch.")
                    logging.warning("This is a known limit. Using the data we have.")
                    break 
                if e.response.status_code == 404:
                    logging.info("API returned 404 Not Found. This means we've fetched all data.")
                    break
            
            logging.error(f"API Error: {e}") 
            return None

    logging.info(f"Success! Fetched a total of {len(all_messages)} messages.")
    return all_messages

# --- 4. EFFICIENT BATCH INSERT ---
def create_database(messages: List[Dict[str, Any]]):
    """
    Creates a DuckDB database and table using efficient batch insertion.
    """
    if not messages:
        logging.warning("No messages to load. Exiting.")
        return

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        logging.info(f"Removed old {DB_FILE}.")

    logging.info(f"Creating new database: {DB_FILE}")

    df = pd.DataFrame(messages)
    
    # --- THIS IS THE FIX ---
    # Treat timestamp as a string to handle timezone info gracefully.
    df = df.astype({
        'user_id': 'string',
        'user_name': 'string',
        'message': 'string',
        'timestamp': 'string' # Was 'datetime64[ns]'
    })
    # --- END FIX ---

    with duckdb.connect(DB_FILE) as con:
        con.register('messages_df', df)
        con.execute("CREATE TABLE messages AS SELECT * FROM messages_df")
        
        logging.info(f"Successfully inserted {len(df)} messages into 'messages' table.")
        
        logging.info("--- Bonus 2: Data Insights (from DB) ---")
        
        total = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        logging.info(f"1. Total messages analyzed: {total}")

        try:
            users = con.execute("SELECT COUNT(DISTINCT user_id) FROM messages").fetchone()[0]
            logging.info(f"2. Analysis: Found {users} unique users.")
        except Exception as e:
            logging.error(f"2. Analysis: Could not run user check. {e}")

        try:
            top_members = con.execute("""
                SELECT user_name, COUNT(*) as msg_count
                FROM messages
                GROUP BY user_name
                ORDER BY msg_count DESC
                LIMIT 5
            """).fetchall()
            
            logging.info("3. Pattern: Top 5 Active Users:")
            for member, count in top_members:
                logging.info(f"   - {member}: {count} messages")
        except Exception as e:
            logging.error(f"3. Pattern: Could not run active user analysis. {e}")

    logging.info("\nData loading and analysis complete.")

# --- Main execution ---
if __name__ == "__main__":
    message_data = fetch_data()
    if message_data:
        create_database(message_data)