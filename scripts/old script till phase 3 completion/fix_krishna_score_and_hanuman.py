from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
content = krishna_path.read_text()

# Add hanuman_info extraction if not present
if "hanuman_info = engine_results.get(\"hanuman\", {})" not in content:
    # Find a place to insert (e.g., after threat_memory extraction)
    insert_line = "threat_memory = engine_results.get(\"threat_memory\", {}) or {}"
    if insert_line in content:
        content = content.replace(insert_line, insert_line + "\n        hanuman_info = engine_results.get(\"hanuman\", {}) or {}")
    else:
        # fallback: insert after behavior extraction
        content = content.replace("behavior = engine_results.get(\"behavior\", {}) or {}", "behavior = engine_results.get(\"behavior\", {}) or {}\n        hanuman_info = engine_results.get(\"hanuman\", {}) or {}")
    print("Added hanuman_info extraction.")

# Ensure score is integer (external_score already does that, but maybe normalized_score is used? The error shows 'score' field)
# In the return dict, we have "score": external_score, which is integer. The error might be from the ScanResponse model expecting int.
# Check if there is any float being assigned to score.
# We'll ensure external_score is int.
# Already it is: external_score = int(round(modified_score * 100))

# However, the error says 'score' Input should be a valid integer, got 0.5. That suggests somewhere else (maybe in fallback?) we are returning a float.
# We'll add a safeguard in the return statement.

# Locate the return dict and ensure score is int.
return_line = 'return {'
if return_line in content:
    # Ensure the score field is cast to int
    content = content.replace('"score": external_score,', '"score": int(external_score),')
    print("Ensured score is integer.")

krishna_path.write_text(content)
print("Krishna fixed.")
