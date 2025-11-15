import gradio as gr
import requests
import json
import logging
import os # Make sure os is imported
from datetime import datetime # Make sure datetime is imported

# --- 1. SET UP PROFESSIONAL LOGGING ---
# This will inherit the configuration from main.py
logger = logging.getLogger(__name__)
# ---

# --- Configuration ---
# We use an env var for the API URL to make it flexible
# Fallback to localhost if not set
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/ask")
logger.info(f"Connecting Gradio Demo to API Server: {API_URL}")


def run_agent_demo(question):
    """
    Executes the agent query with professional error handling.
    
    Args:
        question (str): User's natural language query
        
    Returns:
        dict: Gradio component updates for all UI elements
    """
    logger.info(f"[Query] Received: {question}")
    
    # --- PRO-POLISH: Add Loading State ---
    # This yields a temporary value to show the user it's working
    yield {
        output_answer: gr.update(value="⏳ Processing query...", visible=True),
        output_raw_json: gr.update(value=None, visible=False),
        output_recommendation_group: gr.update(visible=False),
        output_feedback_status: gr.update(value=""), # Clear old status
    }
    
    # Validate input
    if not question or not question.strip():
        yield {
            output_answer: gr.update(value="Please enter a valid question.", visible=True),
        }
        return

    try:
        # Call API with timeout
        response = requests.post(
            API_URL, 
            json={"question": question}, 
            timeout=20
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"[API] Response received successfully")
        
        # Extract response components
        answer = data.get("answer", "No answer available.")
        pretty_json = json.dumps(data, indent=2)
        recommendation = data.get("proactive_recommendation")
        
        # Handle recommendation display
        if recommendation:
            logger.info("[Recommendation] Proactive suggestion detected")
            suggestion_text = recommendation.get("suggestion_text", "")
            action_id = recommendation.get("action_id", "")
            
            # Dynamic button text based on action type
            if "save_preference" in action_id:
                yes_button_text = "Save Preference"
                button_variant = "primary"
            elif "trip_itinerary" in action_id:
                yes_button_text = "Start Itinerary"
                button_variant = "secondary"
            else:
                yes_button_text = "Confirm"
                button_variant = "primary"
            
            yield {
                output_answer: gr.update(value=answer, visible=True),
                output_raw_json: gr.update(value=pretty_json, visible=True),
                output_recommendation_group: gr.update(visible=True),
                output_recommendation_text: gr.update(
                    value=suggestion_text, 
                    visible=True
                ),
                confirm_button: gr.update(
                    value=yes_button_text, 
                    variant=button_variant,
                    visible=True
                ),
                reject_button: gr.update(visible=True),
                output_feedback_status: gr.update(value="")
            }
        else:
            # Graceful fallback for queries without recommendations
            logger.info("[Recommendation] No actionable suggestion for this query")
            yield {
                output_answer: gr.update(value=answer, visible=True),
                output_raw_json: gr.update(value=pretty_json, visible=True),
                output_recommendation_group: gr.update(visible=True),
                output_recommendation_text: gr.update(
                    value="ℹ️ No actionable recommendation for this query. The agent focuses on preference-related suggestions.",
                    visible=True
                ),
                confirm_button: gr.update(visible=False),
                reject_button: gr.update(visible=False),
                output_feedback_status: gr.update(value="")
            }
            
    except requests.exceptions.Timeout:
        logger.error("[API] Request timeout")
        yield {
            output_answer: gr.update(
                value="Request timeout. Please ensure the API server is running and try again.",
                visible=True
            ),
            output_raw_json: gr.update(value=json.dumps({"error": "timeout"}, indent=2), visible=True),
            output_recommendation_group: gr.update(visible=False),
            output_recommendation_text: gr.update(value=""),
            output_feedback_status: gr.update(value="")
        }
    except requests.exceptions.ConnectionError:
        logger.error("[API] Connection failed")
        yield {
            output_answer: gr.update(
                value="Cannot connect to API server. Please start the server with: python main.py",
                visible=True
            ),
            output_raw_json: gr.update(value=json.dumps({"error": "connection_refused"}, indent=2), visible=True),
            output_recommendation_group: gr.update(visible=False),
            output_recommendation_text: gr.update(value=""),
            output_feedback_status: gr.update(value="")
        }
    except Exception as e:
        logger.error(f"[API] Unexpected error: {e}", exc_info=True) # Added exc_info=True
        yield {
            output_answer: gr.update(value=f"Error: {str(e)}", visible=True),
            output_raw_json: gr.update(value=json.dumps({"error": str(e)}, indent=2), visible=True),
            output_recommendation_group: gr.update(visible=False),
            output_recommendation_text: gr.update(value=""),
            output_feedback_status: gr.update(value="")
        }


