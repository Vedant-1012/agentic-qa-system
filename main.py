from fastapi import FastAPI
import uvicorn

# Create the FastAPI app instance
app = FastAPI(title="Proactive Q&A Agent")


# Define a simple "health check" endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Checks if the API is running."""
    return {"status": "ok"}


# This block allows you to run the app with `python main.py`
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)