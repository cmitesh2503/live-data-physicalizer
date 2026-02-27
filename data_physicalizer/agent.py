import os
import cv2
import json
from dotenv import load_dotenv
from fpdf import FPDF
from google import adk  # Ensure your environment points to the Google ADK

# Load the .env file
load_dotenv() 

# The ADK uses the environment variables automatically, 
# but it's good to confirm they are there!
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
        # Header for Summary
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, txt="Summary of Captured Notes", ln=True, align='C')
        pdf.ln(10)
        
        # Bulleted List Logic
        pdf.set_font("Arial", size=12)
        lines = data_content.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line:
                pdf.multi_cell(0, 10, txt=f"• {clean_line}")
        
    elif mode == "table":
        # Header for Table
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, txt="Structured Data Table", ln=True, align='C')
        pdf.ln(10)
        
        try:
            # Parse the JSON string sent by Gemini
            table_data = json.loads(data_content) 
            
            if not table_data or not isinstance(table_data, list):
                return "Error: Invalid table data format. Expected a list of lists."

            # Auto-Width Logic: Calculate width to fill the page
            num_cols = len(table_data[0])
            col_width = pdf.epw / num_cols 

            # --- 1. Draw Highlighted Headers ---
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255) # Light blue fill
            for header in table_data[0]:
                pdf.cell(col_width, 10, txt=str(header), border=1, fill=True, align='C')
            pdf.ln()

            # --- 2. Draw Data Rows ---
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

# Register the tools for the Bidi session
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
    model="gemini-2.0-flash", # Optimized for Multimodal Live API
    system_instruction=INSTRUCTIONS,
    tools=tools
)

if __name__ == "__main__":
    # Start the Bidirectional Live Stream
    agent.run()