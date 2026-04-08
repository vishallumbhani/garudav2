from pathlib import Path

extractor_path = Path("src/utils/file_extractors_v2.py")
with open(extractor_path, "r") as f:
    content = f.read()

# Find the PDF block and replace it with an improved version
# We'll use a simple string replace on a unique pattern
old_pattern = '''        elif ext == ".pdf":
            extractor = "pypdf"
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                text = "\\n\\n--- page break ---\\n\\n".join(pages_text)'''

new_pattern = '''        elif ext == ".pdf":
            extractor = "pypdf"
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    # Clean text: collapse spaces and merge lines
                    page_text = re.sub(r'\\s+', ' ', page_text)
                    page_text = re.sub(r'(?<!\\n)\\n(?!\\n)', ' ', page_text)
                    page_text = re.sub(r'\\n\\s*\\n', '\\n\\n', page_text)
                    pages_text.append(page_text.strip())
                text = "\\n\\n".join(pages_text)'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    with open(extractor_path, "w") as f:
        f.write(content)
    print("PDF extraction improved.")
else:
    print("Old pattern not found. Trying alternative.")
    # Alternative: look for the block without the page break line
    alt_pattern = '''        elif ext == ".pdf":
            extractor = "pypdf"
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                text = "\\n\\n".join(pages_text)'''
    if alt_pattern in content:
        content = content.replace(alt_pattern, new_pattern)
        with open(extractor_path, "w") as f:
            f.write(content)
        print("PDF extraction improved (alternative).")
    else:
        print("Could not find PDF block. Manual edit may be needed.")
