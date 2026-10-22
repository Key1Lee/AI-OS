"""Reuse native grain declaration and key assertions for authored model fixtures."""
import json
import sys
sys.dont_write_bytecode=True
from data_modeling_lab.engine import ModelingEngine
from data_modeling_lab.contracts import GrainRequest

if __name__=='__main__':
    p=json.load(sys.stdin)
    engine=ModelingEngine({'tables':p['tables']},{})
    results=[engine.declare_grain(GrainRequest(**request)).model_dump(mode='json') for request in p['declarations']]
    print(json.dumps({'status':'PASS' if all(r['status']=='pass' for r in results) else 'FAIL','declarations':results,
                     'provenance':'data_modeling_lab.ModelingEngine.declare_grain / key_tests'},allow_nan=False))
