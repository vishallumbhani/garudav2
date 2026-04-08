from pathlib import Path

scan_path = Path("src/services/scan_service.py")
content = scan_path.read_text()

# Add import
if "from src.engines.classification.engine import DataClassification" not in content:
    # Insert after other engine imports
    import_line = "from src.engines.arjuna.engine import Arjuna"
    content = content.replace(import_line, import_line + "\nfrom src.engines.classification.engine import DataClassification")

# Insert the engine call after arjuna_result
marker = "arjuna_result = fallback.wrap_engine(\"arjuna\", Arjuna().run, request)\n    engine_results[\"arjuna\"] = arjuna_result"
if marker in content:
    new_lines = marker + "\n\n    classification_result = fallback.wrap_engine(\"data_classification\", DataClassification().run, request)\n    engine_results[\"data_classification\"] = classification_result"
    content = content.replace(marker, new_lines)
    print("Added classification engine to scan_service.")
else:
    print("Could not find insertion point.")

scan_path.write_text(content)
