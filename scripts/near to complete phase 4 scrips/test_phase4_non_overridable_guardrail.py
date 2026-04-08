#!/usr/bin/env python3
"""
Phase 4D Test: Non-overridable guardrail enforcement

This test verifies that:
1. A break-glass override can be requested and approved
2. The override becomes active
3. A non-overridable guardrail (private key / critical secret) still blocks at runtime
4. Krishna records override_denied instead of override_applied
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
SCAN_URL = f"{BASE_URL}/v1/scan/text"
AUDIT_URL = f"{BASE_URL}/audit/events"
OVERRIDE_REQUEST_URL = f"{BASE_URL}/overrides/request"
OVERRIDE_APPROVE_URL = f"{BASE_URL}/overrides"
ACTIVE_OVERRIDES_URL = f"{BASE_URL}/overrides/active"


def login(email: str, password: str):
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"? Login failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()["access_token"]


def scan_text(token: str, text: str, tenant_id: str = "default"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text, "tenant_id": tenant_id}
    resp = requests.post(SCAN_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"? Scan failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def request_override(token: str, request_type: str, target_ref: str, reason: str, duration_minutes: int = 10):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "request_type": request_type,
        "target_ref": target_ref,
        "request_reason": reason,
        "duration_minutes": duration_minutes,
    }
    resp = requests.post(OVERRIDE_REQUEST_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"? Override request failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def approve_override(token: str, request_id: str, approve: bool = True):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{OVERRIDE_APPROVE_URL}/{request_id}/approve"
    resp = requests.post(url, json={"approve": approve}, headers=headers)
    if resp.status_code != 200:
        print(f"? Override approval failed: {resp.status_code} {resp.text}")
        return False
    return True


def get_active_overrides(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(ACTIVE_OVERRIDES_URL, headers=headers)
    if resp.status_code != 200:
        print(f"? Active override fetch failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def get_audit_events(token: str, limit: int = 5):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(AUDIT_URL, headers=headers, params={"limit": limit})
    if resp.status_code != 200:
        print(f"? Audit fetch failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()


def main():
    print("=" * 70)
    print("Phase 4D Test: Non-overridable Guardrail Enforcement")
    print("=" * 70)

    private_key = "-----BEGIN PRIVATE KEY-----\nABCDEF\n-----END PRIVATE KEY-----"

    print("\n1. Login as platform admin...")
    token = login("admin@garuda.local", "admin123")
    if not token:
        sys.exit(1)
    print("? Login successful")

    print("\n2. Request break-glass override for policy:block_private_keys ...")
    override_req = request_override(
        token=token,
        request_type="break_glass",
        target_ref="policy:block_private_keys",
        reason="Phase 4D non-overridable guardrail test",
        duration_minutes=10,
    )
    if not override_req:
        sys.exit(1)

    request_id = override_req["id"]
    print(f"? Override requested: {request_id}")

    print("\n3. Approve override...")
    if not approve_override(token, request_id):
        sys.exit(1)
    print("? Override approved")

    print("\n4. Confirm override is active...")
    active = get_active_overrides(token)
    if active is None:
        sys.exit(1)

    if len(active) == 0:
        print("? No active overrides found")
        sys.exit(1)

    found = False
    for row in active:
        if row.get("target_ref") == "policy:block_private_keys":
            found = True
            break

    if not found:
        print("? Active override for policy:block_private_keys not found")
        sys.exit(1)

    print(f"? Active overrides found: {len(active)}")

    print("\n5. Rescan private key after override approval...")
    result = scan_text(token, private_key)
    if not result:
        sys.exit(1)

    trace = result.get("details", {}).get("trace", {}) or {}
    decision = result.get("decision")
    policy_action = trace.get("policy_action")
    policy_codes = trace.get("policy_reason_codes", [])
    secret_severity = trace.get("secret_severity")
    active_override = trace.get("active_override")
    override_applied = trace.get("override_applied")
    override_denied = trace.get("override_denied")
    override_denial_reason = trace.get("override_denial_reason")
    hard_stop_reasons = trace.get("hard_stop_reasons", [])
    decision_logic = trace.get("decision_logic")

    print(f"   Decision: {decision}")
    print(f"   Policy action: {policy_action}")
    print(f"   Policy reason codes: {policy_codes}")
    print(f"   Secret severity: {secret_severity}")
    print(f"   Active override: {json.dumps(active_override, indent=2) if active_override else None}")
    print(f"   Override applied: {override_applied}")
    print(f"   Override denied: {override_denied}")
    print(f"   Override denial reason: {override_denial_reason}")
    print(f"   Hard stop reasons: {hard_stop_reasons}")
    print(f"   Decision logic: {decision_logic}")

    passed = True

    if decision != "block":
        print("? Expected final decision to remain block")
        passed = False

    if policy_action != "block":
        print("? Expected policy_action=block")
        passed = False

    if "POLICY_BLOCK_PRIVATE_KEYS" not in policy_codes:
        print("? Expected POLICY_BLOCK_PRIVATE_KEYS in policy_reason_codes")
        passed = False

    if secret_severity != "critical":
        print("? Expected secret_severity=critical")
        passed = False

    if not active_override:
        print("? Expected active_override to be present")
        passed = False

    if override_applied is not False:
        print("? Expected override_applied=false")
        passed = False

    if override_denied is not True:
        print("? Expected override_denied=true")
        passed = False

    if not override_denial_reason:
        print("? Expected override_denial_reason to be set")
        passed = False

    if "critical_secret" not in hard_stop_reasons and "non_overridable_policy" not in hard_stop_reasons:
        print("? Expected hard_stop_reasons to include critical_secret or non_overridable_policy")
        passed = False

    print("\n6. Check latest audit event...")
    events = get_audit_events(token, limit=3)
    if events:
        latest = events[0]
        print("   Latest audit summary:")
        print(f"   - event_id: {latest.get('event_id')}")
        print(f"   - endpoint: {latest.get('endpoint')}")
        print(f"   - decision: {latest.get('decision')}")
        print(f"   - policy_action: {latest.get('policy_action')}")
        print(f"   - policy_reason_codes: {latest.get('policy_reason_codes')}")
        print(f"   - override_applied: {latest.get('override_applied')}")
    else:
        print("?? Could not fetch audit events for final check")

    print("\n" + "=" * 70)
    if passed:
        print("? Phase 4D PASSED: Non-overridable guardrail correctly denied break-glass override")
        sys.exit(0)
    else:
        print("? Phase 4D FAILED: Guardrail enforcement is not behaving as expected")
        sys.exit(2)


if __name__ == "__main__":
    main()