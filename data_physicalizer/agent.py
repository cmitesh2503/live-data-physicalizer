import os
import time
import cv2
import json
from dotenv import load_dotenv
from fpdf import FPDF
from google import adk
from google.adk.models.google_llm import _ResourceExhaustedError 

# Load the .env file
load_dotenv() 

project = os.getenv("GOOGLE_CLOUD_PROJECT")
print(f"Agent initializing for project: {project}...")

# --- TOOL 1: Vision Capture ---
def capture_vision_frame():
    """Captures a single frame from the webcam to 'see' the whiteboard."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Error: Could not open camera."
    
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("vision_capture.jpg", frame)
        cap.release()
        return "I've captured a clear image of the data. Processing now..."
    else:
        cap.release()
        return "Error: Failed to capture frame."

# --- TOOL 2: PDF Export ---
def export_to_pdf(data_content: str, mode: str = "summary"):
    """
    Creates a PDF on the local system.
    mode="summary": A clean, bulleted list of notes.
    mode="table": A structured grid with headers and auto-widths.
    """
    pdf = FPDF()
    pdf.add_page()
    
    if mode == "summary":
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, txt="Summary of Captured Notes", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=12)
        lines = data_content.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line:
                pdf.multi_cell(0, 10, txt=f"• {clean_line}")
        
    elif mode == "table":
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, txt="Structured Data Table", ln=True, align='C')
        pdf.ln(10)
        
        try:
            table_data = json.loads(data_content) 
            
            if not table_data or not isinstance(table_data, list):
                return "Error: Invalid table data format. Expected a list of lists."

            num_cols = len(table_data[0])
            col_width = pdf.epw / num_cols 

            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255) 
            for header in table_data[0]:
                pdf.cell(col_width, 10, txt=str(header), border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font("Arial", size=11)
            for row in table_data[1:]:
                for item in row:
                    pdf.cell(col_width, 10, txt=str(item), border=1)
                pdf.ln()

        except Exception as e:
            return f"Error processing table: {str(e)}"
    
    filename = f"physicalized_{mode}.pdf"
    pdf.output(filename)
    return f"Successfully saved to {filename}"

# --- AGENT CONFIGURATION ---
tools = [capture_vision_frame, export_to_pdf]

INSTRUCTIONS = """
You are a Collaborative Data Physicalizer. 🤖
1. GREET: 'System online. I'm watching the feed. Just say "Physicalize" when you've got your notes ready!'
2. TRIGGER: When the user says 'Physicalize', first call 'capture_vision_frame'.
3. SUMMARY: Analyze the image, output a clear text summary to the console, and then ASK: 
   'I've summarized your notes. Would you like the final PDF as a simple list (Option 1) or a structured table (Option 2)?'
4. EXECUTE: Wait for the user to say '1' or '2'.
   - If '1': Call 'export_to_pdf' with mode='summary'.
   - If '2': Call 'export_to_pdf' with mode='table'. For table mode, you MUST format data_content as a valid JSON list of lists.
"""

agent = adk.Agent(
    name="DataPhysicalizer",
    model="gemini-2.0-flash", 
    instruction=INSTRUCTIONS,
    tools=tools,
)

if __name__ == "__main__":
    from google.adk import runners
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    import threading

    # Error flag to communicate between threads
    error_occurred = threading.Event()
    error_message = {"msg": None}

    # Custom exception hook for threads
    original_hook = threading.excepthook
    
    def handle_thread_exception(args):
        if "429" in str(args.exc_value) or "RESOURCE_EXHAUSTED" in str(args.exc_value):
            error_occurred.set()
            error_message["msg"] = "rate_limit"
        else:
            original_hook(args)
    
    threading.excepthook = handle_thread_exception

    runner = runners.Runner(
        app_name="DataPhysicalizerApp",
        agent=agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    print("--- 🤖 Data Physicalizer Session Started ---")
    
    # Starting trigger
    user_input = "Physicalize"
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            # Reset error flag
            error_occurred.clear()
            
            # We wrap our message in the expected Content format
            message = types.Content(role="user", parts=[types.Part(text=user_input)])
            
            # Run the agent for this specific turn
            event_received = False
            for event in runner.run(user_id="user1", session_id="session1", new_message=message):
                if error_occurred.is_set():
                    raise Exception("Rate limit hit in background thread")
                    
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"\nAgent: {part.text}")
                            event_received = True
            
            # Check if error occurred during iteration
            if error_occurred.is_set():
                raise Exception("Rate limit hit in background thread")
            
            retry_count = 0
            
            # Wait for user response in the terminal
            user_input = input("\nYou: ")
            
            if user_input.lower() in ["quit", "exit"]:
                print("Shutting down session...")
                break
                
        except (_ResourceExhaustedError, Exception) as e:
            # Check for rate limiting
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or isinstance(e, _ResourceExhaustedError) or error_message["msg"] == "rate_limit":
                retry_count += 1
                if retry_count > max_retries:
                    print("\n[System] Max retries exceeded. Giving up.")
                    break
                wait_time = min(60, 30 + (retry_count * 15))  # Exponential backoff: 30s, 45s, 60s
                print(f"\n[System] API rate limit hit (attempt {retry_count}/{max_retries}). Waiting {wait_time}s... ⏳")
                time.sleep(wait_time)
                print("[System] Retrying now...")
                continue
            else:
                # If it's a different error, we should see it
                print(f"\n[System] An unexpected error occurred: {e}")
                break