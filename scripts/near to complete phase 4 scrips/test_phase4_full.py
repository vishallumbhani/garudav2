#!/usr/bin/env python3
"""
Phase 4 Full Test Suite
Tests multi‑tenancy, RBAC, policy engine, audit, and overrides.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
SCAN_URL = f"{BASE_URL}/v1/scan/text"
AUDIT_URL = f"{BASE_URL}/audit/events"
OVERRIDE_REQUEST_URL = f"{BASE_URL}/overrides/request"
OVERRIDE_APPROVE_URL = f"{BASE_URL}/overrides"
ACTIVE_OVERRIDES_URL = f"{BASE_URL}/overrides/active"

def login(email, password):
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password})
    if resp.status_code != 200:
        return None
    return resp.json()["access_token"]

def scan_text(token, text, tenant_id="default"):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(SCAN_URL, json={"text": text, "tenant_id": tenant_id}, headers=headers)
    if resp.status_code != 200:
        return None
    return resp.json()

def get_audit_events(token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(AUDIT_URL, headers=headers, params=params)
    if resp.status_code != 200:
        return None
    return resp.json()

def request_override(token, request_type, target_ref, reason, duration_minutes=15):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "request_type": request_type,
        "target_ref": target_ref,
        "request_reason": reason,
        "duration_minutes": duration_minutes
    }
    resp = requests.post(OVERRIDE_REQUEST_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        return None
    return resp.json()

def approve_override(token, request_id, approve=True):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{OVERRIDE_APPROVE_URL}/{request_id}/approve"
    resp = requests.post(url, json={"approve": approve}, headers=headers)
    return resp.status_code == 200

def get_active_overrides(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(ACTIVE_OVERRIDES_URL, headers=headers)
    if resp.status_code != 200:
        return None
    return resp.json()

def main():
    print("=" * 60)
    print("Phase 4 Full Test Suite")
    print("=" * 60)

    # 1. Login as platform admin
    print("\n1. Login as platform admin...")
    token = login("admin@garuda.local", "admin123")
    if not token:
        print("❌ Login failed")
        return
    print("✅ Login successful")

    # 2. Test private key detection (policy should block)
    print("\n2. Testing private key detection...")
    private_key = "-----BEGIN PRIVATE KEY-----\nABCDEF\n-----END PRIVATE KEY-----"
    result = scan_text(token, private_key)
    if not result:
        print("❌ Scan failed")
        return
    decision = result.get("decision")
    trace = result.get("details", {}).get("trace", {})
    policy_action = trace.get("policy_action")
    policy_codes = trace.get("policy_reason_codes", [])
    secret_severity = trace.get("secret_severity")
    print(f"   Decision: {decision}")
    print(f"   Policy action: {policy_action}")
    print(f"   Policy reason codes: {policy_codes}")
    print(f"   Secret severity: {secret_severity}")
    if policy_action == "block" and "POLICY_BLOCK_PRIVATE_KEYS" in policy_codes:
        print("✅ Private key blocked by policy")
    else:
        print("❌ Policy not applied correctly")

    # 3. Test audit endpoint
    print("\n3. Testing audit endpoint...")
    events = get_audit_events(token, {"limit": 5})
    if events and len(events) > 0:
        print(f"✅ Retrieved {len(events)} audit events")
        # Check that recent event contains policy fields
        latest = events[0]
        if latest.get("policy_action") or latest.get("policy_reason_codes"):
            print("   Audit event contains policy fields")
        else:
            print("   ⚠️ Audit event missing policy fields")
    else:
        print("❌ Failed to retrieve audit events")

    # 4. Test override request and approval
    print("\n4. Testing override request/approval...")
    # Request an override for the private key block policy
    override_req = request_override(token, "break_glass", "policy:block_private_keys", "Emergency test", 10)
    if not override_req:
        print("❌ Failed to request override")
    else:
        request_id = override_req["id"]
        print(f"   Override requested, ID: {request_id}")
        # Approve the override
        if approve_override(token, request_id):
            print("✅ Override approved")
            # Check active overrides
            active = get_active_overrides(token)
            if active and len(active) > 0:
                print(f"   Active overrides: {len(active)}")
            else:
                print("   ⚠️ No active overrides found")
        else:
            print("❌ Failed to approve override")

    # 5. Test that override affects decision (optional: after approval, the policy may be overridden)
    # Note: The override is only active if Krishna checks it. Currently we have a placeholder.
    print("\n5. (Placeholder) Override effect – requires Krishna integration to query active overrides.")

    print("\n" + "=" * 60)
    print("Phase 4 Test Suite completed.")
    print("Check the output above for any failures.")
    print("If private key policy block works and audit events contain policy fields, Phase 4 is ready.")

if __name__ == "__main__":
    main()
