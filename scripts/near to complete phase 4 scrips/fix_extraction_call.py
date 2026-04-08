import re
from pathlib import Path

scan_path = Path("src/services/scan_service.py")
with open(scan_path, "r") as f:
    content = f.read()

old_block = r'''        extraction = extract_from_file\(temp_file, request\.content, request\.filename or "unknown"\)
        request\.normalized_text = extraction\["normalized_text"\]
        request\.file_metadata = extraction\["metadata"\]'''

new_block = '''        extraction = extract_from_file(temp_file, request.filename or "unknown")
        request.normalized_text = extraction["text"]
        request.file_metadata = extraction["metadata"]
        request.normalized_chunks = extraction.get("chunks", [])'''

content = re.sub(old_block, new_block, content)

with open(scan_path, "w") as f:
    f.write(content)

print("Updated scan_service.py to use new extractor.")
