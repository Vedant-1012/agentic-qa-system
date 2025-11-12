import requests
import json
import logging
from typing import List, Dict

# --- 1. SET UP PROFESSIONAL LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
EVAL_FILE = "eval.json"
# We test our local server running on port 8080
API_URL = "http://127.0.0.1:8080/ask" 

def load_eval_set() -> List[Dict]:
    """Loads the golden evaluation set from JSON."""
    try:
        with open(EVAL_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"FATAL: Evaluation file not found: {EVAL_FILE}")
        return None
    except json.JSONDecodeError:
        logging.error(f"FATAL: Could not parse {EVAL_FILE}. Check for syntax errors.")
        return None

def run_evaluation():
    """
    Runs the full evaluation against the live API.
    """
    logging.info("--- Starting Agent Evaluation ---")
    
    eval_set = load_eval_set()
    if not eval_set:
        return

    logging.info(f"Loaded {len(eval_set)} test questions.")
    
    score = 0
    total = len(eval_set)
    
    for i, test in enumerate(eval_set):
        question = test['question']
        golden_answer = test['golden_answer']
        
        logging.info(f"\n--- Test {i+1}/{total} ---")
        logging.info(f"QUESTION: {question}")
        logging.info(f"EXPECTED: {golden_answer}")
        
        try:
            # 1. Call our live API
            response = requests.post(API_URL, json={"question": question}, timeout=20)
            response.raise_for_status()
            
            response_data = response.json()
            agent_answer = response_data.get("answer")
            
            logging.info(f"AGENT:    {agent_answer}")
            
            # 2. Check the answer (simple "contains" check)
            if golden_answer.lower() in agent_answer.lower():
                logging.info("RESULT: PASS")
                score += 1
            else:
                logging.info("RESULT: FAIL")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            logging.info("RESULT: ERROR (Skipping)")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            logging.info("RESULT: ERROR (Skipping)")

    # --- 3. Show Final Score ---
    logging.info("\n--- Evaluation Complete ---")
    if total > 0:
        pass_rate = (score / total) * 100
        logging.info(f"FINAL SCORE: {score}/{total} ({pass_rate:.2f}%)")
    else:
        logging.info("No tests were run.")

if __name__ == "__main__":
    # Make sure your main.py server is running in another terminal!
    logging.info(f"Connecting to API server at {API_URL}...")
    run_evaluation()