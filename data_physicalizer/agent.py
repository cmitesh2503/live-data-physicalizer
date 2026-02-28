import os
import time
import cv2
import json
from dotenv import load_dotenv
from fpdf import FPDF
from google import adk
from google.adk.models.google_llm import _ResourceExhaustedError 
try:
    import pytesseract
except Exception:
    pytesseract = None
import numpy as np

# If on Windows and Tesseract is installed in the common location, point pytesseract to it
if pytesseract is not None:
    try:
        if os.name == 'nt':
            possible = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
            for p in possible:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break
    except Exception:
        pass

# Load the .env file
load_dotenv() 

project = os.getenv("GOOGLE_CLOUD_PROJECT")
print(f"Agent initializing for project: {project}...")

# --- TOOL 1: Vision Capture ---
def capture_vision_frame():
    """Captures a single frame from the webcam and saves it."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Error: Could not open camera."
    
    ret, frame = cap.read()
    if ret:
        filepath = "vision_capture.jpg"
        # improve image contrast/brightness
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        enhanced = cv2.merge((cl,a,b))
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        cv2.imwrite(filepath, enhanced)
        cap.release()
        # perform quick OCR and display result
        ocr_text, ocr_err = ocr_image(filepath)
        summary = ocr_text if ocr_text else ''
        return f"Image captured and saved to {filepath}. OCR output:\n{summary}"
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
        # use default font; avoid unicode bullets by substituting '-'
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, text="Summary of Captured Notes", ln=1, align='C')
        pdf.ln(10)
        
        pdf.set_font("Helvetica", size=12)
        lines = data_content.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line:
                pdf.multi_cell(0, 10, text=f"- {clean_line}")
        
    elif mode == "table":
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, text="Structured Data Table", ln=1, align='C')
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


# --- OCR helper ---
def ocr_image(filepath: str):
    """Return OCR text for an image using pytesseract. Returns (text, error_message)."""
    if not os.path.exists(filepath):
        return None, "Image file not found"
    if pytesseract is None:
        return None, "pytesseract not installed"
    img = cv2.imread(filepath)
    if img is None:
        return None, "Failed to read image"
    try:
        # increase resolution for better OCR
        scale = 2.0
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (5,5), 0)
        # adaptive threshold to handle varying lighting
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 15, 8)
        # morphological closing to fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
        text = pytesseract.image_to_string(th)
        return text, None
    except Exception as e:
        return None, str(e)


def parse_table_from_ocr(text: str):
    """Attempt to infer a table from OCR text.

    Returns a list-of-lists table (header row first) or None on failure.
    Heuristics used:
    - If lines contain ':' treat as key:value pairs -> 2-col table
    - Prefer tab, pipe, comma, or multi-space delimiters (in that order)
    - If rows have inconsistent columns, pad shorter rows with ''
    - If first row looks like header (contains letters) and subsequent rows are more numeric, treat first as header
    """
    if not text:
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    # If most lines contain ':' -> key:value pairs
    colon_count = sum(1 for ln in lines if ':' in ln)
    if colon_count >= max(1, len(lines) // 3):
        table = [["Key", "Value"]]
        for ln in lines:
            if ':' in ln:
                k, v = ln.split(':', 1)
                table.append([k.strip(), v.strip()])
        return table

    # Try delimiters in order
    # delimiters: tab, pipe, comma, then whitespace fallback
    delimiters = ['\t', '|', ',', None]  # None means multi-space or single-space fallback
    best_table = None
    best_var = None
    for d in delimiters:
        rows = []
        if d is not None:
            for ln in lines:
                parts = [p.strip() for p in ln.split(d) if p.strip()]
                rows.append(parts)
        else:
            # split on 2+ spaces first
            import re
            for ln in lines:
                if re.search(r'\s{2,}', ln):
                    parts = [p.strip() for p in re.split(r'\s{2,}', ln) if p.strip()]
                else:
                    parts = [p.strip() for p in ln.split() if p.strip()]
                rows.append(parts)

        # compute variability in column counts
        counts = [len(r) for r in rows]
        if not counts:
            continue
        var = max(counts) - min(counts)
        # prefer low variability and reasonable columns (>=2)
        if min(counts) >= 2 and (best_var is None or var < best_var):
            best_table = rows
            best_var = var

    if best_table:
        max_cols = max(len(r) for r in best_table)
        table = []
        for r in best_table:
            row = r + [''] * (max_cols - len(r))
            table.append(row)

        # Heuristic: if first row contains letters and following rows have numeric in many columns -> header
        import re
        def is_mostly_numeric(vals):
            n = 0
            for v in vals:
                if re.search(r'[0-9]', v):
                    n += 1
            return n >= max(1, len(vals) // 2)

        first = table[0]
        rest = table[1:]
        if rest and any(is_mostly_numeric(r) for r in rest) and any(re.search('[A-Za-z]', c) for c in first):
            return table

        # If no clear header, synthesize headers
        if rest:
            header = [f"Col{i+1}" for i in range(len(table[0]))]
            return [header] + table

    # Fallback: return key:value single-column pairs if available
    kvs = []
    for ln in lines:
        if ':' in ln:
            k, v = ln.split(':', 1)
            kvs.append([k.strip(), v.strip()])
    if kvs:
        return [["Key", "Value"]] + kvs

    return None

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
    import time
    import threading
    import queue
    from google.adk import runners
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    # Thread-safe error queue to communicate between main and runner threads
    error_queue = queue.Queue()
    
    # Custom exception hook to catch errors in runner thread
    original_excepthook = threading.excepthook
    
    def thread_exception_handler(args):
        error_str = str(args.exc_value)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            error_queue.put(("rate_limit", error_str))
        elif "camera" in error_str.lower() or "msmf" in error_str.lower():
            error_queue.put(("camera_error", error_str))
        else:
            # Print other exceptions normally
            original_excepthook(args)
    
    threading.excepthook = thread_exception_handler

    runner = runners.Runner(
        app_name="DataPhysicalizerApp",
        agent=agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    print("--- 🤖 Data Physicalizer Session Started ---")
    user_input = "Physicalize"
    last_summary = ""  # store last text output by agent
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            # Check for errors from background thread
            try:
                error_type, error_msg = error_queue.get_nowait()
                if error_type == "rate_limit":
                    raise Exception(error_msg)
                elif error_type == "camera_error":
                    print(f"\n[System] Camera error detected. Make sure your webcam is available.")
                    user_input = input("\nYou: ")
                    continue
            except queue.Empty:
                pass
            
            message = types.Content(role="user", parts=[types.Part(text=user_input)])
            
            # If user said "Physicalize" or we just captured, add the image to the message
            if user_input.lower() == "physicalize" or (os.path.exists("vision_capture.jpg") and user_input == "Physicalize"):
                # Wait a moment for capture to complete
                time.sleep(1)
                if os.path.exists("vision_capture.jpg"):
                    with open("vision_capture.jpg", "rb") as img_file:
                        image_data = img_file.read()
                    
                    # Create message with both text and image using the correct API
                    message = types.Content(
                        role="user", 
                        parts=[
                            types.Part(text="Please analyze this whiteboard image and extract all the data/notes you can see. Then ask me if I want it as a list or table."),
                            types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_data))
                        ]
                    )
            
            for event in runner.run(user_id="user1", session_id="session1", new_message=message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"\nAgent: {part.text}")
                            last_summary = part.text  # remember last summary
            
            # Check again after the run completes
            try:
                error_type, error_msg = error_queue.get_nowait()
                if error_type == "rate_limit":
                    raise Exception(error_msg)
            except queue.Empty:
                pass
            
            retry_count = 0  # Reset on success
            # Prompt the user. If they choose 1 or 2, run local OCR and export PDF.
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break

            if user_input.strip() in ["1", "2"]:
                if not os.path.exists("vision_capture.jpg"):
                    print("[System] No captured image found. Say 'Physicalize' first to capture an image.")
                    continue
                # if pytesseract missing, fallback to agent-provided summary
                if pytesseract is None:
                    print("[System] pytesseract not installed, using the agent's summary instead of OCR.")
                    text = last_summary
                    err = None
                else:
                    text, err = ocr_image("vision_capture.jpg")
                if err:
                    print(f"[System] OCR error: {err}. Please install Tesseract and the Python package pytesseract.")
                    print("Install instructions: https://github.com/tesseract-ocr/tesseract and pip install pytesseract")
                    # still allow using agent summary
                    text = last_summary
                    err = None

                if user_input.strip() == "1":
                    # Summary mode: use OCR or fallback
                    result = export_to_pdf(text, mode="summary")
                    print(result)
                else:
                    # Table mode: use intelligent parsing heuristics on OCR output or summary
                    table = parse_table_from_ocr(text)
                    if not table:
                        print("[System] Unable to infer a table from the extracted text. Falling back to summary PDF.")
                        result = export_to_pdf(text, mode="summary")
                        print(result)
                        continue
                    result = export_to_pdf(json.dumps(table), mode="table")
                    print(result)
                # after export, continue main loop
                continue
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_count += 1
                if retry_count > max_retries:
                    print(f"\n[System] Max retries exceeded. API quota is exhausted.")
                    print("[System] Please wait 15-30 minutes and try again.")
                    break
                wait_time = 120 * (2 ** (retry_count - 1))  # 2min, 4min, 8min
                minutes = wait_time // 60
                print(f"\n[System] API rate limit hit (attempt {retry_count}/{max_retries}). Waiting {minutes} minute(s)... ⏳")
                time.sleep(wait_time)
                print("[System] Retrying now...")
                continue 
            else:
                print(f"\n[System] Error: {error_str}")
                break