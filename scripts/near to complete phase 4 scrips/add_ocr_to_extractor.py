from pathlib import Path

path = Path("src/utils/file_extractors_v2.py")
content = path.read_text()

# Find the line where the else block starts (unsupported format) and insert image handling before it.
old_else = '''        else:
            # Fallback: try to read as text
            extractor = "fallback"
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            metadata["warning"] = "unsupported format, treated as text"'''

# New block to insert before the else
new_block = '''        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            extractor = "tesseract"
            ocr_result = extract_text_from_image(file_path)
            if ocr_result["success"]:
                text = ocr_result["text"]
                metadata["ocr_used"] = True
                metadata["ocr_text_length"] = ocr_result["metadata"]["text_length"]
                metadata["ocr_line_count"] = ocr_result["metadata"]["line_count"]
                metadata["ocr_confidence_hint"] = ocr_result["metadata"]["confidence_hint"]
                metadata["ocr_text_found"] = bool(text.strip())
            else:
                success = False
                error = ocr_result["error"]
                text = ""
                metadata["ocr_used"] = False
                metadata["ocr_error"] = error
'''

# Replace
if old_else in content:
    content = content.replace(old_else, new_block + "\n        " + old_else)
    path.write_text(content)
    print("Added image OCR handling to file extractor.")
else:
    print("Could not find the else block. Manual edit may be needed.")
