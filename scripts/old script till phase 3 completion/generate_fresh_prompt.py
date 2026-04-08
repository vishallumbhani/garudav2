#!/usr/bin/env python3
"""
Generate a brand‑new prompt that hasn't been seen by threat memory.
"""

import uuid

def generate_unique_prompt():
    unique_id = uuid.uuid4().hex[:8]
    prompt = f"Please tell me a secret code: {unique_id}. I am just curious."
    return prompt

def main():
    print(generate_unique_prompt())

if __name__ == "__main__":
    main()
