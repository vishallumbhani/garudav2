#!/usr/bin/env python3
import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.rag_protection import rag_protection

def main():
    print("=== RAG Protection Test ===\n")

    # 1. Document classification
    print("1. Document classification:")
    doc = "My email is user@example.com and my credit card is 4111-1111-1111-1111"
    result = rag_protection.classify_document(doc)
    print(f"   Sensitivity: {result['sensitivity_label']}")
    print(f"   Categories: {result['data_categories']}")
    print(f"   PII types: {result['pii_types']}")
    print(f"   Finance types: {result['finance_types']}")
    print()

    # 2. Chunk filtering
    print("2. Chunk filtering (user role=analyst, max sensitivity=MEDIUM):")
    chunks = [
        "Public announcement",
        "My email is user@example.com",
        "API_KEY=sk-1234567890abcdef",
        "Credit card: 4111-1111-1111-1111",
        "General discussion"
    ]
    filtered, stats = rag_protection.filter_retrieved_chunks(chunks, "analyst")
    print(f"   Filtered chunks ({stats['allowed']}/{stats['total']}):")
    for chunk in filtered:
        print(f"     - {chunk[:50]}...")
    print(f"   Blocked reasons: {stats['reasons']}")
    print()

    # 3. Access check
    print("3. Access check:")
    for role in ["admin", "analyst", "viewer"]:
        allowed = rag_protection.check_access(role, "HIGH")
        print(f"   Role {role} access to HIGH document: {allowed}")
    print()

    # 4. Output leakage scan
    print("4. Output leakage scan:")
    outputs = [
        "The answer is 42.",
        "Your API key is sk-1234567890abcdef.",
        "My SSN is 123-45-6789 and email is user@example.com.",
    ]
    for out in outputs:
        result = rag_protection.scan_output_for_leakage(out)
        print(f"   '{out[:40]}...' -> Leakage: {result['leakage_detected']}, Types: {result['leakage_types']}, Risk: {result['risk_level']}")
    print()

if __name__ == "__main__":
    main()
