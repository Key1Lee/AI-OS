"""Deterministic business records; cents remain integers, all timestamps UTC.

Raw arrival tables intentionally lack business-key uniqueness. Declared PK/FK
constraints remain enforced; rejected physical violations live in quarantine.
"""
from copy import deepcopy
from .contracts import Domain, ForeignKey as FK, Table
from .bank_data import BANK_DOMAINS, bank_fixture

T0 = '2026-10-01T00:00:00+00:00'
T1 = '2026-10-02T00:00:00+00:00'
T2 = '2026-10-03T00:00:00+00:00'
END = '2026-11-01T00:00:00+00:00'
MONEY = 'Additive integer cents only within the same currency and at the declared transaction grain.'
SNAP = 'Additive across entities at one instant; never sum the same entity across snapshot dates.'

def table(name, entity, columns, pk, pattern='dimension', *, natural=None, fks=(), event=None, processing=None, dates=(), aggregation=None, parents=(), sql=None, grain=None, uniqueness=None):
    return Table(name, entity, grain or 'one row per ' + ', '.join(pk), columns, tuple(pk), tuple(natural or pk), pattern,
                 tuple(fks), event, processing, tuple(dates), aggregation or (MONEY if any('cents' in c for c in columns) else 'Non-additive attributes; count distinct entities.'),
                 tuple(parents), sql, uniqueness or 'Primary key unique/non-null; natural key unique at declared grain.')

FINTECH = Domain('fintech', 'Fintech / Lending', (
    table('borrowers','borrower',{'borrower_id':'text','name':'text'},['borrower_id']),
    table('borrower_versions','borrower risk version',{'version_id':'text','borrower_id':'text','risk_band':'text','valid_from':'timestamptz','valid_to':'timestamptz'},['version_id'],'scd2',natural=['borrower_id','valid_from'], fks=[FK(('borrower_id',),'borrowers',('borrower_id',))],dates=['valid_from','valid_to']),
    table('loans','loan',{'loan_id':'text','borrower_id':'text','principal_cents':'bigint','currency':'text','originated_at':'timestamptz'},['loan_id'],'transaction_fact',fks=[FK(('borrower_id',),'borrowers',('borrower_id',))],event='originated_at'),
    table('payment_events','received payment event',{'event_id':'bigint','transaction_id':'text','loan_id':'text','principal_cents':'bigint','currency':'text','status':'text','event_at':'timestamptz','received_at':'timestamptz'},['event_id'],'event_fact',natural=['transaction_id'],fks=[FK(('loan_id',),'loans',('loan_id',))],event='event_at',processing='received_at',uniqueness='event_id unique; transaction_id intentionally repeats across retries and updates.'),
    table('installments','scheduled installment',{'installment_id':'text','loan_id':'text','due_at':'timestamptz','due_cents':'bigint'},['installment_id'],'factless_fact',fks=[FK(('loan_id',),'loans',('loan_id',))],event='due_at'),
    table('loan_snapshots','daily loan balance',{'loan_id':'text','snapshot_at':'timestamptz','balance_cents':'bigint'},['loan_id','snapshot_at'],'periodic_snapshot',fks=[FK(('loan_id',),'loans',('loan_id',))],event='snapshot_at',aggregation=SNAP),
    table('ledger_entries','posted ledger entry',{'entry_id':'text','transaction_id':'text','loan_id':'text','amount_cents':'bigint','posted_at':'timestamptz'},['entry_id'],'transaction_fact',fks=[FK(('loan_id',),'loans',('loan_id',))],event='posted_at'),
    table('deduplicated_payments','logical payment transaction',{'transaction_id':'text','loan_id':'text','principal_cents':'bigint','currency':'text','status':'text','event_at':'timestamptz','event_id':'bigint'},['transaction_id'],'transaction_fact',fks=[FK(('loan_id',),'loans',('loan_id',))],event='event_at',parents=['payment_events'],sql='SELECT DISTINCT ON (transaction_id) transaction_id,loan_id,principal_cents,currency,status,event_at,event_id FROM payment_events ORDER BY transaction_id,event_at DESC,event_id DESC'),
    table('loan_principal_summary','loan principal KPI',{'loan_id':'text','total_principal_cents':'numeric'},['loan_id'],'aggregate_fact',parents=['loans','deduplicated_payments'],sql="SELECT l.loan_id,COALESCE(SUM(p.principal_cents) FILTER (WHERE p.status='posted' AND p.currency=l.currency),0) AS total_principal_cents FROM loans l LEFT JOIN deduplicated_payments p USING(loan_id) GROUP BY l.loan_id"),
    table('borrower_portfolio_summary','borrower portfolio',{'borrower_id':'text','outstanding_cents':'numeric'},['borrower_id'],'gold',parents=['borrowers','loans','loan_principal_summary'],sql='SELECT b.borrower_id,COALESCE(SUM(l.principal_cents-s.total_principal_cents),0) AS outstanding_cents FROM borrowers b LEFT JOIN loans l USING(borrower_id) LEFT JOIN loan_principal_summary s USING(loan_id) GROUP BY b.borrower_id'),
), 'full')

