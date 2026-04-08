#!/usr/bin/env python3
"""
Reset threat memory keys.
Usage:
    python scripts/reset_threat_memory.py --session <session_id>
    python scripts/reset_threat_memory.py --all
"""

import redis
import argparse

REDIS_URL = "redis://localhost:6379/0"

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", help="Reset keys for a specific session")
    group.add_argument("--all", action="store_true", help="Reset all threat memory keys")
    args = parser.parse_args()

    r = redis.from_url(REDIS_URL, decode_responses=True)

    if args.all:
        count = 0
        for key in r.scan_iter("threat:*"):
            r.delete(key)
            count += 1
        print(f"Deleted {count} threat memory keys (all).")
    elif args.session:
        count = 0
        for key in r.scan_iter(f"threat:session:{args.session}:*"):
            r.delete(key)
            count += 1
        print(f"Deleted {count} keys for session {args.session}.")

if __name__ == "__main__":
    main()
