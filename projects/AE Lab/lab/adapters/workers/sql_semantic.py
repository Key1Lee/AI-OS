"""Read authoritative synthetic definitions; disclose unsupported domain semantics."""
import json
import sys
sys.dont_write_bytecode=True
from semantic.core import Registry, meaning_fingerprint
from adapters.artifacts import artifact_export

if __name__=='__main__':
    p=json.load(sys.stdin);registry=Registry();contract=registry.get('net_revenue','1.0.0')
    print(json.dumps({'contract':contract,'definition_fingerprint':meaning_fingerprint(contract),
        'reference':artifact_export('ae-lab',registry,'net_revenue','1.0.0'),
        'applies_to_lab_metric':False,
        'limitation':'Native contract requires fulfilled-order time and a single product identity per order. Lab scenarios lack that producer contract; no native semantic certification is claimed.',
        'provenance':'semantic.core.Registry / adapters.artifacts.artifact_export; synthetic governed reference only'},allow_nan=False))
