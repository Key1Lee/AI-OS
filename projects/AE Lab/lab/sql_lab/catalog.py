"""Private execution contracts derived from the one learner problem catalog.

Step 1's three contracts remain; Step 2 definitions use the same executor.
"""
from .contracts import Challenge
from .datasets import DOMAINS

D=DOMAINS['fintech'].table('deduplicated_payments').model_sql
P=DOMAINS['fintech'].table('loan_principal_summary').model_sql
C=DOMAINS['ecommerce'].table('order_net_revenue').model_sql

PAY_RULES=('Latest event_at, then greatest event_id wins per transaction_id; resolve before status filtering.',
 'Only posted events in the loan currency count. Negative posted adjustments reduce principal.',
 'Include every loan. For this KPI, a NULL measure contributes zero and remains a source quality warning.',
 'All fixture arrivals are available. Use integer cents, not floating point.')
REF_RULES=('Each order line contributes quantity × unit_cents once.',
 'Choose the latest refund version by refund_id, event_at DESC, event_id DESC before filtering posted.',
 'Lifetime net = line gross minus eligible refund cents. Include every order; all amounts are USD cents.')

def challenge(id,domain,title,inputs,output,key,concepts,oracle,solution,assumptions):
 return Challenge(id,domain,title,'C',3,'Compute the requested finance output from the displayed source records.',
   tuple(inputs.split()),tuple(output.split()),tuple(key.split()),'one row per '+', '.join(key.split()),
   tuple(concepts.split()),assumptions,'What evidence lets you trust this result after a replay?',oracle,solution,
   'Compare the producer row meaning with the consumer row meaning.')

CHALLENGES=[
 challenge('FIN-001','fintech','Loan finance summary','loans payment_events','loan_id total_principal_cents','loan_id',
   'deduplication grain left_join null_handling financial_accuracy','principal',f'WITH deduplicated_payments AS ({D}) '+P,PAY_RULES),
 challenge('SAAS-003','saas','Invoice payment report','invoices invoice_events','invoice_id amount_cents','invoice_id',
   'deduplication deterministic_tie financial_accuracy','paid_invoices',
   "WITH x AS (SELECT DISTINCT ON(invoice_id) * FROM invoice_events ORDER BY invoice_id,event_at DESC,event_id DESC) SELECT i.invoice_id,i.amount_cents FROM invoices i JOIN x USING(invoice_id) WHERE x.status='paid'",
   ('Report invoices whose latest event status is paid. All arrivals available; greatest event_at then event_id wins.',)),
 challenge('EC-001','ecommerce','Order finance report','orders order_items refund_events','order_id net_cents','order_id',
   'fanout deduplication grain financial_accuracy','commerce',C,REF_RULES),
]
CATALOG={c.id:c for c in CHALLENGES}

# The same Step 1 contract is the only authored learner catalog.
from importlib.resources import files
import json
from .bank_oracles import expected_bank
from .datasets import fixture
from decimal import Decimal
for p in json.loads((files('curriculum')/'sql-bank.json').read_text()):
    rules=p['evaluation_rules'];identity=p['problem_id']
    values=[r for variant,seed in [('clean',1),('adversarial',1),('recall',3)]
            for r in expected_bank(identity,fixture(p['domain'],variant,seed))]
    output_types={k:'numeric' if any(isinstance(r[k],(int,float,Decimal)) and not isinstance(r[k],bool) for r in values) else 'text'
                  for k in rules['required_columns']}
    CATALOG[identity]=Challenge(identity,p['domain'],p['neutral_title'],identity.split('-')[1],int(p['difficulty']['level'][1]),
        p['business_context'],tuple(t['name'] for t in p['tables']),tuple(rules['required_columns']),tuple(rules['output_key']),
        p['expected_output_grain'],tuple(p['mastery_tags']),tuple(p['requirements']),p['followups'][0],
        'bank:'+identity,p['solution'],p['hints'][0],kind=p['kind'],manual_criteria=tuple(rules['manual_criteria']),
        output_types=output_types,joins=rules['joins'],ordered=rules['ordered'])
