"""Native key/join evidence over PostgreSQL result rows; no SQL re-execution."""
import json
import sys
sys.dont_write_bytecode=True
from data_modeling_lab.engine import ModelingEngine
from data_modeling_lab.contracts import JoinRequest

EMPTY={'columns':{'orderId':'VARCHAR','customerId':'VARCHAR','status':'VARCHAR','totalPriceCents':'BIGINT','currency':'VARCHAR','createdAt':'VARCHAR','updatedAt':'VARCHAR','sourceVersion':'INTEGER'},'rows':[]}

def execute(p):
    tables={**p['tables'],'raw_orders':EMPTY}
    engine=ModelingEngine({'tables':tables},{})
    with engine.connection() as db:
        tests={name:[t.model_dump(mode='json') for t in engine.key_tests(db,name,keys)] for name,keys in p['keys'].items()}
    joins=[]
    for request in p.get('joins',[]):
        result=engine.join(JoinRequest(**request)).model_dump(mode='json')
        joins.append({k:result[k] for k in ('left_table','right_table','left_key','right_key') if k in result} |
                     {k:result[k] for k in ('actual_cardinality','left_rows','right_rows','actual_rows','fanout','trace','explanation')})
    return {'keys':tests,'joins':joins,'provenance':'data_modeling_lab.ModelingEngine.key_tests / join; PostgreSQL row evidence imported unchanged'}

if __name__=='__main__':print(json.dumps(execute(json.load(sys.stdin)),allow_nan=False))
