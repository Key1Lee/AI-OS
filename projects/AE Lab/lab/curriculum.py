"""The machine-readable shared learning map; no execution capabilities here."""
from importlib.resources import files
import json

ROOT=files('curriculum')
CURRICULUM=json.loads((ROOT/'curriculum.json').read_text())
POLICY=json.loads((ROOT/'policy.json').read_text())

def concepts():
    result={}
    for domain in CURRICULUM['domains']:
        for group,children in domain['concepts'].items():
            parent=f"{domain['id']}.{group}"
            result[parent]={'id':parent,'domain':domain['id'],'title':group.replace('_',' '),'parent':None}
            for child in children:
                identity=f'{parent}.{child}'
                result[identity]={'id':identity,'domain':domain['id'],'title':child.replace('_',' '),'parent':parent}
    return result

CONCEPTS=concepts()
if len(CONCEPTS)!=sum(len(groups)+sum(map(len,groups.values())) for groups in (d['concepts'] for d in CURRICULUM['domains'])):
    raise ValueError('Duplicate curriculum concept IDs')