def on_confirm_recommendation():
    """Handle user confirmation of recommendation."""
    logger.info("[Feedback] User confirmed recommendation")
    return gr.update(value="Action confirmed (demo mode - not persisted)", visible=True)


def on_reject_recommendation():
    """Handle user rejection of recommendation."""
    logger.info("[Feedback] User rejected recommendation")
    return gr.update(value="Action dismissed", visible=True)


# --- Custom CSS for Enterprise Design ---
custom_css = """
/* Main container */
#main-container {
    max-width: 1200px;
    margin: 0 auto;
}

/* Header styling - HIGH CONTRAST */
.header-title {
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    color: #f3f4f6 !important;
    margin-bottom: 0.75rem !important;
    letter-spacing: -0.025em !important;
}

.header-subtitle {
    font-size: 1.125rem !important;
    color: #d1d5db !important;
    line-height: 1.75 !important;
    font-weight: 400 !important;
}

/* Query input */
#query-input textarea {
    font-size: 1rem !important;
    color: #f9fafb !important;
    background-color: #1f2937 !important;
    border-color: #374151 !important;
}

#query-input textarea::placeholder {
    color: #9ca3af !important;
}

/* Agent response - HIGH CONTRAST */
.response-text {
    font-size: 1.125rem !important;
    line-height: 1.75 !important;
    color: #f3f4f6 !important;
    font-weight: 400 !important;
    padding: 1rem 0 !important;
}

/* Recommendation box - PROFESSIONAL DARK THEME */
.recommendation-container {
    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%) !important;
    border: 1px solid #3b82f6 !important;
    border-left: 4px solid #60a5fa !important;
    border-radius: 8px !important;
    padding: 1.5rem !important;
    margin-top: 1.5rem !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2) !important;
}

.recommendation-header {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #93c5fd !important;
    margin-bottom: 0.75rem !important;
}

.recommendation-text {
    font-size: 1.125rem !important;
    line-height: 1.75 !important;
    color: #f3f4f6 !important;
    font-weight: 500 !important;
    margin-bottom: 1rem !important;
}

/* Buttons - SHARP AND CLEAR */
.action-buttons {
    display: flex !important;
    gap: 0.75rem !important;
    margin-top: 1rem !important;
}

button.primary-action {
    background-color: #3b82f6 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 0.625rem 1.25rem !important;
    border-radius: 6px !important;
    border: none !important;
    font-size: 0.9375rem !important;
    transition: all 0.2s !important;
}

button.primary-action:hover {
    background-color: #2563eb !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
}

button.secondary-action {
    background-color: transparent !important;
    color: #d1d5db !important;
    font-weight: 500 !important;
    padding: 0.625rem 1.25rem !important;
    border-radius: 6px !important;
    border: 1px solid #4b5563 !important;
    font-size: 0.9375rem !important;
    transition: all 0.2s !important;
}

button.secondary-action:hover {
    background-color: #374151 !important;
    border-color: #6b7280 !important;
}

/* Status text - VISIBLE */
.status-text {
    font-size: 0.9375rem !important;
    color: #a5f3fc !important;
    font-weight: 500 !important;
    margin-top: 0.75rem !important;
    padding: 0.5rem !important;
    background-color: rgba(6, 182, 212, 0.1) !important;
    border-radius: 4px !important;
}

/* Example queries */
.example-queries button {
    background-color: #374151 !important;
    color: #d1d5db !important;
    border: 1px solid #4b5563 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 0.875rem !important;
    transition: all 0.2s !important;
}

.example-queries button:hover {
    background-color: #4b5563 !important;
    color: #f3f4f6 !important;
    border-color: #6b7280 !important;
}

/* Developer accordion */
.developer-view {
    margin-top: 2rem !important;
    border-top: 1px solid #374151 !important;
    padding-top: 1rem !important;
}

.developer-view summary {
    color: #9ca3af !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
}

.developer-view summary:hover {
    color: #d1d5db !important;
}
"""


