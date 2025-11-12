import duckdb
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import logging
import os
from typing import List, Tuple

# --- 1. SET UP PROFESSIONAL LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
DB_FILE = "data.db"
INDEX_FILE = "index.faiss"
MODEL_NAME = 'all-MiniLM-L6-v2'
# Use a batch size for encoding, good for memory efficiency
EMBEDDING_BATCH_SIZE = 64 

def get_data_for_indexing() -> List[Tuple[str, str, str]]:
    """
    Fetches all data needed for indexing from the database.
    We'll get rowid, user_name, and message.
    """
    logging.info(f"Connecting to {DB_FILE} to fetch messages...")
    if not os.path.exists(DB_FILE):
        logging.error(f"Database file not found: {DB_FILE}")
        logging.error("Please run 'python data_loader.py' first.")
        return []
        
    try:
        with duckdb.connect(DB_FILE, read_only=True) as con:
            # Get the rowid, which is crucial for mapping
            # FAISS index back to the database row.
            messages = con.execute(
                "SELECT rowid, user_name, message FROM messages"
            ).fetchall()
        
        logging.info(f"Successfully fetched {len(messages)} messages from database.")
        return messages
    except Exception as e:
        logging.error(f"Failed to read from DuckDB: {e}")
        return []

def create_index():
    """
    Creates a robust FAISS index from the messages in DuckDB.
    """
    messages_data = get_data_for_indexing()
    if not messages_data:
        logging.error("No data to index. Exiting.")
        return

    try:
        logging.info(f"Loading embedding model '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        logging.error(f"Failed to load SentenceTransformer model: {e}")
        return

    # Create the text we'll embed. We'll keep the rowids separate for mapping.
    # We combine user_name and message for better contextual search
    message_texts = [f"{user}: {text}" for rowid, user, text in messages_data]
    
    logging.info(f"Creating embeddings for {len(message_texts)} messages...")
    
    try:
        embeddings = model.encode(
            message_texts, 
            batch_size=EMBEDDING_BATCH_SIZE, 
            show_progress_bar=True
        )
    except Exception as e:
        logging.error(f"Failed during model.encode: {e}")
        return

    # FAISS requires float32
    embeddings = np.array(embeddings).astype('float32')

    # Get the vector dimension from the first embedding
    dimension = embeddings.shape[1]
    
    logging.info(f"Creating FAISS Index (Dimension: {dimension})...")
    # Using IndexFlatL2 (brute-force) because 3.3k items is tiny.
    # This is an "engineering trade-off": it's faster and more accurate
    # than a complex index at this small scale.
    index = faiss.IndexFlatL2(dimension)
    
    # Add all our vectors to the index
    index.add(embeddings)
    
    logging.info(f"Index created. Total vectors: {index.ntotal}")

    # Save the index to our disk
    try:
        logging.info(f"Saving index to {INDEX_FILE}...")
        faiss.write_index(index, INDEX_FILE)
    except Exception as e:
        logging.error(f"Failed to write index file: {e}")
        return

    logging.info(f"\n--- Robust index creation complete! ---")
    logging.info(f"File '{INDEX_FILE}' is ready.")

if __name__ == "__main__":
    create_index()