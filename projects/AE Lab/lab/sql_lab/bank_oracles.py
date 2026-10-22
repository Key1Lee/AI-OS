"""Independent Python business calculations for 116 authored SQL situations.

No reference SQL is interpreted here. Decimal arithmetic, explicit populations
and ordered event walks provide an independent acceptance oracle.
"""
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
import re
import json

def dt(v):return datetime.fromisoformat(v)
def day(v):return dt(v).date() if 'T' in v else date.fromisoformat(v)
def money(v):return v or 0
def q(v):return Decimal(v).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
def ratio(a,b):return q(Decimal(a)/Decimal(b)) if b else None
def total(rows,col):return sum(money(r[col]) for r in rows)
def group(rows,key):
    out=defaultdict(list)
    for r in rows:out[r[key]].append(r)
    return out
def recent(rows,key):
    out={}
    for r in sorted(rows,key=lambda x:(x['event_at'],x['event_id'])):out[r[key]]=r
    return list(out.values())
def paid(data, cutoff=None):
    rows=data['payment_transactions']
    if cutoff:rows=[r for r in rows if r['received_at']<cutoff]
    return group([r for r in recent(rows,'transaction_id') if r['status']=='posted'],'loan_id')
def net_orders(data):
    refunds=group([r for r in data['refunds'] if r['status']=='posted'],'order_id')
    return {r['order_id']:r['gross_cents']-total(refunds[r['order_id']],'amount_cents') for r in data['orders']}

def _expected_bank(identity, data):
    area,number=identity.split('-')[1:];n=int(number);x=data
    if area=='FND':
        if n==1:return [{'sale_id':r['sale_id'],'sku':r['sku'],'return_cents':-r['cents']} for r in x['sales'] if r['quantity']<0]
        if n==2:return [{'purchase_id':r['purchase_id']} for r in x['purchases'] if r['status']=='completed' and r['cents']>=1000]
        if n==3:return [{'ticket_id':r['ticket_id']} for r in x['tickets'] if r['closed_at'] is None and (r['priority']=='urgent' or r['opened_at']<'2026-10-03T00:00:00+00:00')]
        if n==4:return [{'booking_id':r['booking_id']} for r in x['bookings'] if r['status']=='confirmed' and r['destination'] in ('coast','hill') and 5000<=r['cents']<=10000]
        if n==5:return [{'policy_id':r['policy_id']} for r in x['policies'] if r['starts_at']<='2026-11-01' and (r['ends_at'] is None or '2026-11-01'<r['ends_at'])]
        if n==6:return [{'event_id':r['event_id']} for r in x['wallet_events'] if r['cents'] is None]
        if n==7:return [{'sale_id':r['sale_id'],'bucket':'return' if r['quantity']<0 else 'unknown_discount' if r['discount_cents'] is None else 'discounted' if r['discount_cents']>0 else 'regular'} for r in x['sales']]
        if n==8:return [{'sku':r['sku'],'clean_label':r['label'].strip().lower(),'external_code':r['external_code']} for r in x['products']]
        if n==9:return [{'traveler_id':r['traveler_id'],'email_domain':r['email'].strip().lower().split('@')[1]} for r in x['travelers'] if r['email'] and '@' in r['email']]
        if n==10:return [{'order_id':r['order_id'],'gross_cents':r['gross_cents']} for r in sorted(x['orders'],key=lambda r:(-r['gross_cents'],r['order_id']))[:2]]
    if area=='AGG':
        if n==1:
            scores=[r['csat'] for r in x['tickets'] if r['csat'] is not None]
            return [{'scope':'all','tickets':len(x['tickets']),'rated':len(scores),'avg_score':ratio(sum(scores),len(scores))}]
        if n==2:return [{'store_id':k,'net_cents':total(v,'cents')-total(v,'discount_cents')} for k,v in group(x['sales'],'store_id').items()]
        if n==3:
            groups=group(x['attempts'],'merchant_id')
            return [{'merchant_id':r['merchant_id'],'success_rate':ratio(sum(a['success']==1 for a in groups[r['merchant_id']]),sum(a['success'] is not None for a in groups[r['merchant_id']]))} for r in x['merchants']]
        if n==4:return [{'campaign_id':k,'ctr':ratio(total(v,'clicks'),total(v,'impressions'))} for k,v in group(x['ad_daily'],'campaign_id').items()]
        if n==5:return [{'customer_id':k,'fulfilled_cents':total(v,'gross_cents')} for k,v in group([r for r in x['orders'] if r['status']=='fulfilled'],'customer_id').items() if total(v,'gross_cents')>=5000]
        if n==6:return [{'loan_id':k,'logical_transactions':len({r['transaction_id'] for r in v}),'arrivals':len(v)} for k,v in group(x['payment_transactions'],'loan_id').items()]
        if n==7:return [{'agent_id':k,'tickets':len(v),'open_tickets':sum(r['closed_at'] is None for r in v),'rated':sum(r['csat'] is not None for r in v)} for k,v in group([r for r in x['tickets'] if r['agent_id'] is not None],'agent_id').items()]
        if n==8:
            return [{'destination':k,'min_nights':min((day(r['check_out'])-day(r['check_in'])).days for r in v),'max_nights':max((day(r['check_out'])-day(r['check_in'])).days for r in v)} for k,v in group([r for r in x['bookings'] if r['status']=='confirmed'],'destination').items()]
        if n==9:
            daily=defaultdict(lambda:defaultdict(int))
            for r in x['sales']:daily[r['store_id']][day(r['sold_at'])]+=r['cents']
            return [{'store_id':k,'avg_active_day_cents':ratio(sum(v.values()),len(v))} for k,v in daily.items()]
        if n==10:return [{'policy_id':k,'known_reserve_cents':total(v,'reserve_cents'),'unknown_claims':sum(r['reserve_cents'] is None for r in v),'total_reserve_cents':None if any(r['reserve_cents'] is None for r in v) else total(v,'reserve_cents')} for k,v in group([r for r in x['claims'] if r['status']=='open'],'policy_id').items()]
    if area=='GRN':
        if n==1:
            latest={}
            for r in sorted(x['inventory'],key=lambda r:r['day']):latest[r['store_id'],r['sku']]=r
            return [{'store_id':r['store_id'],'sku':r['sku'],'on_hand':r['on_hand']} for r in latest.values()]
        if n==2:
            last={}
            for r in sorted(x['balances'],key=lambda r:r['day']):
                if r['day']<='2026-10-03':last[r['account_id']]=r['balance_cents']
            return [{'account_id':r['account_id'],'balance_cents':last.get(r['account_id'])} for r in x['accounts']]
        if n==3:
            g=group(x['items'],'order_id')
            return [{'order_id':r['order_id'],'line_cents':total(g[r['order_id']],'line_cents')} for r in x['orders']]
        if n==4:
            g=group([r for r in x['appointments'] if r['status']=='completed'],'clinic_id')
            return [{'clinic_id':r['clinic_id'],'completed_minutes':total(g[r['clinic_id']],'minutes')} for r in x['clinics']]
        if n==5:return [{'seller_id':k,'buyers':len({r['buyer_id'] for r in v})} for k,v in group([r for r in x['purchases'] if r['status']=='completed'],'seller_id').items()]
        if n==6:
            g=defaultdict(int)
            for r in x['loans']:g[r['borrower_id'],r['currency']]+=r['principal_cents']
            return [{'borrower_id':k[0],'currency':k[1],'exposure_cents':v} for k,v in g.items()]
        if n==7:
            g=defaultdict(list)
            for r in x['ad_daily']:g[r['campaign_id'],r['day'][:7]].append(r)
            return [{'campaign_id':k[0],'month':k[1]+'-01','ctr':ratio(total(v,'clicks'),total(v,'impressions'))} for k,v in g.items()]
        if n==8:
            g=defaultdict(int)
            for r in x['sales']:g[r['store_id'],day(r['sold_at']).isoformat()]+=r['cents']
            return [{'store_id':s['store_id'],'day':d['day'],'cents':g[s['store_id'],d['day']]} for s in x['stores'] for d in x['calendar']]
        if n==9:
            g=defaultdict(int)
            for r in x['policies']:
                if r['starts_at']<='2026-11-01' and (r['ends_at'] is None or '2026-11-01'<r['ends_at']):g[r['holder_id']]+=r['premium_cents']
            return [{'holder_id':k,'premium_cents':v} for k,v in g.items()]
        if n==10:
            g=group(x['attempts'],'payment_id')
            return [{'payment_id':k,'latency_ms':max(v,key=lambda r:(r['attempted_at'],r['attempt_id']))['latency_ms']} for k,v in g.items()]
        if n==11:
            acct={r['account_id']:r for r in x['accounts']};g=defaultdict(int)
            for r in x['transactions']:
                a=acct[r['account_id']];g[a['owner_id'],a['currency']]+=money(r['cents'])
            return [{'owner_id':k[0],'currency':k[1],'movement_cents':v} for k,v in g.items()]
        if n==12:
            p=paid(x);c=group(x['charge_offs'],'loan_id')
            return [{'loan_id':r['loan_id'],'outstanding_cents':r['principal_cents']-total(p[r['loan_id']],'principal_cents')-total(c[r['loan_id']],'cents')} for r in x['loans']]
    if area=='JOIN':
        if n==1:
            seen={r['customer_id'] for r in x['orders']}
            return [{'customer_id':r['customer_id']} for r in x['customers'] if r['customer_id'] not in seen]
        if n==2:
            g=group(x['sales'],'store_id')
            return [{'store_id':r['store_id'],'receipt_lines':len(g[r['store_id']])} for r in x['stores']]
        if n==3:
            g=group(x['tickets'],'agent_id')
            return [{'agent_id':r['agent_id'],'avg_csat':ratio(sum(a['csat'] for a in g[r['agent_id']] if a['csat'] is not None),sum(a['csat'] is not None for a in g[r['agent_id']]))} for r in x['agents']]
        if n==4:
            g=group(x['sellers'],'parent_id')
            return [{'seller_id':r['seller_id'],'direct_children':len(g[r['seller_id']])} for r in x['sellers']]
        if n==5:
            p=group([r for r in x['purchases'] if r['status']=='completed'],'seller_id');y=group(x['payouts'],'seller_id')
            return [{'seller_id':r['seller_id'],'unpaid_cents':total(p[r['seller_id']],'cents')-total(y[r['seller_id']],'cents')} for r in x['sellers']]
        if n==6:
            nets=net_orders(x)
            return [{'order_id':r['order_id'],'net_cents':nets[r['order_id']]} for r in x['orders'] if r['status']=='fulfilled']
        if n==7:
            caps=group(x['captures'],'payment_id');ds=group([r for r in x['disputes'] if r['status']=='open'],'payment_id')
            return [{'payment_id':k,'net_exposure_cents':total(caps[k],'cents')-total(ds[k],'cents')} for k in sorted({r['payment_id'] for r in x['attempts']})]
        if n==8:
            a={r['transaction_id']:r['cents'] for r in x['transactions']};b=group(x['statement'],'transaction_id')
            return [{'transaction_id':k,'difference_cents':money(a.get(k))-total(b[k],'cents')} for k in set(a)|set(b)]
        if n==9:
            g=group([r for r in x['claims'] if r['status']=='open'],'policy_id')
            return [{'policy_id':r['policy_id'],'open_claims':len(g[r['policy_id']])} for r in x['policies']]
        if n==10:
            p=group([r for r in x['purchases'] if r['status']=='completed'],'seller_id');g=defaultdict(Decimal)
            for r in x['tags']:g[r['tag']]+=Decimal(r['weight'])*total(p[r['seller_id']],'cents')
            return [{'tag':k,'allocated_cents':q(v)} for k,v in g.items()]
        if n==11:
            g=group([r for r in x['appointments'] if r['status']=='completed'],'clinic_id')
            return [{'clinic_id':r['clinic_id'],'completed_appointments':len(g[r['clinic_id']]),'completed_minutes':total(g[r['clinic_id']],'minutes'),'patients':len({a['patient_id'] for a in g[r['clinic_id']]})} for r in x['clinics']]
        if n==12:
            g=defaultdict(int)
            for r in x['orders']:
                if r['status']=='fulfilled':g[day(r['fulfilled_at']).replace(day=1).isoformat()]+=r['gross_cents']
            return [{'month':k,'recognized_gross_cents':v} for k,v in g.items()]
    if area=='CTE':
        if n==1:
            subs={r['subscription_id']:r['account_id'] for r in x['subscriptions']};g=defaultdict(int)
            for r in x['subscription_versions']:
                if r['status']=='active' and r['valid_from']<='2026-10-03T00:00:00+00:00' and (r['valid_to'] is None or '2026-10-03T00:00:00+00:00'<r['valid_to']):g[subs[r['subscription_id']]]+=r['monthly_cents']
            return [{'account_id':r['account_id'],'mrr_cents':g[r['account_id']]} for r in x['accounts']]
        if n==2:
            g=group([r for r in x['invoices'] if r['status']=='paid'],'subscriber_id')
            return [{'subscriber_id':r['subscriber_id'],'ltv_cents':total(g[r['subscriber_id']],'cents')} for r in x['subscribers']]
        if n==3:
            seen={r['traveler_id'] for r in x['bookings'] if r['status']=='confirmed'}
            return [{'traveler_id':r['traveler_id']} for r in x['travelers'] if r['traveler_id'] not in seen]
        if n==4:
            pos={r['sku'] for r in x['sales'] if r['quantity']>0};neg={r['sku'] for r in x['sales'] if r['quantity']<0}
            return [{'sku':k} for k in pos&neg]
        if n==5:return [{'transaction_id':k} for k in {r['transaction_id'] for r in x['statement']}-{r['transaction_id'] for r in x['transactions']}]
        if n==6:return [{'payment_id':r['payment_id'],'attempt_id':r['attempt_id']} for r in x['attempts'] if r['metadata'].get('channel') in ('web','app')]
        if n==7:return [{'customer_id':k} for k in {r['customer_id'] for r in x['orders']}|{r['customer_id'] for r in x['events']}]
        if n==8:return [{'attempt_id':r['attempt_id'],'risk':int(str(r['metadata']['risk'])) if re.fullmatch(r'[0-9]+',str(r['metadata'].get('risk'))) else None} for r in x['attempts']]
        if n==9:
            g=defaultdict(int)
            for r in x['risk_events']:
                for s in r['signals']:g[s]+=1
            return [{'signal':k,'observations':v} for k,v in g.items()]
        if n==10:
            result=[]
            for r in x['conversions']:
                touches=[a for a in x['touches'] if a['user_id']==r['user_id'] and dt(r['converted_at'])-timedelta(days=7)<=dt(a['touched_at'])<=dt(r['converted_at'])]
                chosen=max(touches,key=lambda a:(a['touched_at'],a['touch_id']),default=None)
                result.append({'conversion_id':r['conversion_id'],'campaign_id':chosen['campaign_id'] if chosen else None})
            return result
    if area=='WIN':
        if n==1:
            result=[]
            for k,v in group(x['transactions'],'account_id').items():
                running=0
                for r in sorted(v,key=lambda r:(r['posted_at'],r['transaction_id'])):
                    running+=money(r['cents']);result.append({'transaction_id':r['transaction_id'],'running_cents':running})
            return result
        if n==2:
            g=defaultdict(lambda:defaultdict(int));result=[]
            for r in x['sales']:g[r['store_id']][r['sku']]+=r['cents']
            for s,values in g.items():
                scores=sorted(set(values.values()),reverse=True)
                result.extend({'store_id':s,'sku':k,'value_rank':scores.index(v)+1} for k,v in values.items())
            return result
        if n==3:
            groups=group(x['sellers'],'region');p=group([r for r in x['purchases'] if r['status']=='completed'],'seller_id');result=[]
            for region,v in groups.items():
                ranked=sorted(v,key=lambda r:(-total(p[r['seller_id']],'cents'),r['seller_id']))[:2]
                result.extend({'region':region,'seller_id':r['seller_id'],'position':i+1} for i,r in enumerate(ranked))
            return result
        if n==4:
            g=group([r for r in x['ticket_events'] if r['action']=='replied'],'ticket_id')
            return [{'ticket_id':r['ticket_id'],'first_reply_at':min((a['event_at'] for a in g[r['ticket_id']]),default=None)} for r in x['tickets']]
        if n==5:
            result=[]
            for k,v in group(x['shipment_events'],'shipment_id').items():
                v=sorted(v,key=lambda r:(r['event_at'],r['event_id']))
                result.extend({'event_id':r['event_id'],'next_event_at':v[i+1]['event_at'] if i+1<len(v) else None} for i,r in enumerate(v))
            return result
        if n==6:
            result=[]
            for k,v in group([r for r in x['invoices'] if r['status']=='paid'],'subscriber_id').items():
                v=sorted(v,key=lambda r:(r['invoiced_at'],r['invoice_id']))
                result.extend({'invoice_id':r['invoice_id'],'moving_cents':ratio(sum(a['cents'] for a in v[max(0,i-1):i+1]),len(v[max(0,i-1):i+1]))} for i,r in enumerate(v))
            return result
        if n==7:
            g=group(x['attempts'],'merchant_id')
            return [{'attempt_id':r['attempt_id'],'merchant_attempts':len(g[r['merchant_id']])} for r in x['attempts']]
        if n==8:
            result=[]
            for k,v in group(x['orders'],'customer_id').items():
                v=sorted(v,key=lambda r:(r['ordered_at'],r['order_id']))
                result.extend({'order_id':r['order_id'],'prior_gross_cents':v[i-1]['gross_cents'] if i else None} for i,r in enumerate(v))
            return result
        if n==9:
            g=group(x['transactions'],'account_id')
            return [{'transaction_id':r['transaction_id'],'final_cents':max(g[r['account_id']],key=lambda a:(a['posted_at'],a['transaction_id']))['cents']} for r in x['transactions']]
        if n==10:
            result=[]
            for k,v in group([r for r in x['attempts'] if r['latency_ms'] is not None],'merchant_id').items():
                a=sorted(r['latency_ms'] for r in v);m=len(a)//2
                result.append({'merchant_id':k,'median_ms':q(a[m] if len(a)%2 else Decimal(a[m-1]+a[m])/2)})
            return result
        if n==11:
            result=[]
            for k,v in group(x['sales'],'store_id').items():
                running=0
                for r in sorted(v,key=lambda a:(a['sold_at'],a['sale_id'])):
                    running+=r['cents'];peers=sum(a['cents'] for a in v if a['sold_at']<=r['sold_at'])
                    result.append({'sale_id':r['sale_id'],'row_total':running,'peer_total':peers})
            return result
        if n==12:
            a=sorted([r for r in x['attempts'] if r['latency_ms'] is not None],key=lambda r:(r['latency_ms'],r['attempt_id']));nrows=len(a);size,extra=divmod(nrows,4);result=[];i=0
            for bucket in range(1,5):
                for _ in range(size+(bucket<=extra)):
                    result.append({'attempt_id':a[i]['attempt_id'],'quartile':bucket});i+=1
            return result
    if area=='DED':
        if n==1:
            p=paid(x)
            return [{'loan_id':r['loan_id'],'paid_cents':total(p[r['loan_id']],'principal_cents')} for r in x['loans']]
        if n==2:return [{'transfer_id':r['transfer_id'],'wallet_id':r['wallet_id'],'cents':r['cents']} for r in recent(x['wallet_events'],'transfer_id') if r['status']=='posted']
        if n==3:
            g={r['shipment_id']:r for r in recent(x['shipment_events'],'shipment_id')}
            return [{'shipment_id':r['shipment_id']} for r in x['shipments'] if g.get(r['shipment_id'],{}).get('status')=='delivered']
        if n==4:
            current={r['claim_id']:r['status'] for r in recent(x['claim_events'],'claim_id')}
            return [{'claim_id':r['claim_id'],'reserve_cents':r['reserve_cents']} for r in x['claims'] if current.get(r['claim_id'])=='open']
        if n==5:
            current=recent(x['subscription_events'],'subscriber_id');g=group(current,'status')
            return [{'status':k,'subscribers':len(v)} for k,v in g.items()]
        if n==6:return [{'customer_id':a,'event_type':b,'event_at':c} for a,b,c in {(r['customer_id'],r['event_type'],r['event_at']) for r in x['events']}]
        if n==7:
            p=paid(x,'2026-10-04T00:00:00+00:00')
            return [{'loan_id':r['loan_id'],'known_paid_cents':total(p[r['loan_id']],'principal_cents')} for r in x['loans']]
        if n==8:
            g={r['loan_id']:r['status'] for r in recent([r for r in x['loan_status_history'] if r['event_at']<'2026-10-03T00:00:00+00:00'],'loan_id')}
            return [{'loan_id':r['loan_id'],'status':g.get(r['loan_id'])} for r in x['loans']]
    if area=='DATE':
        if n==1:return [{'order_id':r['order_id']} for r in x['orders'] if '2026-10-01T00:00:00+00:00'<=r['ordered_at']<'2026-11-01T00:00:00+00:00']
        if n==2:
            g=defaultdict(int)
            for r in x['ad_daily']:
                year,week,_=day(r['day']).isocalendar();g[r['campaign_id'],year,week]+=r['clicks']
            return [{'campaign_id':k[0],'iso_year':k[1],'iso_week':k[2],'clicks':v} for k,v in g.items()]
        if n==3:
            g=defaultdict(int)
            for r in x['sales']:
                at=day(r['sold_at']);fy=at.year if at.month>=7 else at.year-1;fq=((at.month-7)%12)//3+1;g[r['store_id'],fy,fq]+=r['cents']
            return [{'store_id':k[0],'fiscal_year':k[1],'fiscal_quarter':k[2],'cents':v} for k,v in g.items()]
        if n in (4,5):
            zones={r['clinic_id']:ZoneInfo(r['timezone']) for r in x['clinics']};g=defaultdict(int)
            for r in x['appointments']:
                if r['status']!='completed':continue
                local=dt(r['scheduled_at']).astimezone(zones[r['clinic_id']])
                key=(r['clinic_id'],local.date().isoformat(),local.hour) if n==4 else (r['clinic_id'],(local-timedelta(hours=9)).date().isoformat())
                g[key]+=1
            return [({'clinic_id':k[0],'local_day':k[1],'local_hour':k[2],'appointments':v} if n==4 else {'clinic_id':k[0],'service_day':k[1],'appointments':v}) for k,v in g.items()]
        if n==6:
            g=defaultdict(int)
            for r in x['orders']:
                if r['status']=='fulfilled':g[day(r['fulfilled_at'])]+=r['gross_cents']
            return [{'day':r['day'],'rolling_cents':sum(v for k,v in g.items() if day(r['day'])-timedelta(days=6)<=k<=day(r['day']))} for r in x['calendar']]
        if n==7:
            result=[]
            for k,v in group(x['activity'],'subscriber_id').items():
                days=sorted(day(r['day']) for r in v);start=prior=days[0]
                for current in days[1:]+[None]:
                    if current is None or current!=prior+timedelta(days=1):
                        result.append({'subscriber_id':k,'start_day':start.isoformat(),'end_day':prior.isoformat(),'streak_days':(prior-start).days+1});start=current
                    prior=current
            return result
        if n==8:return [{'policy_id':r['policy_id'],'coverage_days':(day(r['ends_at'])-day(r['starts_at'])).days} for r in x['policies'] if r['ends_at'] is not None]
    if area=='PAT':
        if n==1:
            g=group(x['events'],'customer_id');result=[]
            for r in x['customers']:
                events=g[r['customer_id']];views=[a for a in events if a['event_type']=='view'];converted=False
                for v in views:
                    for c in events:
                        if c['event_type']=='cart' and dt(v['event_at'])<dt(c['event_at']):
                            converted|=any(p['event_type']=='purchase' and dt(c['event_at'])<dt(p['event_at'])<=dt(v['event_at'])+timedelta(hours=24) for p in events)
                result.append({'customer_id':r['customer_id'],'eligible':int(bool(views)),'converted':int(converted)})
            return result
        if n in (2,3):
            g=group(x['subscribers'],'joined_at');active={(r['subscriber_id'],day(r['day'])) for r in x['activity']};result=[]
            for k,v in g.items():
                joined=day(k);retained=sum(any((r['subscriber_id'],joined+timedelta(days=i)) in active for i in ([1] if n==2 else [1,2,3])) for r in v)
                result.append({'cohort_day':joined.isoformat(),'subscribers':len(v),'retained':retained,'retention_rate':ratio(retained,len(v))})
            return result
        if n==4:
            g=defaultdict(list);invoices=group([r for r in x['invoices'] if r['status']=='paid'],'subscriber_id')
            for r in x['subscribers']:g[day(r['joined_at']).replace(day=1).isoformat()].append(r)
            return [{'cohort_month':k,'subscribers':len(v),'ltv_cents':sum(total(invoices[r['subscriber_id']],'cents') for r in v),'avg_ltv_cents':ratio(sum(total(invoices[r['subscriber_id']],'cents') for r in v),len(v))} for k,v in g.items()]
        if n==5:
            touches={r['conversion_id']:r['campaign_id'] for r in expected_bank('SQL-CTE-010',x)};g=defaultdict(int);spend=group(x['ad_daily'],'campaign_id')
            for r in x['conversions']:
                if touches[r['conversion_id']]:g[touches[r['conversion_id']]]+=r['value_cents']
            return [{'campaign_id':r['campaign_id'],'attributed_cents':g[r['campaign_id']],'roas':ratio(g[r['campaign_id']],total(spend[r['campaign_id']],'spend_cents'))} for r in x['campaigns']]
        if n==6:
            p=paid(x);s=group(x['scheduled_payments'],'loan_id');result=[];asof=date(2026,10,6)
            for r in x['loans']:
                paid_cents=total(p[r['loan_id']],'principal_cents');cumulative=0;first=None
                for a in sorted(s[r['loan_id']],key=lambda a:(a['due_at'],a['schedule_id'])):
                    cumulative+=a['due_cents']
                    if day(a['due_at'])<asof and cumulative>paid_cents and first is None:first=day(a['due_at'])
                result.append({'loan_id':r['loan_id'],'days_past_due':(asof-first).days if first else 0})
            return result
        if n==7:
            g=defaultdict(int);eligible={r['order_id'] for r in x['orders'] if r['status']=='fulfilled'}
            for r in x['orders']:
                if r['order_id'] in eligible:g[day(r['fulfilled_at']).replace(day=1).isoformat()]+=r['gross_cents']
            for r in x['refunds']:
                if r['order_id'] in eligible and r['status']=='posted':g[day(r['refund_at']).replace(day=1).isoformat()]-=money(r['amount_cents'])
            return [{'month':k,'recognized_net_cents':v} for k,v in g.items()]
        if n==8:
            buyers=group([r for r in x['purchases'] if r['status']=='completed'],'buyer_id');cohorts=defaultdict(list)
            for k,v in buyers.items():
                v=sorted(v,key=lambda r:(r['bought_at'],r['purchase_id']));first=dt(v[0]['bought_at']);repeat=any(first<dt(r['bought_at'])<=first+timedelta(days=7) for r in v[1:]);cohorts[first.date().replace(day=1).isoformat()].append(repeat)
            return [{'cohort_month':k,'buyers':len(v),'repeat_buyers':sum(v),'repeat_rate':ratio(sum(v),len(v))} for k,v in cohorts.items()]
    if area=='ADV':
        if n==1:
            closed=group([r for r in x['tickets'] if r['closed_at'] is not None],'agent_id')
            return [{'agent_id':r['agent_id'],'closed_tickets':len(closed[r['agent_id']])} for r in x['agents']]
        if n==2:return expected_bank('SQL-WIN-001',x)
        if n==3:return expected_bank('SQL-JOIN-011',x)
        if n==4:
            seen={r['agent_id'] for r in x['tickets'] if r['closed_at'] is not None}
            return [{'agent_id':r['agent_id']} for r in x['agents'] if r['agent_id'] not in seen]
        if n==5:
            caps=group(x['captures'],'merchant_id');by_payment={r['payment_id']:r['merchant_id'] for r in x['attempts']};ds=defaultdict(int)
            for r in x['disputes']:
                if r['status']=='open' and r['payment_id'] in by_payment:ds[by_payment[r['payment_id']]]+=r['cents']
            return [{'merchant_id':r['merchant_id'],'dispute_rate':ratio(ds[r['merchant_id']],total(caps[r['merchant_id']],'cents'))} for r in x['merchants']]
        if n==6:
            g=defaultdict(int)
            for r in x['sales']:
                if date(2026,10,1)<=day(r['sold_at'])<date(2026,11,1):g[r['store_id']]+=r['cents']
            return [{'store_id':k,'cents':v} for k,v in g.items()]
        if n==7:
            result=[]
            for k,v in group([r for r in x['tickets'] if r['csat'] is not None],'agent_id').items():
                v=sorted(v,key=lambda r:(r['opened_at'],r['ticket_id']))
                result.extend({'ticket_id':r['ticket_id'],'moving_csat':ratio(sum(a['csat'] for a in v[max(0,i-1):i+1]),len(v[max(0,i-1):i+1]))} for i,r in enumerate(v))
            return result
        if n==8:
            p=paid(x);c=group(x['charge_offs'],'loan_id');g=defaultdict(lambda:[0,0])
            for r in x['loans']:
                rows=p[r['loan_id']];k=(r['borrower_id'],r['currency']);g[k][0]+=r['principal_cents']-total(rows,'principal_cents')-total(c[r['loan_id']],'cents');g[k][1]+=sum(a['principal_cents'] is None for a in rows)
            return [{'borrower_id':k[0],'currency':k[1],'known_outstanding_cents':v[0],'unknown_payments':v[1],'certified_outstanding_cents':None if v[1] else v[0]} for k,v in g.items()]
        if n==9:return expected_bank('SQL-PAT-007',x)
        if n==10:
            claims=group([r for r in x['claims'] if r['status']=='open'],'policy_id');g=defaultdict(lambda:[0,0])
            for r in x['policies']:
                g[r['holder_id']][0]+=total(claims[r['policy_id']],'reserve_cents');g[r['holder_id']][1]+=sum(a['reserve_cents'] is None for a in claims[r['policy_id']])
            return [{'holder_id':k,'known_reserve_cents':v[0],'unknown_claims':v[1]} for k,v in g.items()]
    if area=='XFR':
        if n==1:
            g=group(x['payments'],'loan_id');out=[]
            for loan in x['loans']:
                rows=g[loan['loan_id']];known=[r for r in rows if r['principal_paid_cents'] is not None];cents=total(known,'principal_paid_cents')
                out.append({'loan_id':loan['loan_id'],'payment_rows':len(rows),'known_rows':len(known),'known_cents':cents,
                    'state':'no_records' if not rows else 'unknown' if len(known)<len(rows) else 'zero' if cents==0 else 'known'})
            return out
        if n==2:
            out=[]
            for k,v in group(x['events'],'customer_id').items():
                prior=None;session=0
                for r in sorted(v,key=lambda a:(a['event_at'],a['event_id'])):
                    current=dt(r['event_at'])
                    if prior is None or current-prior>timedelta(minutes=30):session+=1
                    out.append({'event_id':r['event_id'],'session_no':session});prior=current
            return out
        if n==3:
            g=defaultdict(int)
            for r in x['orders']:
                if r['status']=='fulfilled':g[day(r['fulfilled_at']).replace(day=1)]+=r['gross_cents']
            out=[]
            for k,v in g.items():
                prior=g.get((k-timedelta(days=1)).replace(day=1))
                out.append({'month':k.isoformat(),'cents':v,'prior_cents':prior,'mom_rate':ratio(v-prior,prior) if prior is not None else None})
            return out
        if n==4:return [{'sku':r['sku'],'normalized_code':r['external_code'].strip().upper().replace('-','') if r['external_code'] is not None else None,'display_prefix':r['label'].strip()[:3]+':'+r['sku']} for r in x['products']]
        if n==5:
            g=defaultdict(lambda:defaultdict(int));out=[]
            for r in x['sales']:g[r['store_id']][r['sku']]+=r['cents']
            for store,products in g.items():
                for sku,cents in products.items():
                    rank=1+sum(v>cents for v in products.values())
                    if rank<=2:out.append({'store_id':store,'sku':sku,'value_rank':rank})
            return out
        if n in (6,7):
            g=defaultdict(list);active=group(x['activity'],'subscriber_id')
            for r in x['subscribers']:
                joined=day(r['joined_at']);start=joined-timedelta(days=joined.weekday()) if n==6 else joined.replace(day=1)
                g[start].append(r)
            out=[]
            for start,rows in g.items():
                if n==6:lo=start+timedelta(days=7);hi=lo+timedelta(days=7)
                else:
                    lo=(start+timedelta(days=32)).replace(day=1);hi=(lo+timedelta(days=32)).replace(day=1)
                retained=sum(any(lo<=day(a['day'])<hi for a in active[r['subscriber_id']]) for r in rows)
                out.append({('cohort_week' if n==6 else 'cohort_month'):start.isoformat(),'subscribers':len(rows),'retained':retained})
            return out
        if n==8:return [{'attempt_id':r['attempt_id'],'product':item['product'],'units':int(item['units']) if item.get('units') is not None else None} for r in x['attempts'] for item in r['metadata'].get('items',[])]
        if n==9:
            p=group(x['payments'],'schedule_id');d={r['loan_id']:r['days_past_due'] for r in x['delinquencies'] if r['as_of']=='2026-10-06'}
            return [{'schedule_id':r['schedule_id'],'unpaid_cents':max(0,r['due_cents']-total(p[r['schedule_id']],'principal_paid_cents')),'snapshot_dpd':d.get(r['loan_id'])} for r in x['scheduled_payments'] if r['due_at']<'2026-10-06T00:00:00+00:00']
        if n==10:
            out=[]
            for k,v in group(x['shipment_events'],'shipment_id').items():
                v=sorted(v,key=lambda r:(r['event_at'],r['event_id']))
                if len(v)>=2:out.append({'shipment_id':k,'second_event_id':v[1]['event_id']})
            return out
        if n==11:return [{'merchant_id':k,'success_pct':ratio(100*sum(r['success']==1 for r in v),sum(r['success'] is not None for r in v))} for k,v in group(x['attempts'],'merchant_id').items()]
        if n==12:
            owners={r['account_id']:r['owner_id'] for r in x['accounts']}
            return [{'transaction_id':r['transaction_id'],'owner_id':owners[r['account_id']]} for r in x['transactions']]
        if n==13:
            g=group(x['attempts'],'merchant_id');out=[]
            for r in x['merchants']:
                values=[Decimal(a['metadata']['settled_amount']) for a in g[r['merchant_id']] if a['metadata'].get('settled_amount') is not None]
                out.append({'merchant_id':r['merchant_id'],'settled_amount':sum(values,Decimal(0)) if values else None})
            return out
        if n==14:
            g=defaultdict(int)
            for r in x['ad_daily']:
                at=day(r['day']);g[r['campaign_id'],at-timedelta(days=at.weekday())]+=r['clicks']
            return [{'campaign_id':k[0],'week':k[1].isoformat(),'clicks':v,'prior_clicks':g.get((k[0],k[1]-timedelta(days=7))),
                     'wow_rate':ratio(v-g[k[0],k[1]-timedelta(days=7)],g[k[0],k[1]-timedelta(days=7)]) if (k[0],k[1]-timedelta(days=7)) in g else None} for k,v in g.items()]
        if n==15:
            g=defaultdict(int)
            for r in x['sales']:g[r['store_id'],day(r['sold_at']).replace(day=1)]+=r['cents']
            out=[]
            for (store,month),cents in g.items():
                prior=g.get((store,month.replace(year=month.year-1)))
                out.append({'store_id':store,'month':month.isoformat(),'cents':cents,'prior_year_cents':prior,'yoy_rate':ratio(cents-prior,prior) if prior is not None else None})
            return out
        if n==16:
            g=group(x['events'],'customer_id');out=[]
            for customer in x['customers']:
                events=g[customer['customer_id']];views=[r for r in events if r['event_type']=='view' and r['event_at']>=customer['signup_at']]
                converted=any(p['event_type']=='purchase' and dt(v['event_at'])<dt(p['event_at'])<=dt(v['event_at'])+timedelta(hours=24) for v in views for p in events)
                out.append({'customer_id':customer['customer_id'],'eligible':int(bool(views)),'converted':int(converted)})
            return out
    raise ValueError(f'Unknown SQL bank oracle {identity}')


def expected_bank(identity,data):
    rows=_expected_bank(identity,data)
    # SQL rowsets are unordered unless the consumer explicitly requests order.
    # Stable serialization is essential for private cross-process digests.
    return rows if identity=='SQL-FND-010' else sorted(rows,key=lambda r:json.dumps(r,sort_keys=True,default=str))
