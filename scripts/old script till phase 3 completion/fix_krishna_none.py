from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Replace all occurrences
content = content.replace('engine_results.get("hanuman", {})', 'engine_results.get("hanuman") or {}')
content = content.replace('engine_results.get("yudhishthira", {})', 'engine_results.get("yudhishthira") or {}')
content = content.replace('engine_results.get("shakuni", {})', 'engine_results.get("shakuni") or {}')
content = content.replace('engine_results.get("arjuna", {})', 'engine_results.get("arjuna") or {}')
content = content.replace('engine_results.get("data_classification", {})', 'engine_results.get("data_classification") or {}')
content = content.replace('engine_results.get("kautilya", {})', 'engine_results.get("kautilya") or {}')
content = content.replace('engine_results.get("behavior", {})', 'engine_results.get("behavior") or {}')
content = content.replace('engine_results.get("threat_memory", {})', 'engine_results.get("threat_memory") or {}')
content = content.replace('engine_results.get("bhishma", {})', 'engine_results.get("bhishma") or {}')

path.write_text(content)
print("Fixed Krishna to handle None values.")
