from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
lines = path.read_text().splitlines()

new_block = [
    '        self.secret_patterns = [',
    '            # Generic variable assignments (medium confidence)',
    '            (r"(?:api[_-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\\s*[:=]\\s*[\'\\"]?([A-Za-z0-9_\\-\\+\\/]+)[\'\\"]?", "generic_secret"),',
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

# Find the line where secret_patterns starts
start_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith('self.secret_patterns = ['):
        start_idx = i
        break

if start_idx is None:
    print("Could not find secret_patterns block.")
    exit(1)

# Find the closing bracket
end_idx = start_idx
bracket_count = 0
for i in range(start_idx, len(lines)):
    line = lines[i]
    bracket_count += line.count('[') - line.count(']')
    if bracket_count == 0 and i > start_idx:
        end_idx = i
        break

# Replace the block
new_lines = lines[:start_idx] + new_block + lines[end_idx+1:]
path.write_text('\n'.join(new_lines))
print("Replaced secret_patterns block.")
