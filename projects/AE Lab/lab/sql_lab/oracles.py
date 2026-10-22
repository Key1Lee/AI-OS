"""Independent Python reference calculations, never evaluating answer SQL."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from .datasets import T1, T2


def latest(records, key, time='event_at', tie='event_id', cutoff=None):
    chosen={}
    for row in records:
        if cutoff and row['received_at'] >= cutoff:
            continue
        identity=row[key]
        if identity not in chosen or (row[time],row[tie]) > (chosen[identity][time],chosen[identity][tie]):
            chosen[identity]=row
    return list(chosen.values())


def principal(data, cutoff=None):
    loans={r['loan_id']:r for r in data['loans']}
    paid=defaultdict(int)
    for p in latest(data['payment_events'],'transaction_id',cutoff=cutoff):
        if p['status']=='posted' and p['currency']==loans[p['loan_id']]['currency']:
            paid[p['loan_id']] += p['principal_cents'] or 0
    return [{'loan_id':r['loan_id'],'total_principal_cents':paid[r['loan_id']]} for r in data['loans']]


def commerce(data):
    gross=defaultdict(int); refunded=defaultdict(int)
    for r in data['order_items']:
        gross[r['order_id']]+=r['quantity']*r['unit_cents']
    for r in latest(data['refund_events'],'refund_id'):
        if r['status']=='posted': refunded[r['order_id']]+=r['refund_cents']
    return [{'order_id':r['order_id'],'net_cents':gross[r['order_id']]-refunded[r['order_id']]} for r in data['orders']]


def mrr(data, at=T2):
    account={r['subscription_id']:r['account_id'] for r in data['subscriptions']}
    amounts=defaultdict(int)
    for v in data['subscription_versions']:
        if v['valid_from']<=at and (v['valid_to'] is None or at<v['valid_to']) and v['status']=='active':
            amounts[account[v['subscription_id']]]+=v['monthly_cents']
    return [{'account_id':r['account_id'],'mrr_cents':amounts[r['account_id']]} for r in data['accounts']]


def expected(name, data):
    if name.startswith('bank:'):
        from .bank_oracles import expected_bank
        return expected_bank(name[5:],data)
    if name=='principal':return principal(data)
    if name=='no_payments':
        seen={r['loan_id'] for r in data['payment_events']}
        return [{'loan_id':r['loan_id']} for r in data['loans'] if r['loan_id'] not in seen]
    if name=='outstanding':
        paid={r['loan_id']:r['total_principal_cents'] for r in principal(data)}
        return [{'loan_id':r['loan_id'],'outstanding_cents':r['principal_cents']-paid[r['loan_id']]} for r in data['loans']]
    if name=='delinquency':
        paid={r['loan_id']:r['total_principal_cents'] for r in principal(data)}
        due=defaultdict(int); late=defaultdict(int)
        for r in data['installments']:
            if r['due_at']<T2:due[r['loan_id']]+=r['due_cents']
        for r in data['loans']:
            late[r['borrower_id']]+=int(due[r['loan_id']]>paid[r['loan_id']])
        return [{'borrower_id':r['borrower_id'],'delinquent_loans':late[r['borrower_id']]} for r in data['borrowers']]
    if name=='reconciliation':
        paid={r['loan_id']:r['total_principal_cents'] for r in principal(data)}
        ledger=defaultdict(int)
        for r in data['ledger_entries']:ledger[r['loan_id']]+=r['amount_cents']
        return [{'loan_id':r['loan_id'],'diff_cents':paid[r['loan_id']]-ledger[r['loan_id']]} for r in data['loans']]
    if name=='incremental':return principal(data,cutoff=T2)
    if name=='commerce':return commerce(data)
    if name=='ltv':
        net={r['order_id']:r['net_cents'] for r in commerce(data)}; ltv=defaultdict(int)
        for r in data['orders']:ltv[r['customer_id']]+=net[r['order_id']]
        return [{'customer_id':r['customer_id'],'ltv_cents':ltv[r['customer_id']]} for r in data['customers']]
    if name=='attribution':
        net={r['order_id']:r['net_cents'] for r in commerce(data)}; amount=defaultdict(Decimal)
        for r in data['order_attribution']:amount[r['campaign_id']]+=Decimal(r['weight'])*net[r['order_id']]
        return [{'campaign_id':r['campaign_id'],'attributed_cents':amount[r['campaign_id']]} for r in data['campaigns']]
    if name=='running':
        net={r['order_id']:r['net_cents'] for r in commerce(data)}; sums=defaultdict(int); output=[]
        for r in sorted(data['orders'],key=lambda r:(r['ordered_at'],r['order_id'])):
            sums[r['customer_id']]+=net[r['order_id']]
            output.append({'order_id':r['order_id'],'running_net_cents':sums[r['customer_id']]})
        return output
    if name=='mrr':return mrr(data)
    if name=='expansion':
        before={r['account_id']:r['mrr_cents'] for r in mrr(data,T1)}
        return [{'account_id':r['account_id'],'change_cents':r['mrr_cents']-before[r['account_id']]} for r in mrr(data)]
    if name=='paid_invoices':
        return [{'invoice_id':r['invoice_id'],'amount_cents':r['amount_cents']} for r in data['invoices']
                if r['invoice_id'] in {e['invoice_id'] for e in latest(data['invoice_events'],'invoice_id') if e['status']=='paid'}]
    if name=='retention':
        usage={r['account_id'] for r in data['usage_events'] if T1<=r['event_at']<T2}
        active={r['account_id'] for r in mrr(data) if r['mrr_cents']>0}
        return [{'account_id':r['account_id'],'retained':int(r['account_id'] in usage and r['account_id'] in active)} for r in data['accounts']]
    raise ValueError(f'Unknown oracle {name}')
