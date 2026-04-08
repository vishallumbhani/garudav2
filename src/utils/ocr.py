import pytesseract
from PIL import Image
from pathlib import Path
import re
from typing import Dict, Any, Optional

def extract_text_from_image(image_path: Path) -> Dict[str, Any]:
    """
    Extract text from an image using Tesseract OCR.
    Returns dict with:
        - success: bool
        - text: str (normalized)
        - metadata: dict (text_length, line_count, confidence_hint)
        - error: Optional[str]
    """
    try:
        img = Image.open(image_path)
        # Use default Tesseract config (English)
        ocr_text = pytesseract.image_to_string(img)
        if not ocr_text.strip():
            return {
                "success": True,
                "text": "",
                "metadata": {
                    "text_length": 0,
                    "line_count": 0,
                    "confidence_hint": "low",
                },
                "error": None,
            }
        # Normalize text: collapse whitespace, preserve paragraph breaks
        lines = ocr_text.splitlines()
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        line_count = len(non_empty_lines)
        text = "\n".join(non_empty_lines)
        # Collapse multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        text_length = len(text)
        # Simple confidence hint: if text is very short, quality may be low
        if text_length < 20:
            confidence_hint = "low"
        elif text_length < 100:
            confidence_hint = "medium"
        else:
            confidence_hint = "high"
        return {
            "success": True,
            "text": text,
            "metadata": {
                "text_length": text_length,
                "line_count": line_count,
                "confidence_hint": confidence_hint,
            },
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "metadata": {},
            "error": str(e),
        }
