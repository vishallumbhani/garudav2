from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
content = path.read_text()

# Define the corrected block as a raw string
new_block = r'''        self.secrets_patterns = [
            # Generic variable assignments (medium confidence)
            (r"(?:api[_\-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\\+\\/]+)['\"]?", "generic_secret"),
            # Provider-specific (high confidence)
            (r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----", "private_key"),
            (r"Bearer\s+[A-Za-z0-9_\-\.]+", "bearer_token"),
            (r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]+", "basic_auth"),
            (r"sk-[A-Za-z0-9]{32,}", "openai_api_key"),
            (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
            (r"eyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*", "jwt"),
            (r"-----BEGIN CERTIFICATE-----", "certificate"),
        ]'''

# Find the line that starts with 'self.secrets_patterns = [' and replace until the matching ']'
import re
pattern = r'self\.secrets_patterns = \[.*?\]\s*'
content = re.sub(pattern, new_block, content, flags=re.DOTALL)
path.write_text(content)
print("Secret patterns replaced.")
