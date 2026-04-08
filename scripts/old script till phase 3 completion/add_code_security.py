import re
from pathlib import Path

hanuman_path = Path("src/engines/hanuman/engine.py")
with open(hanuman_path, "r") as f:
    content = f.read()

# Add code security detection after the existing code detection block
# We'll insert a new function in the run method, after determining content_kind == "code"

code_security_block = '''
        # Code security detection (if content is code)
        code_risk_hint = "low"
        code_risk_reason = ""
        if content_kind == "code":
            # Secrets patterns
            secret_patterns = [
                (r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----", "private_key"),
                (r"sk-[A-Za-z0-9]{32,}", "openai_api_key"),
                (r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", "api_key"),
                (r"password\s*[:=]\s*['\"]?[^\s'\"]+", "password"),
                (r"token\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{20,}", "token"),
                (r"Bearer\s+[A-Za-z0-9_\-\.]+", "bearer_token"),
            ]
            dangerous_calls = [
                (r"os\.system\(", "os.system"),
                (r"subprocess\.(call|Popen|run)\(", "subprocess"),
                (r"eval\(", "eval"),
                (r"exec\(", "exec"),
                (r"__import__\(", "__import__"),
                (r"compile\(", "compile"),
            ]
            found_secrets = []
            found_dangerous = []
            for pattern, name in secret_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found_secrets.append(name)
            for pattern, name in dangerous_calls:
                if re.search(pattern, text):
                    found_dangerous.append(name)
            if found_secrets:
                code_risk_hint = "high"
                code_risk_reason = f"Secrets detected: {', '.join(found_secrets)}"
            elif found_dangerous:
                code_risk_hint = "medium"
                code_risk_reason = f"Dangerous functions: {', '.join(found_dangerous)}"
            else:
                code_risk_reason = "No obvious code risks"
        else:
            code_risk_hint = None
            code_risk_reason = None
'''

# Insert after the line where content_kind is set (but before returning)
# We'll find a good insertion point, e.g., after the line that sets `has_secrets_pattern`
insert_after = "has_secrets_pattern = self._has_pattern(self.secrets_patterns, text)"
if insert_after in content:
    content = content.replace(insert_after, insert_after + "\n" + code_security_block)
    print("Added code security detection.")
else:
    print("Could not find insertion point. Adding at end of risk calculation block.")
    # Fallback: add after the risk_hint calculation
    risk_hint_line = 'risk_hint = "low"'
    if risk_hint_line in content:
        content = content.replace(risk_hint_line, risk_hint_line + "\n" + code_security_block)
        print("Added code security detection after risk_hint.")
    else:
        print("Manual edit needed.")

# Also add code_risk_hint and code_risk_reason to the return dict
return_dict_marker = 'return {'
if return_dict_marker in content:
    # Add fields to the return dict
    fields_to_add = '''
            "code_risk_hint": code_risk_hint,
            "code_risk_reason": code_risk_reason,
'''
    content = content.replace(return_dict_marker, return_dict_marker + fields_to_add)
    print("Added code risk fields to return dict.")
else:
    print("Could not find return dict.")

with open(hanuman_path, "w") as f:
    f.write(content)
print("Code security detection added to Hanuman.")
