import gradio as gr
import requests
import json
import logging

# --- 1. SET UP PROFESSIONAL LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
API_URL = "http://127.0.0.1:8080/ask" # Our local, live API server
logging.info(f"Connecting Gradio... API Server URL is {API_URL}")

def run_agent_demo(question):
    """
    This function is called by Gradio when the user hits 'Submit'.
    It calls our FastAPI, gets the JSON, and returns the pieces for the UI.
    """
    logging.info(f"[Gradio] Received question: {question}")
    try:
        # 1. Call our live API
        response = requests.post(API_URL, json={"question": question}, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        
        # 2. Extract the pieces for the UI
        answer = data.get("answer", "No answer found.")
        pretty_json = json.dumps(data, indent=2)
        
        # 3. Check for a recommendation (THE "WOW" PART)
        recommendation = data.get("proactive_recommendation")
        
        if recommendation:
            logging.info("[Gradio] Recommendation found, showing feedback buttons.")
            suggestion_text = recommendation.get("suggestion_text")
            action_id = recommendation.get("action_id")
            
            # This is our "pro" upgrade: change the button text based on the action
            if "save_preference" in action_id:
                yes_button_text = "Yes, save preference"
            elif "trip_itinerary" in action_id:
                yes_button_text = "Yes, start itinerary"
            else:
                yes_button_text = "Yes"
            
            # This is how Gradio makes components visible
            return {
                output_answer: gr.update(value=answer, visible=True),
                output_raw_json: gr.update(value=pretty_json, visible=True),
                
                # --- This is the magic ---
                output_recommendation_group: gr.update(visible=True),
                output_recommendation_text: gr.update(value=suggestion_text),
                confirm_button: gr.update(value=yes_button_text) # Set dynamic button text
            }
        else:
            # No recommendation, so just show the answer
            logging.info("[Gradio] No recommendation found, hiding feedback buttons.")
            return {
                output_answer: gr.update(value=answer, visible=True),
                output_raw_json: gr.update(value=pretty_json, visible=True),
                
                # --- Hide the recommendation buttons ---
                output_recommendation_group: gr.update(visible=False),
                output_recommendation_text: gr.update(value="")
            }

    except requests.exceptions.RequestException as e:
        logging.error(f"[Gradio] API Error: {e}")
        return {
            output_answer: gr.update(value=f"API Error: {e}", visible=True),
            output_raw_json: gr.update(visible=True, value=f"Error: {e}"),
            output_recommendation_group: gr.update(visible=False)
        }

# --- Dummy functions for the "Yes/No" buttons ---
# In a real app, these would call another API endpoint (e.g., /save_preference)
def on_confirm_recommendation():
    logging.info("[Gradio] User clicked 'Yes'")
    return "Great! I've saved that. (Demo)"

def on_reject_recommendation():
    logging.info("[Gradio] User clicked 'No'")
    return "No problem. I won't save it. (Demo)"

# --- Build the Gradio UI ---
with gr.Blocks(theme=gr.themes.Soft(), title="Proactive Q&A Agent") as demo:
    gr.Markdown("# 🚀 Proactive Q&A Agent Demo")
    gr.Markdown("This demo calls the live FastAPI agent. Ask a question to see the full agentic pipeline, including proactive recommendations.")
    
    with gr.Row():
        input_question = gr.Textbox(label="Ask a question...", placeholder="e.g., What does Lily O'Sullivan like?")
        submit_button = gr.Button("Submit", variant="primary")

    # --- Answer Area ---
    output_answer = gr.Markdown(visible=False)
    
    # --- Recommendation "Feedback Loop" Area ---
    # This group is hidden by default
    with gr.Group(visible=False) as output_recommendation_group:
        gr.Markdown("---")
        output_recommendation_text = gr.Markdown(label="Proactive Recommendation")
        
        with gr.Row():
            # Button text will be set dynamically
            confirm_button = gr.Button("Yes", variant="primary") 
            reject_button = gr.Button("No, thanks")
        
        output_feedback_status = gr.Textbox(label="Feedback Status", interactive=False)

    # --- Debug Area (Raw JSON) ---
    with gr.Accordion("Show Raw API Response (JSON)", open=False):
        output_raw_json = gr.JSON(label="Full Agent Response")

    # --- Wire up the components ---
    submit_button.click(
        fn=run_agent_demo,
        inputs=[input_question],
        outputs=[
            output_answer, 
            output_raw_json, 
            output_recommendation_group, 
            output_recommendation_text,
            confirm_button # Add the button to the output list
        ]
    )
    
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

# --- Launch the App ---
if __name__ == "__main__":
    logging.info("Launching Gradio Demo UI...")
    demo.launch()