import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Check if already present
if "kautilya_info" in content:
    print("Kautilya fields already in Krishna.")
    exit(0)

# Find a good place to insert – after the threat memory fields but before building trace.
# We'll add after the line that sets "threat_global_reason".
marker = 'threat_global_reason = threat_memory.get("global_reason", "")'
if marker not in content:
    print("Marker not found. Manual edit may be needed.")
    exit(1)

insert_code = '''
        # Kautilya routing info
        kautilya_info = engine_results.get("kautilya", {})
        kautilya_path = kautilya_info.get("path")
        kautilya_reason = kautilya_info.get("reason")
        kautilya_engines_run = kautilya_info.get("engines_run")
        kautilya_engines_skipped = kautilya_info.get("engines_skipped")
        kautilya_cost_tier = kautilya_info.get("cost_tier")
        kautilya_latency_budget_ms = kautilya_info.get("latency_budget_ms")
'''
content = content.replace(marker, marker + "\n" + insert_code)

# Now add these fields to the trace dict. Find the line where trace = { and add after.
trace_start = "trace = {"
if trace_start in content:
    trace_fields = '''
        "kautilya_path": kautilya_path,
        "kautilya_reason": kautilya_reason,
        "kautilya_engines_run": kautilya_engines_run,
        "kautilya_engines_skipped": kautilya_engines_skipped,
        "kautilya_cost_tier": kautilya_cost_tier,
        "kautilya_latency_budget_ms": kautilya_latency_budget_ms,
'''
    content = content.replace(trace_start, trace_start + "\n" + trace_fields)
else:
    print("Could not find trace dict start. Manual edit needed.")

with open(krishna_path, "w") as f:
    f.write(content)
print("Kautilya fields added to Krishna trace.")
