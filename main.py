import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import os
from datetime import datetime
import duckdb

from agent import run_agent
from tools import FAISS_INDEX, DB_FILE 

# --- 1. PRODUCTION LOGGING (CONSOLE ONLY - SIMPLE & CLEAN) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)


# --- 2. CREATE THE FASTAPI APP ---
app = FastAPI(
    title="Proactive Q&A Agent API",
    description="Production-ready agentic RAG system with intelligent routing between SQL and vector search.",
    version="1.0.0"
)


# --- 3. DEFINE THE REQUEST & RESPONSE MODELS ---
class QueryRequest(BaseModel):
    question: str


# --- 4. HEALTH CHECK ENDPOINT ---
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Production health check endpoint for monitoring.
    
    Validates:
    - FAISS vector index is loaded
    - DuckDB database is accessible
    - Environment variables are configured
    """
    health_status = {
        "status": "ok",
        "components": {},
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

    try:
        # Check FAISS index
        if FAISS_INDEX is None:
            health_status["status"] = "degraded"
            health_status["components"]["faiss_index"] = "not_loaded"
            logger.error("Health check: FAISS index not loaded")
        else:
            health_status["components"]["faiss_index"] = {
                "status": "ok",
                "vectors": FAISS_INDEX.ntotal
            }

        # Check database connection
        try:
            with duckdb.connect(DB_FILE, read_only=True) as con:
                result = con.execute("SELECT COUNT(*) FROM messages").fetchone()
                health_status["components"]["database"] = {
                    "status": "ok",
                    "message_count": result[0] if result else 0
                }
        except Exception as db_error:
            health_status["status"] = "error"
            health_status["components"]["database"] = {
                "status": "error",
                "error": str(db_error)
            }
            logger.error(f"Health check: Database error - {db_error}")

        # Check environment variables
        if not os.getenv("GEMINI_API_KEY"):
            health_status["status"] = "degraded"
            health_status["components"]["gemini_api"] = "key_missing"
            logger.warning("Health check: GEMINI_API_KEY not set")
        else:
            health_status["components"]["gemini_api"] = "configured"

        # Return appropriate status code
        if health_status["status"] == "ok":
            logger.info("Health check successful - all systems operational")
            return JSONResponse(status_code=200, content=health_status)
        elif health_status["status"] == "degraded":
            logger.warning("Health check degraded - some components have issues")
            return JSONResponse(status_code=200, content=health_status)
        else:
            logger.error("Health check failed - critical errors detected")
            return JSONResponse(status_code=503, content=health_status)

    except Exception as e:
        logger.error(f"Health check failed with exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# --- 5. ROOT HEALTH CHECK ---
@app.get("/", tags=["Health"])
async def root_health_check():
    """Simple health check at root endpoint."""
    logger.info("Root health check accessed")
    return {"status": "ok", "message": "Agent is live and ready."}


# --- 6. MAIN AGENT ENDPOINT ---
@app.post("/ask", tags=["Agent"])
async def ask_agent(request: QueryRequest):
    """
    Main endpoint to query the agent.
    
    Intelligently routes queries to SQL or vector search,
    synthesizes responses, and provides proactive recommendations.
    """
    try:
        logger.info(f"Received query: {request.question}")
        response = run_agent(request.question)

        # Log the tool used
        trace = response.get("reasoning_trace", [])
        tool_used = "unknown"
        if "Fact_Seeker" in str(trace):
            tool_used = "Fact_Seeker (SQL)"
        elif "Context_Seeker" in str(trace):
            tool_used = "Context_Seeker (Vector)"
        
        logger.info(f"Query processed successfully. Tool used: {tool_used}")
        return response
        
    except Exception as e:
        logger.error(f"Error during /ask endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "answer": "I'm sorry, I encountered a critical server error.",
                "evidence": [],
                "proactive_recommendation": None,
                "reasoning_trace": [f"Server Error: {str(e)}"]
            }
        )


# --- 7. STARTUP EVENT ---
@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("=" * 50)
    logger.info("Proactive Q&A Agent API Starting")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 50)


# --- 8. MAKE IT RUNNABLE ---
if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
