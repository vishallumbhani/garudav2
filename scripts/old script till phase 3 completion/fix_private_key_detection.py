import re
from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
content = path.read_text()

# Replace the secrets_patterns with a version that includes multi-line PEM keys
# and severity levels. We'll keep the old patterns and add new ones.
new_secrets = '''        self.secrets_patterns = [
            # PEM private keys (multi-line, highest severity)
            (r"-----BEGIN (RSA|OPENSSH|DSA|EC)? ?PRIVATE KEY-----.*?-----END (RSA|OPENSSH|DSA|EC)? ?PRIVATE KEY-----", "private_key", "critical"),
            # AWS access keys
            (r"AKIA[0-9A-Z]{16}", "aws_access_key", "high"),
            # Generic variable assignments (medium-high)
            (r"(?:api[_\\-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\\s*[:=]\\s*['\\"]?([A-Za-z0-9_\\-+/]+)['\\"]?", "generic_secret", "medium"),
            # Provider-specific (high)
            (r"Bearer\\s+[A-Za-z0-9_\\-\\.]+", "bearer_token", "high"),
            (r"Authorization:\\s*Basic\\s+[A-Za-z0-9+/=]+", "basic_auth", "high"),
            (r"sk-[A-Za-z0-9]{32,}", "openai_api_key", "high"),
            (r"eyJ[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*", "jwt", "high"),
            (r"-----BEGIN CERTIFICATE-----", "certificate", "medium"),
        ]'''

# Find the old block and replace it
pattern = r'self\.secrets_patterns = \[.*?\]\s*'
content = re.sub(pattern, new_secrets, content, flags=re.DOTALL)

# Update the _detect_secrets method to return (type, severity) tuples
# We'll replace the method
old_detect = '''    def _detect_secrets(self, text: str) -> List[str]:
        detected = []
        for pat, name in self.secrets_patterns:
            if re.search(pat, text, re.IGNORECASE):
                detected.append(name)
        return detected'''

new_detect = '''    def _detect_secrets(self, text: str) -> List[tuple]:
        detected = []
        for pat, name, severity in self.secrets_patterns:
            if re.search(pat, text, re.IGNORECASE):
                detected.append((name, severity))
        return detected'''

content = content.replace(old_detect, new_detect)

# Also update the run method to use the new structure
# Find the line where detected_secrets is assigned
content = content.replace('detected_secrets = self._detect_secrets(text)', 'detected_secrets_raw = self._detect_secrets(text)\n        detected_secrets = [s[0] for s in detected_secrets_raw]\n        secret_severities = [s[1] for s in detected_secrets_raw]\n        # Determine highest severity\n        if secret_severities:\n            severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}\n            max_severity = max(secret_severities, key=lambda s: severity_rank.get(s, 0))\n        else:\n            max_severity = None')

# Then add secret_severity to the return dict
return_line = '            "detected_secrets": detected_secrets,'
if return_line in content:
    content = content.replace(return_line, return_line + '\n            "secret_severity": max_severity,')

path.write_text(content)
print("Updated secret detection with severity and multi-line PEM support.")
