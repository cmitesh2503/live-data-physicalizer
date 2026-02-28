# 📊 Real-Time Data Physicalizer

## 🚀 The Vision
Turning messy physical data into structured digital assets instantly using Live Multimodal AI.

## 🛠️ Tech Stack
- **Agent Framework:** Google Agent Development Kit (ADK)
- **AI Core:** Google Gemini Multimodal Live API
- **Language:** Python 3.10+
- **Key Tools:** OpenCV (for frame capture), PyGitHub (for data export)

## ⚡ How it Works
1. **Live Stream:** The agent receives a real-time video feed via the Gemini Live API.
2. **Vision Reasoning:** Gemini identifies data structures (tables, lists, charts).
3. **ADK Tool-Use:** The agent triggers a Python tool to format the data into JSON.

## Tesseract OCR (optional)

This project uses `pytesseract` as a wrapper for Tesseract OCR. Tesseract is a separate system dependency.

- Install Tesseract on Windows:
	- Download the installer (UB Mannheim builds): https://github.com/UB-Mannheim/tesseract/wiki
	- Or, if you have Chocolatey: `choco install tesseract` (requires admin privileges)
- After installing, ensure the Tesseract executable is on `PATH` or set the `TESSERACT_CMD` environment variable to the full path, e.g.: `C:\Program Files\Tesseract-OCR\tesseract.exe`.

The small helper in `data_physicalizer/lab.py` will read `TESSERACT_CMD` or `TESSERACT_PATH` to override the executable location.