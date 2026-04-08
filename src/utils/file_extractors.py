import os
import json
import csv
import re
from pathlib import Path
from typing import Dict, Any, Optional
import pypdf

def extract_from_file(file_path: Path, content_bytes: bytes, original_name: str) -> Dict[str, Any]:
    """
    Extract normalized text and metadata from a file.
    Returns dict with input_type, normalized_text, metadata.
    """
    ext = Path(original_name).suffix.lower()
    metadata = {
        "file_name": original_name,
        "file_extension": ext,
        "length": len(content_bytes),
        "content_type": _guess_mime(ext)
    }
    text = ""

    if ext in ['.txt', '.md', '.log', '.py', '.js', '.java']:
        # Plain text files
        text = content_bytes.decode('utf-8', errors='ignore')
    elif ext == '.csv':
        try:
            decoded = content_bytes.decode('utf-8')
            reader = csv.reader(decoded.splitlines())
            rows = list(reader)
            text = "\n".join(",".join(row) for row in rows)
        except:
            text = decoded
    elif ext == '.json':
        try:
            data = json.loads(content_bytes)
            text = json.dumps(data, indent=2)
        except:
            text = content_bytes.decode('utf-8', errors='ignore')
    elif ext in ['.yaml', '.yml']:
        # For simplicity, treat as text
        text = content_bytes.decode('utf-8', errors='ignore')
    elif ext == '.pdf':
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except Exception as e:
            text = f"[PDF extraction error: {e}]"
    else:
        # Unsupported – treat as text but warn
        text = content_bytes.decode('utf-8', errors='ignore')
        metadata['warning'] = "unsupported format, treated as text"

    return {
        "input_type": "file",
        "normalized_text": text,
        "metadata": metadata
    }

def _guess_mime(ext: str) -> str:
    mime_map = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.log': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.py': 'text/x-python',
        '.js': 'application/javascript',
        '.java': 'text/x-java',
        '.yaml': 'application/x-yaml',
        '.yml': 'application/x-yaml',
        '.pdf': 'application/pdf'
    }
    return mime_map.get(ext, 'application/octet-stream')
