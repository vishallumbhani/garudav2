from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
lines = path.read_text().splitlines()

# Find start index
start = None
for i, line in enumerate(lines):
    if 'self.secrets_patterns = [' in line:
        start = i
        break

if start is None:
    print("Could not find self.secrets_patterns = [")
    exit(1)

# Find end index (matching closing bracket)
end = start
brace_count = 0
for i in range(start, len(lines)):
    line = lines[i]
    brace_count += line.count('[') - line.count(']')
    if brace_count == 0 and i > start:
        end = i
        break

if end == start:
    print("Could not find closing bracket")
    exit(1)

# New block (with proper indentation)
new_block = [
    '        self.secrets_patterns = [',
    '            # Generic variable assignments (medium confidence)',
    '            (r"(?:api[_\\-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\\s*[:=]\\s*[\\\'"]?([A-Za-z0-9_\\-\\+\\/]+)[\\\'"]?", "generic_secret"),',
    '            # Provider-specific (high confidence)',
    '            (r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----", "private_key"),',
    '            (r"Bearer\\s+[A-Za-z0-9_\\-\\.]+", "bearer_token"),',
    '            (r"Authorization:\\s*Basic\\s+[A-Za-z0-9+/=]+", "basic_auth"),',
    '            (r"sk-[A-Za-z0-9]{32,}", "openai_api_key"),',
    '            (r"AKIA[0-9A-Z]{16}", "aws_access_key"),',
    '            (r"eyJ[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*\\.[A-Za-z0-9_\\-]*", "jwt"),',
    '            (r"-----BEGIN CERTIFICATE-----", "certificate"),',
    '        ]',
]

# Replace the lines
new_lines = lines[:start] + new_block + lines[end+1:]
path.write_text('\n'.join(new_lines))
print("Secret patterns updated.")
