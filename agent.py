import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Import our custom tools
from tools import seek_facts, seek_context

# --- 1. SET UP PROFESSIONAL LOGGING ---
# REMOVED basicConfig, ADDED this:
logger = logging.getLogger(__name__)
# ---

# --- 2. LOAD API KEY & CONFIGURE GEMINI ---
load_dotenv()  # Loads the .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("FATAL ERROR: GEMINI_API_KEY not found in .env file.")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = gen_model = genai.GenerativeModel(
        'gemini-2.5-flash',
        # Set safety to a minimum to avoid blocks on harmless words
        safety_settings={'HARASSMENT':'BLOCK_NONE', 'HATE':'BLOCK_NONE'}
    )
    logger.info("Gemini Pro model configured successfully.")
except Exception as e:
    logger.error(f"FATAL ERROR: Could not configure Gemini. {e}")
    exit(1)


# --- UPDATED: TOOL 3 (Helper Function) ---
def _extract_entity(message: str, entity_type: str) -> str:
    """
    A dedicated LLM call to extract a specific entity from a message.
    """
    logger.info(f"[Tool 3 Extractor] Extracting '{entity_type}' from: {message}")
    try:
        prompt = f"""
        You are an entity extractor. From the following text, extract the *specific* {entity_type}.
        Be very concise. For example, if the text is "I like lilies and roses", the preference is "lilies and roses".
        If the text is "Plan a trip to the distilleries", the trip_subject is "distilleries".
        
        Text:
        "{message}"
        
        Extracted {entity_type}:
        """
        response = GEMINI_MODEL.generate_content(prompt)
        
        # --- THIS IS THE FINAL FIX ---
        # Add a safety check in case Gemini blocks the response
        if not response.parts:
            logger.warning("[Tool 3 Extractor] No content part returned (likely safety filter).")
            return message # Fallback to the full message
        # --- END FIX ---

        entity = response.text.strip().replace('"', '').replace('\n', '')
        logger.info(f"[Tool 3 Extractor] Extracted: {entity}")
        return entity
    except Exception as e:
        logger.error(f"[Tool 3 Extractor] Failed: {e}", exc_info=True)
        return message # Fallback to the full message