COMMERCE = Domain('ecommerce','E-commerce',(
    table('customers','customer',{'customer_id':'text','email':'text'},['customer_id'],'scd1'),
    table('products','product',{'product_id':'text','name':'text'},['product_id']),
    table('orders','order',{'order_id':'text','customer_id':'text','ordered_at':'timestamptz','currency':'text'},['order_id'],'transaction_fact',fks=[FK(('customer_id',),'customers',('customer_id',))],event='ordered_at'),
    table('order_items','order line',{'item_id':'text','order_id':'text','product_id':'text','quantity':'integer','unit_cents':'bigint'},['item_id'],'transaction_fact',fks=[FK(('order_id',),'orders',('order_id',)),FK(('product_id',),'products',('product_id',))]),
    table('refund_events','refund webhook',{'event_id':'bigint','refund_id':'text','order_id':'text','refund_cents':'bigint','status':'text','event_at':'timestamptz','received_at':'timestamptz'},['event_id'],'event_fact',natural=['refund_id'],fks=[FK(('order_id',),'orders',('order_id',))],event='event_at',processing='received_at',uniqueness='event_id unique; refund_id repeats as delivery/version identity.'),
    table('campaigns','campaign',{'campaign_id':'text','name':'text'},['campaign_id']),
    table('order_attribution','order campaign bridge',{'order_id':'text','campaign_id':'text','weight':'numeric(10,4)'},['order_id','campaign_id'],'bridge',fks=[FK(('order_id',),'orders',('order_id',)),FK(('campaign_id',),'campaigns',('campaign_id',))],aggregation='Weights sum to 1 per order; allocate order revenue before campaign aggregation.'),
    table('order_net_revenue','order finance model',{'order_id':'text','net_cents':'numeric'},['order_id'],'aggregate_fact',parents=['order_items','refund_events'],sql="WITH gross AS (SELECT order_id,SUM(quantity*unit_cents) n FROM order_items GROUP BY order_id), latest AS (SELECT DISTINCT ON(refund_id) * FROM refund_events ORDER BY refund_id,event_at DESC,event_id DESC), refunds AS (SELECT order_id,SUM(refund_cents) n FROM latest WHERE status='posted' GROUP BY order_id) SELECT o.order_id,COALESCE(g.n,0)-COALESCE(r.n,0) net_cents FROM orders o LEFT JOIN gross g USING(order_id) LEFT JOIN refunds r USING(order_id)"),
    table('customer_ltv','customer lifetime net revenue',{'customer_id':'text','ltv_cents':'numeric'},['customer_id'],'gold',parents=['customers','orders','order_net_revenue'],sql='SELECT c.customer_id,COALESCE(SUM(n.net_cents),0) ltv_cents FROM customers c LEFT JOIN orders o USING(customer_id) LEFT JOIN order_net_revenue n USING(order_id) GROUP BY c.customer_id'),
), 'full')

