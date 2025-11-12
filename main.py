import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import logging

# Import our agent's "brain"
from agent import run_agent

# --- 1. SET UP PROFESSIONAL LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- 2. CREATE THE FASTAPI APP ---
app = FastAPI(
    title="Proactive Q&A Agent",
    description="An agentic system that answers questions and provides proactive recommendations.",
    version="1.0.0"
)

# --- 3. DEFINE THE REQUEST & RESPONSE MODELS ---
# This tells FastAPI what the incoming JSON should look like
class QueryRequest(BaseModel):
    question: str
    
# We don't need a response model, FastAPI will auto-handle our agent's dict

# --- 4. CREATE THE API ENDPOINTS ---
@app.get("/", tags=["Health"])
async def health_check():
    """A simple health check to confirm the API is live."""
    logging.info("Health check successful.")
    return {"status": "ok", "message": "Agent is live and ready."}

@app.post("/ask", tags=["Agent"])
async def ask_agent(request: QueryRequest):
    """
    The main endpoint to ask the agent a question.
    """
    try:
        # This is it! We just call our agent's main function.
        response = run_agent(request.question)
        return response
    except Exception as e:
        # Robust error handling for the API
        logging.error(f"Error during /ask endpoint: {e}")
        return {
            "answer": "I'm sorry, I encountered a critical server error.",
            "evidence": [],
            "proactive_recommendation": None,
            "reasoning_trace": [f"Server Error: {e}"]
        }

# --- 5. MAKE IT RUNNABLE ---
if __name__ == "__main__":
    logging.info("Starting FastAPI server...")
    # We use port 8080, which is standard for deployments
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)