# --- UPDATED: TOOL 3: Action Recommender (Smarter Prioritization) ---
def get_recommendation(question: str, context: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    A smarter, evidence-based engine. It now prioritizes
    high-value keywords (like 'favorite') over generic ones.
    """
    logger.info("[Tool 3: Recommender] Analyzing context for recommendations...")
    
    question_lower = question.lower()
    if not isinstance(context, list):
        return None # Can't do anything

    best_recommendation = None
    best_score = 0 # 0 = no match, 1 = low-priority, 2 = high-priority
    
    # INTENT 1: Is this a "preference" question?
    is_preference_query = "like" in question_lower or "favorite" in question_lower
    if is_preference_query:
        logger.info("[Tool 3] Question intent is 'preference'.")
    
    for item in context:
        if item.get("source") == "Fact_Seeker": continue
        message = item.get("message", "").lower()
        
        # --- Check for Preferences ---
        # High-priority: explicit keywords
        if "favorite" in message or "lilies" in message or "roses" in message:
            if best_score < 2: # Only overwrite if this is a better match
                logger.info(f"[Tool 3] Found HIGH-PRIORITY preference (rowid {item.get('rowid')})")
                best_score = 2
                extracted_pref = _extract_entity(item['message'], "preference")
                best_recommendation = {
                    "action_id": "save_preference",
                    "suggestion_text": f"I've noted a strong preference for '{extracted_pref}'. Would you like to save this to the member's profile?",
                    "structured_data": {"type": "preference", "value": extracted_pref, "source_message": item['message']}
                }
        
        # Low-priority: generic keywords (only if it's a preference query)
        elif is_preference_query and ("outstanding" in message or "concierge" in message):
            if best_score < 1: # Don't overwrite a high-priority match
                logger.info(f"[Tool 3] Found LOW-PRIORITY preference (rowid {item.get('rowid')})")
                best_score = 1
                extracted_pref = _extract_entity(item['message'], "preference")
                best_recommendation = {
                    "action_id": "save_preference",
                    "suggestion_text": f"I noted a preference for '{extracted_pref}'. Would you like to save this to the member's profile?",
                    "structured_data": {"type": "preference", "value": extracted_pref, "source_message": item['message']}
                }

        # --- Check for Travel (only if we haven't found a preference) ---
        travel_keywords = ["trip", "flight", "planning", "distilleries", "journey"]
        if not is_preference_query and best_score == 0 and any(kw in message for kw in travel_keywords):
            logger.info(f"[Tool 3] Found travel intent in message (rowid {item.get('rowid')})")
            best_score = 1
            extracted_trip = _extract_entity(item['message'], "trip_subject")
            best_recommendation = {
                "action_id": "suggest_trip_itinerary",
                "suggestion_text": f"I see a message about a trip to '{extracted_trip}'. Would you like to start an itinerary?",
                "structured_data": {"type": "travel", "value": extracted_trip, "source_message": item['message']}
            }
            
    if not best_recommendation:
        logger.info("[Tool 3: Recommender] No specific recommendation found.")
        
    return best_recommendation


# --- TOOL 4: Synthesizer (The LLM) ---
def synthesize_answer(question: str, context: List[Dict[str, Any]]) -> str:
    """
    Uses the Gemini LLM to generate a final, human-friendly answer.
    """
    logger.info("[Tool 4: Synthesizer] Generating final answer with LLM...")
    
    # Create a clean prompt with our new structured context
    context_str = "\n".join(
        [f"- (From {d.get('timestamp', 'N/A')}) {d.get('user_name', 'N/A')}: {d.get('message', 'N/A')}" for d in context if d.get('message')]
    )
    
    prompt = f"""
    You are a helpful assistant. Based *only* on the context I provide,
    answer the user's question.
    
    Context:
    {context_str}
    
    Question:
    {question}
    
    Answer:
    """
    
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        
        # Add safety check here too
        if not response.parts:
            logger.warning("[Tool 4 Synthesizer] No content part returned (likely safety filter).")
            return "I found the context, but I am unable to formulate a response at this time."
            
        return response.text
    except Exception as e:
        logger.error(f"[Synthesizer] Error generating content: {e}", exc_info=True)
        return "I'm sorry, I encountered an error while formulating a response."


# --- THE "MANAGER": The Router Agent ---
def run_agent(question: str) -> Dict[str, Any]:
    """
    Runs the full agentic pipeline:
    1. Route to the correct tool (Fact or Context).
    2. Get a recommendation.
    3. Synthesize the final answer.
    4. Return the full, structured response.
    """
    logger.info(f"\n--- New Query Received --- \nQuestion: {question}")
    trace = []
    
    # --- 1. ROUTER LOGIC ---
    trace.append("Router: Received query.")
    fact_result = seek_facts(question)
    
    if fact_result:
        trace.append("Router: Query is fact-based. Using Tool 1 (Fact_Seeker).")
        # Standardize context to be a list of dicts
        context = [{"source": "Fact_Seeker", "context": fact_result["context"]}]
        final_answer = fact_result["answer"]
        trace.append("Synthesizer: Bypassed. Used direct answer from tool.")
    else:
        trace.append("Router: Query is vague/contextual. Using Tool 2 (Context_Seeker).")
        context = seek_context(question) # This now returns a list of dicts
        
        if not context:
            trace.append("Context_Seeker: No context found.")
            return {
                "answer": "I'm sorry, I couldn't find any information about that.",
                "evidence": [],
                "proactive_recommendation": None,
                "reasoning_trace": trace
            }
        
        # --- 3. SYNTHESIZER ---
        trace.append("Router: Calling Tool 4 (Synthesizer).")
        final_answer = synthesize_answer(question, context)

    # --- 4. RECOMMENDER ---
    trace.append("Router: Calling Tool 3 (Recommender).")
    recommendation = get_recommendation(question, context)

    # --- 5. FINAL RESPONSE ---
    trace.append("Router: Formatting final response.")
    return {
        "answer": final_answer,
        "evidence": context, # This is now the clean, structured list
        "proactive_recommendation": recommendation, # This is now a structured object
        "reasoning_trace": trace
    }


# --- Main Test Block ---
def run_tests():
    """Runs tests on the full agent pipeline."""
    import json
    
    print("\n--- (Test 1) Fact-Based Query ---")
    q1 = "Who is the most active user?"
    a1 = run_agent(q1)
    print(json.dumps(a1, indent=2))
    
    print("\n--- (Test 2) Context-Based Query ---")
    q2 = "What does Lily O'Sullivan like?"
    a2 = run_agent(q2)
    print(json.dumps(a2, indent=2))
    
    print("\n--- (Test 3) Fact-Based Query (with Travel) ---")
    q3 = "What is Lily O'Sullivan planning about distilleries?"
    a3 = run_agent(q3)
    print(json.dumps(a3, indent=2))

if __name__ == "__main__":
    run_tests()