SAAS = Domain('saas','SaaS',(
    table('accounts','account',{'account_id':'text','name':'text','started_at':'timestamptz'},['account_id'],event='started_at'),
    table('plans','plan',{'plan_id':'text','name':'text'},['plan_id']),
    table('subscriptions','subscription',{'subscription_id':'text','account_id':'text','plan_id':'text','started_at':'timestamptz'},['subscription_id'],'factless_fact',fks=[FK(('account_id',),'accounts',('account_id',)),FK(('plan_id',),'plans',('plan_id',))],event='started_at'),
    table('subscription_versions','subscription effective version',{'version_id':'text','subscription_id':'text','monthly_cents':'bigint','status':'text','valid_from':'timestamptz','valid_to':'timestamptz'},['version_id'],'scd2',natural=['subscription_id','valid_from'],fks=[FK(('subscription_id',),'subscriptions',('subscription_id',))],dates=['valid_from','valid_to'],aggregation=SNAP),
    table('invoices','invoice',{'invoice_id':'text','subscription_id':'text','invoice_at':'timestamptz','amount_cents':'bigint'},['invoice_id'],'transaction_fact',fks=[FK(('subscription_id',),'subscriptions',('subscription_id',))],event='invoice_at'),
    table('invoice_events','invoice payment event',{'event_id':'bigint','invoice_id':'text','status':'text','event_at':'timestamptz','received_at':'timestamptz'},['event_id'],'event_fact',natural=['invoice_id'],fks=[FK(('invoice_id',),'invoices',('invoice_id',))],event='event_at',processing='received_at',uniqueness='event_id unique; multiple statuses per invoice.'),
    table('usage_events','feature usage event',{'usage_id':'text','account_id':'text','feature':'text','event_at':'timestamptz'},['usage_id'],'event_fact',fks=[FK(('account_id',),'accounts',('account_id',))],event='event_at'),
    table('account_mrr','account MRR as of cutoff',{'account_id':'text','mrr_cents':'numeric'},['account_id'],'gold',parents=['accounts','subscriptions','subscription_versions'],sql="SELECT a.account_id,COALESCE(SUM(v.monthly_cents) FILTER (WHERE v.status='active'),0) mrr_cents FROM accounts a LEFT JOIN subscriptions s USING(account_id) LEFT JOIN subscription_versions v ON v.subscription_id=s.subscription_id AND v.valid_from <= TIMESTAMPTZ '2026-10-03 00:00+00' AND (v.valid_to IS NULL OR TIMESTAMPTZ '2026-10-03 00:00+00'<v.valid_to) GROUP BY a.account_id",aggregation=SNAP),
), 'full')

DOMAINS = {d.id:d for d in (FINTECH,COMMERCE,SAAS)}
DOMAINS.update(BANK_DOMAINS)

def rows(columns, values):
    return [dict(zip(columns, v)) for v in values]

