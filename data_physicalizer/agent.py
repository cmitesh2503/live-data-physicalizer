from google.adk.agents import Agent  # Ensure this import is clean

root_agent = Agent(
    model='gemini-3.1-pro-preview',  # Updated to the latest model
    name='DataPhysicalizer',
    description='A high-precision multimodal agent for real-time data extraction.',
    instruction=(
        "You are the Data Physicalizer. Watch the live video stream carefully. "
        "Identify tables, spreadsheets, or whiteboard notes. "
        "Extract the data accurately and use the 'commit_to_github' tool to save it."
    ),
)
