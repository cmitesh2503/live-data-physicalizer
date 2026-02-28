
import os

try:
	import pytesseract
except Exception as e:
	print('pytesseract not installed:', e)
	raise

# Allow overriding the tesseract executable via environment variable
# Set `TESSERACT_CMD` or `TESSERACT_PATH` if Tesseract is not on PATH
tess_env = os.environ.get('TESSERACT_CMD') or os.environ.get('TESSERACT_PATH')
if tess_env:
	pytesseract.pytesseract.tesseract_cmd = tess_env

print('tesseract_cmd =', pytesseract.pytesseract.tesseract_cmd)
print('exists?', os.path.exists(pytesseract.pytesseract.tesseract_cmd))
if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
	print('\nTesseract executable not found.')
	print('Install Tesseract OCR (Windows):')
	print('- Download Windows installer (UB Mannheim): https://github.com/UB-Mannheim/tesseract/wiki')
	print("- Or use Chocolatey (requires admin): choco install tesseract")
	print('Or set the path environment variable, e.g.:')
	print('  setx TESSERACT_CMD "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"')