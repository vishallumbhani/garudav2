#!/usr/bin/env python3
"""
Debug Krishna's weight calculation and session high_risk_count.
Adds print statements to see actual values.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# 1. Add debug prints to Krishna
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

debug_code = '''
        # DEBUG: print scores and weights
        print(f"DEBUG: bhishma_score={bhishma_score}, hanuman_score={hanuman_score}, shakuni_score={shakuni_score}, arjuna_score={arjuna_score}")
        print(f"DEBUG: weights={self.weights}")
        computed_base = (self.weights["bhishma"] * bhishma_score +
                         self.weights["hanuman"] * hanuman_score +
                         self.weights["shakuni"] * shakuni_score +
                         self.weights["arjuna"] * arjuna_score)
        print(f"DEBUG: computed_base={computed_base}")
'''

# Insert after extracting arjuna_score
if "arjuna_score = arjuna.get(\"score\", 0.5)" in krishna:
    insert_after = "arjuna_score = arjuna.get(\"score\", 0.5)"
    krishna = krishna.replace(insert_after, insert_after + "\n" + debug_code)
    with open("src/engines/krishna/engine.py", "w") as f:
        f.write(krishna)
    print("Added debug prints to Krishna.")
else:
    print("Could not find arjuna_score extraction line.")

# 2. Add debug prints to behavior service
with open("src/services/behavior_service.py", "r") as f:
    behavior = f.read()

debug_behavior = '''
        # DEBUG: print high_risk_count
        print(f"DEBUG: computed high_risk_count={high_risk_count}, max_risk={max_risk}, weighted_risk={weighted_risk}")
'''
if "high_risk_count = sum(1 for s in scores if s >= self.high_risk_threshold)" in behavior:
    insert_after = "high_risk_count = sum(1 for s in scores if s >= self.high_risk_threshold)"
    behavior = behavior.replace(insert_after, insert_after + debug_behavior)
    with open("src/services/behavior_service.py", "w") as f:
        f.write(behavior)
    print("Added debug prints to behavior service.")
else:
    print("Could not find high_risk_count calculation line.")

print("\n✅ Debug prints added. Restart server and observe terminal output.")
