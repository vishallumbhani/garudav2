from pathlib import Path

path = Path("src/services/scan_service.py")
content = path.read_text()

# Find the problematic block and replace it
# The block we want to replace is from the line with 'if engine_policy.get("arjuna", True):' 
# to the line after the else block. We'll use a more precise approach.

# Look for the pattern:
old_block = '''    if engine_policy.get("arjuna", True):
        arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
        engine_results["arjuna"] = arjuna_result

    classification_result = fallback.wrap_engine("data_classification", DataClassification().run, request)
    engine_results["data_classification"] = classification_result

    else:
        engine_results["arjuna"] = {"engine": "arjuna", "status": "skipped", "score": 0.0}'''

new_block = '''    if engine_policy.get("arjuna", True):
        arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
        engine_results["arjuna"] = arjuna_result
    else:
        engine_results["arjuna"] = {"engine": "arjuna", "status": "skipped", "score": 0.0}

    classification_result = fallback.wrap_engine("data_classification", DataClassification().run, request)
    engine_results["data_classification"] = classification_result'''

if old_block in content:
    content = content.replace(old_block, new_block)
    path.write_text(content)
    print("Fixed syntax error in scan_service.py.")
else:
    print("Old block not found. Trying a more flexible replacement.")
    # Use regex to find and replace
    import re
    pattern = r'    if engine_policy\.get\("arjuna", True\):\n        arjuna_result = fallback\.wrap_engine\("arjuna", Arjuna\(\)\.run, request\)\n        engine_results\["arjuna"\] = arjuna_result\n\n    classification_result = fallback\.wrap_engine\("data_classification", DataClassification\(\)\.run, request\)\n    engine_results\["data_classification"\] = classification_result\n\n    else:\n        engine_results\["arjuna"\] = {"engine": "arjuna", "status": "skipped", "score": 0\.0}'
    replacement = r'    if engine_policy.get("arjuna", True):\n        arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)\n        engine_results["arjuna"] = arjuna_result\n    else:\n        engine_results["arjuna"] = {"engine": "arjuna", "status": "skipped", "score": 0.0}\n\n    classification_result = fallback.wrap_engine("data_classification", DataClassification().run, request)\n    engine_results["data_classification"] = classification_result'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    path.write_text(content)
    print("Fixed using regex.")