def fixture(domain, variant='clean', seed=1):
    if domain in BANK_DOMAINS:
        return bank_fixture(domain,variant,seed)
    if variant not in ('clean','adversarial','recall') or seed not in (1,2,3):
        raise ValueError('Unknown deterministic fixture')
    bad = variant != 'clean'
    multiplier = seed if variant != 'recall' else seed+3
    data = {}
    def put(name, values):
        data[name] = rows(DOMAINS[domain].table(name).columns, values)
    if domain == 'fintech':
        put('borrowers',[('B1','Ada'),('B2','Bo'),('B3','Cy')])
        put('borrower_versions',[('V1','B1','low',T0,T2),('V2','B1','high',T2,None),('V3','B2','low',T0,None),('V4','B3','medium',T0,None)])
        put('loans',[('L1','B1',100000,'USD',T0),('L2','B1',50000,'USD',T0),('L3','B2',80000,'USD',T0),('L4','B3',20000,'EUR',T0)])
        p=[(1,'TX1','L1',10000,'USD','posted',T1,T1),(3,'TX2','L1',5000,'USD','posted',T2,T2),(4,'TX3','L2',7000,'USD','posted',T1,T1),(5,'TX4','L4',3000,'EUR','posted',T1,T1)]
        if bad:
            p += [(2,'TX1','L1',10000,'USD','posted',T1,T2),
                  (6,'TX2','L1',6000,'USD','posted',T2,T2), # identical timestamps; id breaks tie
                  (7,'TX5','L2',-2000,'USD','posted',T2,T2),
                  (8,'TX6','L1',9000,'USD','posted',T1,T1),(9,'TX6','L1',9000,'USD','reversed',T2,T2),
                  (10,'TX7','L2',None,'USD','posted',T1,T2),
                  (11,'TX8','L1',10000,'USD','posted',T1,T2), # distinct transaction, same amount
                  (12,'TX9','L1',1000,'EUR','posted',T2,T2),
                  (13,'TX10','L1',4000,'USD','posted',T0,END), # late arrival cutoff
                  (14,'TX11','L2',1000,'USD','deleted',T2,T2)]
        put('payment_events',p)
        put('installments',[('I1','L1',T1,20000),('I2','L2',T1,9000),('I3','L3',T1,5000)])
        put('loan_snapshots',[('L1',T1,90000),('L1',T2,84000),('L2',T2,43000)])
        # Independent ledger reconciles eligible latest payment versions; one late adjustment if bad.
        put('ledger_entries',[('E1','TX1','L1',10000,T1),('E2','TX2','L1',6000 if bad else 5000,T2),('E3','TX3','L2',7000,T1),('E4','TX4','L4',3000,T1)] +
            ([('E5','TX5','L2',-2000,T2),('E6','TX8','L1',10000,T2),('E7','TX10','L1',4000,END),('E8','ADJ','L2',100,T2)] if bad else []))
    elif domain == 'ecommerce':
        put('customers',[('C1','ada@example.test'),('C2','bo@example.test'),('C3','cy@example.test')])
        put('products',[('P1','Book'),('P2','Lamp')])
        put('orders',[('O1','C1',T1,'USD'),('O2','C1',T2,'USD'),('O3','C2',T2,'USD')])
        put('order_items',[('IT1','O1','P1',2,1000),('IT2','O1','P2',1,3000),('IT3','O2','P1',1,1000),('IT4','O3','P2',1,3000)])
        put('refund_events',[(1,'R1','O1',1000,'posted',T1,T1),(3,'R2','O1',500,'posted',T2,T2)] +
            ([(2,'R1','O1',1000,'posted',T1,T2),(4,'R2','O1',700,'posted',T2,T2),(5,'R3','O2',500,'posted',T1,T1),(6,'R3','O2',500,'reversed',T2,T2)] if bad else []))
        put('campaigns',[('A1','Search'),('A2','Mail'),('A3','Social')])
        put('order_attribution',[('O1','A1','0.6000'),('O1','A2','0.4000'),('O2','A1','1.0000'),('O3','A2','1.0000')])
    elif domain == 'saas':
        put('accounts',[('A1','Acme',T0),('A2','Beta',T0),('A3','Quiet',T0)])
        put('plans',[('P1','Basic'),('P2','Team')])
        put('subscriptions',[('S1','A1','P1',T0),('S2','A1','P2',T0),('S3','A2','P1',T0)])
        put('subscription_versions',[('V1','S1',1000,'active',T0,T2),('V2','S1',1800 if bad else 1500,'active',T2,None),('V3','S2',2000,'active',T0,None),('V4','S3',1000,'active',T0,T2),('V5','S3',1000,'cancelled' if bad else 'active',T2,None)])
        put('invoices',[('I1','S1',T1,1000),('I2','S1',T2,1800 if bad else 1500),('I3','S2',T2,2000),('I4','S3',T2,1000)])
        put('invoice_events',[(1,'I1','paid',T1,T1),(2,'I2','paid',T2,T2),(3,'I3','paid',T2,T2)] + ([(4,'I2','failed',T2,T2),(5,'I4','paid',T1,END)] if bad else []))
        put('usage_events',[('U1','A1','export',T1),('U2','A1','dashboard',T2),('U3','A2','export',T1)])
    if variant == 'recall':
        # A newer revision can lower an amount or restore a previously failed
        # state. Sorting by amount/status must not accidentally imitate event IDs.
        if domain == 'fintech':
            next(r for r in data['payment_events'] if r['event_id']==6)['principal_cents']=3000
            next(r for r in data['ledger_entries'] if r['entry_id']=='E2')['amount_cents']=3000
            data['payment_events'].append({'event_id':15,'transaction_id':'TX2','loan_id':'L1',
                'principal_cents':4500,'currency':'USD','status':'posted','event_at':T1,'received_at':END})
        elif domain == 'ecommerce':
            next(r for r in data['refund_events'] if r['event_id']==4)['refund_cents']=200
        elif domain == 'saas':
            data['invoice_events'].append({'event_id':6,'invoice_id':'I2','status':'paid','event_at':T2,'received_at':T2})
    for values in data.values():
        for row in values:
            for key,value in row.items():
                if key.endswith('_cents') and value is not None:
                    row[key] *= multiplier
    if seed == 2:
        for values in data.values():values.reverse()
    return data

def injected_violations(domain):
    """Rejected ingress samples: physical constraints cannot admit these rows."""
    if domain != 'fintech':
        return []
    base=deepcopy(fixture(domain,'clean')['payment_events'][0])
    collision=deepcopy(base)
    orphan={**base,'event_id':999,'transaction_id':'ORPHAN','loan_id':'MISSING'}
    overlap={'version_id':'OVERLAP','borrower_id':'B1','risk_band':'high','valid_from':T1,'valid_to':END}
    return [{'table':'payment_events','row':collision,'failure':'primary_key_collision'},
            {'table':'payment_events','row':orphan,'failure':'broken_foreign_key'},
            {'table':'borrower_versions','row':overlap,'failure':'scd_overlap'}]
