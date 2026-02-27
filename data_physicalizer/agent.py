from google.adk.agents import Agent  # Ensure this import is clean
import os
import json
import base64
import requests
from datetime import datetime

def save_extracted_data(data_content: str, source_type: str = "whiteboard"):
    """
    Saves extracted data from a physical source into a structured format.
    Use this tool whenever you have successfully identified a table or list in the video.
    Args:
        data_content: The extracted data formatted as a JSON string.
        source_type: The origin of the data (e.g., 'whiteboard', 'spreadsheet', 'handwritten').
    """
    try:
        # Create a filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"physicalized_{source_type}_{timestamp}.json"
        
        # In a real hackathon, we would push this to GitHub or Cloud Storage
        with open(filename, "w") as f:
            f.write(data_content)
            
        return f"✅ Success: Data saved to {filename}"
    except Exception as e:
        return f"❌ Error saving data: {str(e)}"

root_agent = Agent(
    model='gemini-2.5-flash',  # Updated to the latest model
    name='DataPhysicalizer',
    description='A high-precision multimodal agent for real-time data extraction.',
    instruction=(
        "You are the Data Physicalizer. Watch the live video stream. "
        "When you see data, extract it and immediately use the 'save_extracted_data' tool."
    ),
    tools=[save_extracted_data]
)