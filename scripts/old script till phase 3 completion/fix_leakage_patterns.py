from pathlib import Path

path = Path("src/services/rag_protection.py")
content = path.read_text()

# Replace the leakage_patterns with more comprehensive ones
new_patterns = '''        self.leakage_patterns = [
            # Credentials
            (r"(?:api[_-]?key|token|password|secret)\\s*(?:is|=|:)\\s*['\"]?([A-Za-z0-9_\\-+/]+)['\"]?", "credential"),
            (r"-----BEGIN .* PRIVATE KEY-----", "private_key"),
            (r"sk-[A-Za-z0-9]{32,}", "openai_key"),
            (r"AKIA[0-9A-Z]{16}", "aws_key"),
            # PII
            (r"\\b\\d{3}[-.]?\\d{2}[-.]?\\d{4}\\b", "ssn"),
            (r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", "email"),
            (r"\\b\\d{10}\\b|\\b\\d{3}-\\d{3}-\\d{4}\\b", "phone"),
            # Financial
            (r"\\b(?:\\d{4}[- ]?){3}\\d{4}\\b", "credit_card"),
            (r"\\b\\d{9,12}\\b", "bank_account"),
        ]'''

# Replace old pattern block
import re
pattern = r'self\.leakage_patterns = \[.*?\]'
content = re.sub(pattern, new_patterns, content, flags=re.DOTALL)
path.write_text(content)
print("Leakage patterns updated.")
