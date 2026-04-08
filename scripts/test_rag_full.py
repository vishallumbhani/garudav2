#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.rag_protection import rag_protection

def main():
    print("=== RAG Protection Full Test ===\n")

    # 1. Ingest document
    print("1. Ingesting document...")
    doc_id = "doc-001"
    text = "Customer report: user@example.com, card 4111-1111-1111-1111"
    metadata = rag_protection.ingest_document(doc_id, text, tenant_id="acme")
    print(f"   Metadata: {metadata}")

    # 2. Add chunk
    print("\n2. Adding chunk...")
    rag_protection.add_chunk(doc_id, 0, text)

    # 3. Simulate retrieval with filtering (new signature: filtered, stats, audit_trace)
    print("\n3. Retrieval filtering (user role = viewer):")
    chunks = [
        {"text": "Public info", "doc_id": "doc-public"},
        {"text": text, "doc_id": doc_id},
        {"text": "Another public chunk", "doc_id": "doc-public2"}
    ]
    filtered, stats, audit = rag_protection.filter_chunks(chunks, "viewer")
    print(f"   Stats: {stats}")
    print(f"   Filtered chunks: {[c['text'][:30] for c in filtered]}")
    print("   Audit trace:")
    for entry in audit:
        print(f"     - {entry['reason']} -> allowed={entry['allowed']}")

    # 4. Output leakage scan with redact mode
    print("\n4. Output leakage scan (mode=redact):")
    outputs = [
        "The answer is 42.",
        "Your API key is sk-1234567890abcdef.",
        "My SSN is 123-45-6789 and email is user@example.com.",
    ]
    for out in outputs:
        result = rag_protection.scan_output(out, mode="redact")
        if result["action"] == "redact":
            print(f"   '{out[:40]}...' -> action=redact, redacted={result['redacted_text']}")
        else:
            print(f"   '{out[:40]}...' -> action={result['action']}")

    # 5. Output scan with block mode
    print("\n5. Output scan with block mode:")
    for out in outputs:
        result = rag_protection.scan_output(out, mode="block")
        print(f"   '{out[:40]}...' -> action={result['action']}")

if __name__ == "__main__":
    main()
