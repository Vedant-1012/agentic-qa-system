# import duckdb
# import faiss
# from sentence_transformers import SentenceTransformer
# import numpy as np
# import logging
# import os
# from typing import Optional, List, Dict, Any

# # --- 1. SET UP PROFESSIONAL LOGGING ---
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# # --- Configuration ---
# DB_FILE = "data.db"
# INDEX_FILE = "index.faiss"
# MODEL_NAME = 'all-MiniLM-L6-v2'
# # --- END FIX ---


# # --- 2. ROBUST PRE-LOADING ---
# try:
#     if not os.path.exists(DB_FILE):
#         logging.error(f"Database file not found: {DB_FILE}. Run data_loader.py.")
#         raise FileNotFoundError
#     if not os.path.exists(INDEX_FILE):
#         logging.error(f"Index file not found: {INDEX_FILE}. Run index.py.")
#         raise FileNotFoundError

#     logging.info("Pre-loading embedding model...")
#     EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME)
#     logging.info("Pre-loading FAISS index...")
#     FAISS_INDEX = faiss.read_index(INDEX_FILE)
    
#     with duckdb.connect(DB_FILE, read_only=True) as con:
#         ALL_USERS = con.execute("SELECT DISTINCT user_name FROM messages").fetchall()
#         ALL_USERS = [user[0] for user in ALL_USERS]
        
#     logging.info(f"Models loaded. Found {len(ALL_USERS)} unique users.")

# except Exception as e:
#     logging.error(f"FATAL ERROR: Could not load models. {e}")
#     exit(1)


# # --- TOOL 1: Fact Seeker (No changes) ---
# def seek_facts(question: str) -> Optional[Dict[str, Any]]:
#     """
#     Uses SQL to find specific, factual answers from the database.
#     """
#     logging.info(f"[Tool 1: Fact_Seeker] Received query: '{question}'")
    
#     with duckdb.connect(DB_FILE, read_only=True) as con:
        
#         # --- Skill 1: Find Most Active User ---
#         if "most active" in question.lower():
#             try:
#                 result = con.execute("""
#                     SELECT user_name, COUNT(*) as msg_count
#                     FROM messages
#                     GROUP BY user_name
#                     ORDER BY msg_count DESC
#                     LIMIT 1
#                 """).fetchone()
                
#                 if result:
#                     user_name, count = result
#                     return {
#                         "fact": "most_active_user",
#                         "answer": user_name,
#                         "context": f"{user_name} is the most active user with {count} messages."
#                     }
#             except Exception as e:
#                 logging.error(f"[Fact_Seeker] Error finding active user: {e}")
                
#         # --- Skill 2: Find Message Count for a User ---
#         if "how many messages" in question.lower():
#             try:
#                 found_user = None
#                 for user_name in ALL_USERS:
#                     if user_name.lower() in question.lower():
#                         found_user = user_name
#                         break
                
#                 if found_user:
#                     count = con.execute(
#                         "SELECT COUNT(*) FROM messages WHERE user_name = ?", 
#                         [found_user]
#                     ).fetchone()[0]
                    
#                     return {
#                         "fact": "user_message_count",
#                         "answer": str(count),
#                         "context": f"{found_user} has sent {count} messages."
#                     }
#             except Exception as e:
#                 logging.error(f"[Fact_Seeker] Error finding message count: {e}")

#     logging.info("[Tool 1: Fact_Seeker] No specific fact found.")
#     return None

# # --- TOOL 2: Context Seeker (With Timestamps) ---
# def seek_context(question: str, top_k: int = 3) -> Optional[List[Dict[str, Any]]]:
#     """
#     Uses FAISS vector search to find the most relevant messages.
#     Returns a list of structured dictionaries including timestamps.
#     """
#     logging.info(f"[Tool 2: Context_Seeker] Received query: '{question}'")
    
#     try:
#         question_embedding = EMBEDDING_MODEL.encode([question], convert_to_numpy=True).astype('float32')
#         D, I = FAISS_INDEX.search(question_embedding, top_k)
#         message_indices = [int(i) for i in I[0]] 

#         with duckdb.connect(DB_FILE, read_only=True) as con:
#             indices_str = ', '.join(map(str, message_indices))
            
#             results = con.execute(
#                 f"SELECT rowid, user_name, message, timestamp FROM messages WHERE rowid IN ({indices_str})"
#             ).fetchall()
        
#         # Re-order results to match FAISS relevance
#         results_map = {rowid: (user, msg, ts) for rowid, user, msg, ts in results}
        
#         ordered_results = []
#         for rowid in message_indices:
#             if rowid in results_map:
#                 user, msg, ts = results_map[rowid]
#                 ordered_results.append({
#                     "user_name": user,
#                     "message": msg,
#                     "timestamp": str(ts), # Convert timestamp to string
#                     "rowid": rowid
#                 })
                
#         logging.info(f"[Context_Seeker] Found {len(ordered_results)} relevant contexts.")
#         return ordered_results
            
#     except Exception as e:
#         logging.error(f"[Context_Seeker] Error searching index: {e}")
#         return None

# # --- Main Test Block (Updated) ---
# def run_tests():
#     """Runs tests on all tools in this file."""
#     logging.info("--- (Test) Tool 1: Fact_Seeker ---")
    
#     q1 = "Who is the most active user?"
#     a1 = seek_facts(q1)
#     logging.info(f"Q: {q1}\nA: {a1}")
    
#     q2 = "How many messages did Thiago Monteiro send?"
#     a2 = seek_facts(q2)
#     logging.info(f"Q: {q2}\nA: {a2}")
    
#     logging.info("\n--- (Test) Tool 2: Context_Seeker ---")
    
