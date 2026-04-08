from enum import IntEnum

class Severity(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

def map_decision_to_severity(decision: str, has_engine_failures: bool, is_isolated: bool = False) -> Severity:
    if is_isolated:
        return Severity.HIGH
    if decision == "block":
        return Severity.HIGH
    if decision == "challenge":
        return Severity.MEDIUM
    if decision == "monitor" and has_engine_failures:
        return Severity.MEDIUM
    return Severity.LOW