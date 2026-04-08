import re
from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# 1. Extract policy_action and policy_reason_codes from Yudhishthira
# Add after the existing extraction lines for yudhishthira
if "policy_action = yudhishthira.get(\"policy_action\")" not in content:
    # Find where yudhishthira is defined
    marker = "yudhishthira = engine_results.get(\"yudhishthira\", {}) or {}"
    if marker in content:
        content = content.replace(marker, marker + """
        policy_action = yudhishthira.get("policy_action")
        policy_reason_codes = yudhishthira.get("reason_codes", [])
""")
        print("Added policy_action extraction.")
    else:
        print("Could not find yudhishthira extraction marker.")

# 2. Add policy_action to the decision logic (before sensitivity floor)
# Find the line where sensitivity_label is checked
marker_sens = '# Sensitivity-based decision floor'
if marker_sens in content:
    # Insert before that line
    insert_code = '''
        # Policy override from Yudhishthira
        if policy_action == "block":
            decision = "block"
            decision_logic += f" (policy_action={policy_action} -> block)"
        elif policy_action == "challenge" and decision != "block":
            decision = "challenge"
            decision_logic += f" (policy_action={policy_action} -> challenge)"
        elif policy_action == "monitor" and decision not in ["block", "challenge"]:
            decision = "monitor"
            decision_logic += f" (policy_action={policy_action} -> monitor)"
'''
    content = content.replace(marker_sens, insert_code + "\n\n        " + marker_sens)
    print("Added policy_action to decision logic.")
else:
    print("Could not find sensitivity floor marker. Trying alternative.")

# 3. Add policy_reason_codes to trace
# Find where the trace dict is built and add policy_reason_codes
trace_marker = '"decision_logic": decision_logic,'
if trace_marker in content:
    insert_trace = '''
            "policy_action": policy_action,
            "policy_reason_codes": policy_reason_codes,
'''
    content = content.replace(trace_marker, trace_marker + "\n" + insert_trace)
    print("Added policy fields to trace.")
else:
    print("Could not find decision_logic in trace.")

path.write_text(content)
print("✅ Krishna patched with policy_action and policy_reason_codes.")