#     q3 = "What does Lily O'Sullivan like?"
#     a3 = seek_context(q3)
#     import json # for pretty printing
#     logging.info(f"Q: {q3}\nContext Found:\n{json.dumps(a3, indent=2)}")

# if __name__ == "__main__":
#     run_tests()


import duckdb
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import logging # <-- Keep this
import os
from typing import Optional, List, Dict, Any

# --- 1. SET UP PROFESSIONAL LOGGING ---
# We removed basicConfig and added this:
logger = logging.getLogger(__name__)
# ---

# --- Configuration ---
DB_FILE = "data.db"
INDEX_FILE = "index.faiss"
MODEL_NAME = 'all-MiniLM-L6-v2'


# --- 2. ROBUST PRE-LOADING ---
try:
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file not found: {DB_FILE}. Run data_loader.py.")
        raise FileNotFoundError
    if not os.path.exists(INDEX_FILE):
        logger.error(f"Index file not found: {INDEX_FILE}. Run index.py.")
        raise FileNotFoundError

    logger.info("Pre-loading embedding model...")
    EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME)
    logger.info("Pre-loading FAISS index...")
    FAISS_INDEX = faiss.read_index(INDEX_FILE)
    
    with duckdb.connect(DB_FILE, read_only=True) as con:
        ALL_USERS = con.execute("SELECT DISTINCT user_name FROM messages").fetchall()
        ALL_USERS = [user[0] for user in ALL_USERS]
        
    logger.info(f"Models loaded. Found {len(ALL_USERS)} unique users.")

except Exception as e:
    logger.error(f"FATAL ERROR: Could not load models. {e}")
    exit(1)


# --- TOOL 1: Fact Seeker (No changes) ---
def seek_facts(question: str) -> Optional[Dict[str, Any]]:
    """
    Uses SQL to find specific, factual answers from the database.
    """
    logger.info(f"[Tool 1: Fact_Seeker] Received query: '{question}'")
    
    with duckdb.connect(DB_FILE, read_only=True) as con:
        
        # --- Skill 1: Find Most Active User ---
        if "most active" in question.lower():
            try:
                result = con.execute("""
                    SELECT user_name, COUNT(*) as msg_count
                    FROM messages
                    GROUP BY user_name
                    ORDER BY msg_count DESC
                    LIMIT 1
                """).fetchone()
                
                if result:
                    user_name, count = result
                    return {
                        "fact": "most_active_user",
                        "answer": user_name,
                        "context": f"{user_name} is the most active user with {count} messages."
                    }
            except Exception as e:
                logger.error(f"[Fact_Seeker] Error finding active user: {e}")
                
        # --- Skill 2: Find Message Count for a User ---
        if "how many messages" in question.lower():
            try:
                found_user = None
                for user_name in ALL_USERS:
                    if user_name.lower() in question.lower():
                        found_user = user_name
                        break
                
                if found_user:
                    count = con.execute(
                        "SELECT COUNT(*) FROM messages WHERE user_name = ?", 
                        [found_user]
                    ).fetchone()[0]
                    
                    return {
                        "fact": "user_message_count",
                        "answer": str(count),
                        "context": f"{found_user} has sent {count} messages."
                    }
            except Exception as e:
                logger.error(f"[Fact_Seeker] Error finding message count: {e}")

    logger.info("[Tool 1: Fact_Seeker] No specific fact found.")
    return None

# --- TOOL 2: Context Seeker (With Timestamps) ---
def seek_context(question: str, top_k: int = 3) -> Optional[List[Dict[str, Any]]]:
    """
    Uses FAISS vector search to find the most relevant messages.
    Returns a list of structured dictionaries including timestamps.
    """
    logger.info(f"[Tool 2: Context_Seeker] Received query: '{question}'")
    
    try:
        question_embedding = EMBEDDING_MODEL.encode([question], convert_to_numpy=True).astype('float32')
        D, I = FAISS_INDEX.search(question_embedding, top_k)
        message_indices = [int(i) for i in I[0]] 

        with duckdb.connect(DB_FILE, read_only=True) as con:
            indices_str = ', '.join(map(str, message_indices))
            
            results = con.execute(
                f"SELECT rowid, user_name, message, timestamp FROM messages WHERE rowid IN ({indices_str})"
            ).fetchall()
        
        # Re-order results to match FAISS relevance
        results_map = {rowid: (user, msg, ts) for rowid, user, msg, ts in results}
        
        ordered_results = []
        for rowid in message_indices:
            if rowid in results_map:
                user, msg, ts = results_map[rowid]
                ordered_results.append({
                    "user_name": user,
                    "message": msg,
                    "timestamp": str(ts), # Convert timestamp to string
                    "rowid": rowid
                })
                
        logger.info(f"[Context_Seeker] Found {len(ordered_results)} relevant contexts.")
        return ordered_results
            
    except Exception as e:
        logger.error(f"[Context_Seeker] Error searching index: {e}")
        return None

# --- Main Test Block (Updated) ---
def run_tests():
    """Runs tests on all tools in this file."""
    logger.info("--- (Test) Tool 1: Fact_Seeker ---")
    
    q1 = "Who is the most active user?"
    a1 = seek_facts(q1)
    logger.info(f"Q: {q1}\nA: {a1}")
    
    q2 = "How many messages did Thiago Monteiro send?"
    a2 = seek_facts(q2)
    logger.info(f"Q: {q2}\nA: {a2}")
    
    logger.info("\n--- (Test) Tool 2: Context_Seeker ---")
    
    q3 = "What does Lily O'Sullivan like?"
    a3 = seek_context(q3)
    import json # for pretty printing
    logger.info(f"Q: {q3}\nContext Found:\n{json.dumps(a3, indent=2)}")

if __name__ == "__main__":
    run_tests()