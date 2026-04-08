from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Add hanuman_info extraction if not present
if "hanuman_info = engine_results.get(\"hanuman\", {})" not in content:
    # Insert after the line where bhishma is extracted
    marker = "bhishma = engine_results.get(\"bhishma\", {})"
    if marker in content:
        content = content.replace(marker, marker + "\n        hanuman_info = engine_results.get(\"hanuman\", {}) or {}")
        print("Added hanuman_info extraction.")
    else:
        print("Marker not found. Trying alternative.")
        # Insert near the top after engine_results.get lines
        content = content.replace(
            "engine_results.get(\"behavior\", {})",
            "engine_results.get(\"behavior\", {})\n        hanuman_info = engine_results.get(\"hanuman\", {}) or {}"
        )
        print("Added hanuman_info after behavior.")

# Ensure external_score is integer
if "external_score = int(round(modified_score * 100))" not in content:
    if "external_score = modified_score * 100" in content:
        content = content.replace("external_score = modified_score * 100", "external_score = int(round(modified_score * 100))")
        print("Fixed external_score to integer.")
    else:
        # Add conversion before return
        content = content.replace("return {", "    external_score = int(round(modified_score * 100))\n    return {")
        print("Added external_score conversion.")

path.write_text(content)
print("Krishna updated.")
