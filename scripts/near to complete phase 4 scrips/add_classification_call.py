from pathlib import Path

path = Path("src/services/scan_service.py")
content = path.read_text()

# Find the line where arjuna_result is added to engine_results
marker = 'engine_results["arjuna"] = arjuna_result'
if marker in content:
    # Insert classification call after that line
    new_lines = '''

    classification_result = fallback.wrap_engine("data_classification", DataClassification().run, request)
    engine_results["data_classification"] = classification_result
'''
    content = content.replace(marker, marker + new_lines)
    path.write_text(content)
    print("Added classification engine call.")
else:
    print("Marker not found.")
