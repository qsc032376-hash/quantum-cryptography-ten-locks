from enum import IntEnum
class Status(IntEnum):
 UNTESTED=0
 SYMBOLICALLY_VALID=1
 OPERATOR_VERIFIED=2
 COMPILED=3
 CHECKER_FULL=4
 RELIABILITY_VALIDATED=5

def qualify(entry):
 required=('hash_ok','circuit_executed')
 return entry.get('status')=='full' and all(entry.get(k) for k in required) and entry.get('metrics_status')=='ok' and entry.get('flags')==[]
