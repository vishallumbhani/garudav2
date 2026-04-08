from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Insert after the line where trace is defined
insert_line = 'trace = {'
new_field = '        "normalized_text": request.normalized_text[:200] if request.normalized_text else None,'
if insert_line in content:
    content = content.replace(insert_line, insert_line + "\n" + new_field)
    with open(krishna_path, "w") as f:
        f.write(content)
    print("Added normalized_text to trace.")
else:
    print("Could not find trace definition.")
