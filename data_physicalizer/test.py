
from pathlib import Path
import sys
from pathlib import Path

# Ensure repo root is on sys.path so we can import the package when running from the package folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_physicalizer.agent import ocr_image
p=Path('vision_capture.jpg')
print('vision_capture exists:', p.exists(), 'size:', p.stat().st_size if p.exists() else 'n/a')
text, err = ocr_image('vision_capture.jpg')
print('OCR ERR:', err)
print('OCR TEXT:\\n', text)