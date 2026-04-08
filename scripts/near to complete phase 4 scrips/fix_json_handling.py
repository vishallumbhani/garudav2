#!/usr/bin/env python3
"""
Fix JSON handling in build_arjuna_dataset.py: always try line-by-line first.
"""

import re
from pathlib import Path

script_path = Path("scripts/build_arjuna_dataset.py")
if not script_path.exists():
    print("Script not found.")
    exit(1)

with open(script_path, "r") as f:
    content = f.read()

# Replace the entire JSON block with a new version that tries line-by-line first.
new_json_block = '''    elif ext == ".json":
        # Try line-by-line (JSONL) first, because many JSON files are actually JSONL
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except:
                        # If the line fails, it might be part of a multi-line JSON object; break to try whole-file
                        break
                    if not isinstance(record, dict):
                        continue
                    text = extract_text(record)
                    if not text or len(text) < MIN_TEXT_LEN:
                        continue
                    label, known = extract_label(record)
                    if known:
                        yield text, label, False, None
                    else:
                        heuristic = heuristic_label(text)
                        if heuristic:
                            yield text, heuristic, True, None
                        else:
                            yield text, None, False, record.get("label", "unknown")
            else:
                # If we successfully processed all lines without breaking, we're done
                return
        except Exception as e:
            pass

        # If line-by-line failed or we broke out, try whole-file JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Process as single JSON object
            if isinstance(data, list):
                for record in data:
                    if not isinstance(record, dict):
                        continue
                    text = extract_text(record)
                    if not text or len(text) < MIN_TEXT_LEN:
                        continue
                    label, known = extract_label(record)
                    if known:
                        yield text, label, False, None
                    else:
                        heuristic = heuristic_label(text)
                        if heuristic:
                            yield text, heuristic, True, None
                        else:
                            yield text, None, False, record.get("label", "unknown")
            elif isinstance(data, dict):
                # Try common keys that contain lists
                for key in ["data", "examples", "samples", "root"]:
                    if key in data and isinstance(data[key], list):
                        for record in data[key]:
                            if not isinstance(record, dict):
                                continue
                            text = extract_text(record)
                            if not text or len(text) < MIN_TEXT_LEN:
                                continue
                            label, known = extract_label(record)
                            if known:
                                yield text, label, False, None
                            else:
                                heuristic = heuristic_label(text)
                                if heuristic:
                                    yield text, heuristic, True, None
                                else:
                                    yield text, None, False, record.get("label", "unknown")
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")'''

# Find the JSON block start
start_marker = '    elif ext == ".json":'
if start_marker not in content:
    print("Could not find JSON block.")
    exit(1)

lines = content.split('\n')
start_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith(start_marker.strip()):
        start_idx = i
        break
if start_idx is None:
    print("Could not find start.")
    exit(1)

# Determine indentation
indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
# Find end of block (next elif at same indent)
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) == indent and (lines[i].strip().startswith('elif') or lines[i].strip().startswith('else')):
        end_idx = i
        break
if end_idx is None:
    end_idx = len(lines)

# Replace block
new_lines = lines[:start_idx] + new_json_block.split('\n') + lines[end_idx:]
with open(script_path, "w") as f:
    f.write('\n'.join(new_lines))

print("JSON handling updated to try line-by-line first.")
