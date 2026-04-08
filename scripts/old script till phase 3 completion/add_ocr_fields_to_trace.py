from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Add OCR fields to the trace
# We'll insert them after the file_metadata line
insert_after = '"file_metadata": request.file_metadata if hasattr(request, "file_metadata") else None,'
new_fields = '''        "ocr_used": request.file_metadata.get("ocr_used") if request.file_metadata else None,
        "ocr_text_found": request.file_metadata.get("ocr_text_found") if request.file_metadata else None,
        "ocr_text_length": request.file_metadata.get("ocr_text_length") if request.file_metadata else None,
        "ocr_line_count": request.file_metadata.get("ocr_line_count") if request.file_metadata else None,
        "ocr_confidence_hint": request.file_metadata.get("ocr_confidence_hint") if request.file_metadata else None,
        "ocr_error": request.file_metadata.get("ocr_error") if request.file_metadata else None,
'''
if insert_after in content:
    content = content.replace(insert_after, insert_after + "\n" + new_fields)
    path.write_text(content)
    print("Added OCR fields to trace.")
else:
    print("Could not find insertion point. Trying alternative.")
    # Fallback: add after "file_metadata" line if present
    if '"file_metadata":' in content:
        content = content.replace('"file_metadata":', new_fields + '"file_metadata":')
        path.write_text(content)
        print("Added OCR fields before file_metadata.")
    else:
        print("Manual edit needed.")