# --- Build Enterprise-Grade Interface (FIXED THEME) ---
with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="slate"
    ).set(
        body_background_fill="#0f172a",
        body_text_color="#f3f4f6",
        block_background_fill="#1e293b",
        block_border_color="#334155",
        input_background_fill="#1f2937",
        button_primary_background_fill="#3b82f6",
        button_primary_text_color="#ffffff",
    ),
    css=custom_css,
    title="Proactive Q&A Agent"
) as demo:
    
    # Header
    with gr.Column(elem_id="main-container"):
        gr.Markdown(
            "# Proactive Q&A Agent",
            elem_classes=["header-title"]
        )
        gr.Markdown(
            "Production-ready agentic RAG system with intelligent routing between SQL and vector search. "
            "Ask a question to see factual accuracy, contextual understanding, and proactive recommendations.",
            elem_classes=["header-subtitle"]
        )
        
        # Query Input Section
        with gr.Row():
            with gr.Column(scale=4):
                input_question = gr.Textbox(
                    label="Query",
                    placeholder="Example: What kind of flowers does Lily like?",
                    lines=2,
                    elem_id="query-input"
                )
            with gr.Column(scale=1):
                submit_button = gr.Button(
                    "Submit Query",
                    variant="primary",
                    size="lg"
                )
        
        # Example Queries
        with gr.Row(elem_classes=["example-queries"]):
            gr.Examples(
                examples=[
                    ["Who is the most active user?"],
                    ["What kind of flowers does Lily like?"],
                    ["What is Lily O'Sullivan planning about distilleries?"],
                    ["How many messages did Thiago Monteiro send?"],
                ],
                inputs=[input_question],
                label="Example Queries"
            )
        
        # Response Section
        with gr.Column():
            output_answer = gr.Markdown(
                label="Agent Response",
                visible=False,
                elem_classes=["response-text"]
            )
        
        # Recommendation Section (Professional Design)
        with gr.Column(visible=False, elem_classes=["recommendation-container"]) as output_recommendation_group:
            gr.Markdown("PROACTIVE RECOMMENDATION", elem_classes=["recommendation-header"])
            output_recommendation_text = gr.Markdown(elem_classes=["recommendation-text"])
            
            with gr.Row(elem_classes=["action-buttons"]):
                confirm_button = gr.Button(
                    "Confirm",
                    visible=False,
                    elem_classes=["primary-action"]
                )
                reject_button = gr.Button(
                    "Dismiss",
                    visible=False,
                    elem_classes=["secondary-action"]
                )
            
            output_feedback_status = gr.Markdown(
                visible=False,
                elem_classes=["status-text"]
            )
        
        # Debug Section (Collapsible)
        with gr.Accordion("Developer View: Raw API Response", open=False, elem_classes=["developer-view"]):
            output_raw_json = gr.JSON(
                label="Full Response Object",
                visible=False
            )
    
    # Event Handlers
    
    # Consolidate all outputs for clarity
    all_outputs = [
        output_answer,
        output_raw_json,
        output_recommendation_group,
        output_recommendation_text,
        confirm_button,
        reject_button,
        output_feedback_status
    ]

    # Submit on button click
    submit_button.click(
        fn=run_agent_demo,
        inputs=[input_question],
        outputs=all_outputs
    )
    
    # Submit on Enter key
    input_question.submit(
        fn=run_agent_demo,
        inputs=[input_question],
        outputs=all_outputs
    )
    
    # Feedback handlers
    confirm_button.click(
        fn=on_confirm_recommendation,
        inputs=[],
        outputs=[output_feedback_status]
    )
    
    reject_button.click(
        fn=on_reject_recommendation,
        inputs=[],
        outputs=[output_feedback_status]
    )


# --- Launch Configuration ---
if __name__ == "__main__":
    logger.info("Launching Gradio Demo Interface...")
    demo.launch(
    server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
    server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )