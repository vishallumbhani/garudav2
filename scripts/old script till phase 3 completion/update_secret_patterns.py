import re
from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
content = path.read_text()

# Replace the secret_patterns block with expanded patterns
new_secret_patterns = '''        self.secret_patterns = [
            # Generic variable assignments (medium confidence)
            (r"(?:api[_-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\\s*[:=]\\s*['\\"]?([A-Za-z0-9_\\-\\+\\/]+)['\\"]?", "generic_secret"),
            # Provider-specific (high confidence)
            (r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----", "private_key"),
            (r"Bearer\\s+[A-Za-z0-9_\\-\\.]+", "bearer_token"),
            (r"Authorization:\\s*Basic\\s+[A-Za-z0-9+/=]+", "basic_auth"),
            (r"sk-[A-Za-z0-9]{32,}", "openai_api_key"),
            (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
            (r"eyJ[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*", "jwt"),
            (r"-----BEGIN CERTIFICATE-----", "certificate"),
        ]'''

# Find the old block and replace
pattern = r'self\.secret_patterns = \[.*?\]'
content = re.sub(pattern, new_secret_patterns, content, flags=re.DOTALL)
path.write_text(content)
print("Updated secret patterns.")
