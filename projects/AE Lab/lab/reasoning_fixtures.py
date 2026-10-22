"""Synthetic business evidence, reusing Step 2 source snapshots by copy.

These are exercise calculations, not governed metrics or production policies.
"""
from copy import deepcopy
from collections import defaultdict,Counter
from decimal import Decimal, ROUND_HALF_UP
from .sql_lab.datasets import fixture as sql_fixture,DOMAINS

VARIANTS=('sample','edge','revisit')
LINKS={'commerce':'commerce','saas':'saas','payments':'payments','logistics':'logistics','marketing':'advertising'}

def at(day):return f'2026-10-{day:02d}T00:00:00+00:00'
def ratio(n,d):return None if not d else str((Decimal(n)/Decimal(d)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def groups(rows,key):
 out=defaultdict(list)
 for r in rows:out[r[key]].append(r)
 return out
def total(rows,key):return sum(Decimal(str(r[key])) for r in rows if r[key] is not None)
def latest(rows,key,time='event_at'):
 out={}
 for r in sorted(rows,key=lambda r:(r[time],r.get('event_id',r.get('attempt_id','')))):out[r[key]]=r
 return list(out.values())
def active(r,day,start='starts_at',end='ends_at'):return r[start]<=day and (r[end] is None or day<r[end])

def fixture(domain,variant='sample'):
 if variant not in VARIANTS:raise ValueError('Unknown reasoning fixture')
 bad=variant!='sample'
 x=sql_fixture(LINKS[domain],'clean' if not bad else 'adversarial',1 if variant!='revisit' else 2) if domain in LINKS else {}
 if domain=='saas':
  x['revenue_movements']=[dict(account_id='A1',opening_cents=10000,closing_cents=12000),dict(account_id='A2',opening_cents=8000,closing_cents=0),dict(account_id='A3',opening_cents=2000,closing_cents=1500),dict(account_id='A4',opening_cents=0,closing_cents=5000)]
  if bad:x['revenue_movements']+=[dict(account_id='A5',opening_cents=1000,closing_cents=None)]
 elif domain=='marketing':
  x['leads']=[dict(lead_id='L1',user_id='U1',created_at=at(1),segment='enterprise',email='a@demo.test'),dict(lead_id='L2',user_id='U2',created_at=at(2),segment='startup',email='b@demo.test'),dict(lead_id='L3',user_id='U3',created_at=at(2),segment='enterprise',email=None)]
  x['lead_states']=[dict(event_id=1,lead_id='L1',status='qualified',event_at=at(2)),dict(event_id=2,lead_id='L2',status='new',event_at=at(2)),dict(event_id=3,lead_id='L3',status='new',event_at=at(2))]
  x['lead_credit']=[dict(credit_id='C1',lead_id='L1',campaign_id='K1',weight='0.6'),dict(credit_id='C2',lead_id='L1',campaign_id='K2',weight='0.4'),dict(credit_id='C3',lead_id='L2',campaign_id='K2',weight='1')]
  x['lead_deliveries']=[dict(delivery_id=1,lead_id='L1',email=' A@DEMO.TEST '),dict(delivery_id=2,lead_id='L2',email='b@demo.test')]
  x['segment_history']=[dict(version_id='V1',lead_id='L1',segment='startup',valid_from=at(1),valid_to=at(3)),dict(version_id='V2',lead_id='L1',segment='enterprise',valid_from=at(3),valid_to=None)]
  if bad:
   x['lead_states']+=[dict(event_id=4,lead_id='L1',status='disqualified',event_at=at(4)),dict(event_id=5,lead_id='L2',status='qualified',event_at=at(4))]
   x['lead_credit']+=[dict(credit_id='C4',lead_id='L3',campaign_id='K1',weight='0.8'),dict(credit_id='C5',lead_id='L3',campaign_id='K2',weight='0.5')]
   x['lead_deliveries']+=[dict(delivery_id=3,lead_id='L1',email='a@demo.test'),dict(delivery_id=4,lead_id='L3',email=None)]
 elif domain=='iot':
  x={'devices':[dict(device_id='D1',account_id='A2',commissioned_at=at(1)),dict(device_id='D2',account_id='A1',commissioned_at=at(1)),dict(device_id='D3',account_id='A1',commissioned_at=at(1))],
   'heartbeats':[dict(delivery_id=1,event_id='E1',device_id='D1',event_at=at(2),received_at=at(2),healthy=True),dict(delivery_id=2,event_id='E2',device_id='D2',event_at=at(2),received_at=at(2),healthy=False),dict(delivery_id=3,event_id='E3',device_id='D1',event_at=at(3),received_at=at(3),healthy=True)],
   'intervals':[dict(interval_id='I1',device_id='D1',start_at=at(1),end_at=at(2),monitored_minutes=60,up_minutes=60),dict(interval_id='I2',device_id='D1',start_at=at(2),end_at=at(3),monitored_minutes=60,up_minutes=30),dict(interval_id='I3',device_id='D2',start_at=at(1),end_at=at(2),monitored_minutes=60,up_minutes=30)],
   'memberships':[dict(version_id='V1',device_id='D1',account_id='A1',valid_from=at(1),valid_to=at(3)),dict(version_id='V2',device_id='D1',account_id='A2',valid_from=at(3),valid_to=None),dict(version_id='V3',device_id='D2',account_id='A1',valid_from=at(1),valid_to=None)],
   'trips':[dict(trip_id='T1',device_id='D1',started_at=at(2),km=20),dict(trip_id='T2',device_id='D1',started_at=at(3),km=30),dict(trip_id='T3',device_id='D2',started_at=at(2),km=10)]}
  if bad:
   x['heartbeats']+=[dict(delivery_id=4,event_id='E1',device_id='D1',event_at=at(2),received_at=at(4),healthy=True),dict(delivery_id=5,event_id='E4',device_id='D3',event_at=at(2),received_at=at(5),healthy=None)]
   x['intervals']+=[dict(interval_id='I4',device_id='D2',start_at=at(2),end_at=at(3),monitored_minutes=60,up_minutes=None)]
 elif domain=='workforce':
  x={'people':[dict(person_id='P1',name='Mira'),dict(person_id='P2',name='Bo'),dict(person_id='P3',name='Kai')],
   'employments':[dict(employment_id='E1',person_id='P1',kind='employee',starts_at=at(1),ends_at=None),dict(employment_id='E2',person_id='P2',kind='employee',starts_at=at(1),ends_at=at(3)),dict(employment_id='E3',person_id='P3',kind='employee',starts_at=at(3),ends_at=None)],
   'assignments':[dict(assignment_id='A1',employment_id='E1',team='red',fte='0.6',valid_from=at(1),valid_to=None),dict(assignment_id='A2',employment_id='E1',team='blue',fte='0.4',valid_from=at(1),valid_to=None),dict(assignment_id='A3',employment_id='E2',team='red',fte='1',valid_from=at(1),valid_to=at(3)),dict(assignment_id='A4',employment_id='E3',team='blue',fte='1',valid_from=at(3),valid_to=None)],
   'time_entries':[dict(entry_id='T1',employment_id='E1',day='2026-10-02',hours=8),dict(entry_id='T2',employment_id='E1',day='2026-10-02',hours=2),dict(entry_id='T3',employment_id='E2',day='2026-10-02',hours=8)]}
  if bad:
   x['employments']+=[dict(employment_id='E4',person_id='P1',kind='contractor',starts_at=at(2),ends_at=None)]
   x['assignments']+=[dict(assignment_id='A5',employment_id='E4',team='red',fte=None,valid_from=at(2),valid_to=None)]
   x['time_entries']+=[dict(entry_id='T4',employment_id='E4',day='2026-10-02',hours=3)]
 elif domain=='ai':
  x={'users':[dict(user_id='U1',account_id='A1',internal=False),dict(user_id='U2',account_id='A1',internal=False),dict(user_id='U3',account_id='A2',internal=True)],
   'tasks':[dict(task_id='T1',user_id='U1',created_at=at(1),eligible=True),dict(task_id='T2',user_id='U1',created_at=at(2),eligible=True),dict(task_id='T3',user_id='U2',created_at=at(3),eligible=True),dict(task_id='T4',user_id='U3',created_at=at(3),eligible=False)],
   'attempts':[dict(attempt_id='A1',task_id='T1',finished_at=at(2),status='succeeded',approved=True,model_version='M1'),dict(attempt_id='A2',task_id='T2',finished_at=at(2),status='succeeded',approved=True,model_version='M1'),dict(attempt_id='A3',task_id='T2',finished_at=at(3),status='failed',approved=False,model_version='M2')],
   'tool_calls':[dict(call_id='C1',attempt_id='A1',cost_cents=5),dict(call_id='C2',attempt_id='A1',cost_cents=5),dict(call_id='C3',attempt_id='A2',cost_cents=10),dict(call_id='C4',attempt_id='A3',cost_cents=20)],
   'feedback':[dict(feedback_id='F1',task_id='T1',score=5),dict(feedback_id='F2',task_id='T2',score=None)],
   'model_versions':[dict(model_version='M1',family='small'),dict(model_version='M2',family='large')]}
  if bad:
   x['attempts']+=[dict(attempt_id='A4',task_id='T3',finished_at=at(4),status='succeeded',approved=False,model_version='M2')]
   x['tool_calls']+=[dict(call_id='C5',attempt_id='A4',cost_cents=0)]
 elif domain=='logistics' and bad:
  x['shipment_events'].append(dict(event_id=999,shipment_id='MISSING',status='delivered',event_at=at(3),received_at=at(4)))
 if variant=='revisit':
  # Change business evidence, not only physical order. Old numeric answers must
  # not substitute for a fresh inference in the same case.
  if domain=='iot':x['intervals'][0]['up_minutes']=30
  elif domain=='ai':x['attempts'][0]['approved']=False
  elif domain=='workforce':x['time_entries'][0]['hours']=6
  elif domain=='marketing':x['lead_states'].append(dict(event_id=9,lead_id='L3',status='qualified',event_at=at(4)))
  elif domain=='saas':x['revenue_movements'][0]['closing_cents']=9000
  for rows in x.values():rows.reverse()
 return deepcopy(x)

def schemas(domain,data):
 out=[]
 for name,rows in data.items():
  if domain in LINKS and name in {t.name for t in DOMAINS[LINKS[domain]].tables}:
   definition=DOMAINS[LINKS[domain]].table(name);cols=definition.columns
  else:
   cols={k:('boolean' if isinstance(v,bool) else 'numeric' if isinstance(v,(int,float)) else 'text') for r in rows for k,v in r.items()}
  out.append({'name':name,'columns':cols})
 return out


def facts(domain,x):
 """Explicit business calculations used only by authored assessment fixtures."""
 f={}
 if domain=='commerce':
  orders=x['orders'];fulfilled=[r for r in orders if r['status']=='fulfilled'];ids={r['order_id'] for r in fulfilled};refs=[r for r in x['refunds'] if r['status']=='posted' and r['order_id'] in ids]
  itemg=groups(x['items'],'order_id');rg=groups(x['refunds'],'order_id')
  f.update(order_key=['order_id'],item_key=['item_id'],output_order=['order_id'],customer_key=['customer_id'],relationship='1:M',
   orders=len(orders),fulfilled=len(fulfilled),gross=str(total(fulfilled,'gross_cents')),refunds=str(total(refs,'amount_cents')),net=str(total(fulfilled,'gross_cents')-total(refs,'amount_cents')),
   aov=ratio(total(fulfilled,'gross_cents'),len(fulfilled)),buyers=len({r['customer_id'] for r in fulfilled}),customers=len(x['customers']),
   conversion=ratio(len({r['customer_id'] for r in fulfilled}),len(x['customers'])),
   joined_rows=sum(max(1,len(itemg[r['order_id']])) for r in orders),
   two_child_rows=sum(max(1,len(itemg[r['order_id']]))*max(1,len(rg[r['order_id']])) for r in orders),
   multiplied_gross=str(sum(Decimal(r['gross_cents'])*max(1,len(itemg[r['order_id']])) for r in fulfilled)),
   item_gross=str(total([r for r in x['items'] if r['order_id'] in ids],'line_cents')),distinct_amount_total=str(sum({r['gross_cents'] for r in fulfilled})))
  from .sql_lab.bank_oracles import expected_bank
  required=expected_bank('SQL-PAT-001',x);optional=expected_bank('SQL-XFR-016',x)
  f.update(funnel_eligible=sum(r['eligible'] for r in required),funnel_converted=sum(r['converted'] for r in required),optional_converted=sum(r['converted'] for r in optional))
 elif domain=='saas':
  from .sql_lab.oracles import mrr
  rows=x['revenue_movements'];opening=[r for r in rows if r['opening_cents']>0];unknown=sum(r['closing_cents'] is None for r in opening)
  start=total(opening,'opening_cents');end=total(opening,'closing_cents');grr=sum(min(Decimal(r['opening_cents']),Decimal(r['closing_cents'])) for r in opening if r['closing_cents'] is not None)
  states={r['invoice_id']:r for r in latest(x['invoice_events'],'invoice_id')};paid=[r for r in x['invoices'] if states.get(r['invoice_id'],{}).get('status')=='paid']
  f.update(account_key=['account_id'],subscription_key=['subscription_id'],version_key=['version_id'],account_count=len(x['accounts']),
   subscription_rows=len(x['subscriptions']),relationship='1:M',mrr=str(total(mrr(x),'mrr_cents')),invoice_paid=str(total(paid,'amount_cents')),
   eligible_accounts=len(opening),churned=sum(r['closing_cents']==0 for r in opening),churn=ratio(sum(r['closing_cents']==0 for r in opening),len(opening)),
   opening=str(start),closing_known=str(end),unknown_closing=unknown,nrr=None if unknown else ratio(end,start),grr=None if unknown else ratio(grr,start),
   new_revenue=str(total([r for r in rows if r['opening_cents']==0],'closing_cents')),invoice_event_rows=len(x['invoice_events']),
   active_accounts=len({r['account_id'] for r in x['usage_events']}),null_end_versions=sum(r['valid_to'] is None for r in x['subscription_versions']))
 elif domain=='payments':
  pg=groups(x['attempts'],'payment_id');caps=groups(x['captures'],'payment_id')
  f.update(attempt_key=['attempt_id'],payment_key=['payment_id'],merchant_key=['merchant_id'],attempts=len(x['attempts']),payments=len(pg),
   known_outcomes=sum(r['success'] is not None for r in x['attempts']),successful_attempts=sum(r['success']==1 for r in x['attempts']),
   attempt_rate=ratio(sum(r['success']==1 for r in x['attempts']),sum(r['success'] is not None for r in x['attempts'])),
   successful_payments=sum(any(r['success']==1 for r in rows) for rows in pg.values()),capture_total=str(total(x['captures'],'cents')),
   attempt_amount=str(total(x['attempts'],'amount_cents')),unknown_amounts=sum(r['amount_cents'] is None for r in x['attempts']),zero_amounts=sum(r['amount_cents']==0 for r in x['attempts']),
   no_capture=sum(not caps[k] for k in pg),relationship='1:M',repeated_capture_total=str(sum(total(caps[k],'cents')*len(rows) for k,rows in pg.items())))
 elif domain=='logistics':
  shipments={r['shipment_id']:r for r in x['shipments']};events=[r for r in x['shipment_events'] if r['shipment_id'] in shipments];first={}
  for r in sorted(events,key=lambda r:(r['event_at'],r['event_id'])):
   if r['status']=='delivered':first.setdefault(r['shipment_id'],r)
  final=latest(events,'shipment_id');ontime=sum(r['event_at']<=shipments[k]['promised_at'] for k,r in first.items())
  f.update(shipment_key=['shipment_id'],event_key=['event_id'],shipments=len(shipments),event_rows=len(x['shipment_events']),delivered=len(first),
   current_delivered=sum(r['status']=='delivered' for r in final),ontime=ontime,on_time_delivered=ratio(ontime,len(first)),on_time_all=ratio(ontime,len(shipments)),
   missing_delivery=len(shipments)-len(first),orphan_events=len(x['shipment_events'])-len(events),
   late_arrivals=sum(r['received_at']>r['event_at'] for r in events),relationship='1:M',leg_cost=str(total(x['legs'],'cost_cents')))
 elif domain=='marketing':
  current={r['lead_id']:r['status'] for r in latest(x['lead_states'],'lead_id')};history={r['lead_id']:r['status'] for r in latest([r for r in x['lead_states'] if r['event_at']<at(3)],'lead_id')}
  weights=groups(x['lead_credit'],'lead_id');qualified={k for k,v in current.items() if v=='qualified'};historic={k for k,v in history.items() if v=='qualified'}
  users={r['user_id']:r['lead_id'] for r in x['leads']};tg=groups(x['touches'],'user_id')
  f.update(lead_key=['lead_id'],delivery_key=['delivery_id'],credit_key=['credit_id'],state_key=['event_id'],qualified=len(qualified),historical_qualified=len(historic),
   qualified_credit_rows=sum(len(weights[k]) for k in qualified),historical_credit_rows=sum(len(weights[k]) for k in historic),
   allocated=str(sum(total(weights[k],'weight') for k in qualified)),historical_allocated=str(sum(total(weights[k],'weight') for k in historic)),
   invalid_weights=sum(total(v,'weight')!=1 for v in weights.values()),campaigns=len(x['campaigns']),
   lead_touch_rows=sum(max(1,len(tg[r['user_id']])) for r in x['leads']),duplicate_deliveries=len(x['lead_deliveries'])-len({r['lead_id'] for r in x['lead_deliveries']}),
   leads=len(x['leads']),enterprise_now=sum(r['segment']=='enterprise' for r in x['leads']),
   historical_l1_segment=next(r['segment'] for r in x['segment_history'] if r['lead_id']=='L1' and active(r,at(2),'valid_from','valid_to')),relationship='M:M')
 elif domain=='iot':
  eventg=groups(x['heartbeats'],'event_id');device_events=groups(x['heartbeats'],'device_id');ig=groups(x['intervals'],'device_id');trips=groups(x['trips'],'device_id')
  known=[r for r in x['intervals'] if r['up_minutes'] is not None];minutes=total(x['intervals'],'monitored_minutes');unknown=minutes-total(known,'monitored_minutes')
  f.update(device_key=['device_id'],delivery_key=['delivery_id'],logical_key=['event_id'],interval_key=['interval_id'],trip_key=['trip_id'],relationship='1:M',
   devices=len(x['devices']),arrivals=len(x['heartbeats']),logical_events=len(eventg),retries=len(x['heartbeats'])-len(eventg),
   no_observation=sum(not device_events[r['device_id']] for r in x['devices']),unknown_observations=sum(r['healthy'] is None for r in latest(x['heartbeats'],'event_id')),
   known_down=sum(r['healthy'] is False for r in latest(x['heartbeats'],'event_id')),known_up_minutes=str(total(known,'up_minutes')),known_minutes=str(total(known,'monitored_minutes')),
   total_minutes=str(minutes),unknown_minutes=str(unknown),uptime_known=ratio(total(known,'up_minutes'),total(known,'monitored_minutes')),
   uptime_strict=None if unknown else ratio(total(known,'up_minutes'),minutes),coverage=ratio(total(known,'monitored_minutes'),minutes),
   joined_rows=sum(max(1,len(ig[d['device_id']]))*max(1,len(trips[d['device_id']])) for d in x['devices']),
   pre_close_events=len({r['event_id'] for r in x['heartbeats'] if r['event_at']<at(3)}),known_at_close=len({r['event_id'] for r in x['heartbeats'] if r['event_at']<at(3) and r['received_at']<at(3)}),
   trips=len(x['trips']),active_trip_devices=len({r['device_id'] for r in x['trips']}),
   historic_first_account=next(r['account_id'] for r in x['memberships'] if r['device_id']=='D1' and active(r,at(2),'valid_from','valid_to')),
   current_first_account=next(r['account_id'] for r in x['devices'] if r['device_id']=='D1'),
   bad_intervals=sum(r['up_minutes'] is not None and not 0<=r['up_minutes']<=r['monitored_minutes'] for r in x['intervals']))
 elif domain=='workforce':
  employed=[r for r in x['employments'] if active(r,at(3))];staff=[r for r in employed if r['kind']=='employee'];ids={r['employment_id'] for r in staff};a=[r for r in x['assignments'] if active(r,at(3),'valid_from','valid_to') and r['employment_id'] in ids];ag=groups(x['assignments'],'employment_id')
  f.update(person_key=['person_id'],employment_key=['employment_id'],assignment_key=['assignment_id'],entry_key=['entry_id'],relationship='1:M',
   people=len(x['people']),active_relationships=len(employed),headcount=len({r['person_id'] for r in staff}),all_worker_people=len({r['person_id'] for r in employed}),
   active_assignments=len(a),fte=str(total(a,'fte')),unknown_fte=sum(r['fte'] is None for r in x['assignments']),hours=str(total(x['time_entries'],'hours')),
   multiplied_hours=str(sum(Decimal(r['hours'])*len([a for a in ag[r['employment_id']] if active(a,r['day']+'T00:00:00+00:00','valid_from','valid_to')]) for r in x['time_entries'])),
   before_boundary=sum(active(r,at(2)) and r['kind']=='employee' for r in x['employments']),employee_leavers=sum(r['ends_at']==at(3) and r['kind']=='employee' for r in x['employments']))
 elif domain=='ai':
  eligible=[r for r in x['tasks'] if r['eligible']];tg=groups(x['attempts'],'task_id');cg=groups(x['tool_calls'],'attempt_id');chosen=latest(x['attempts'],'task_id','finished_at');selected={r['task_id']:r for r in chosen}
  final=sum(selected.get(t['task_id'],{}).get('status')=='succeeded' and selected[t['task_id']]['approved'] for t in eligible)
  any_success=sum(any(a['status']=='succeeded' and a['approved'] for a in tg[t['task_id']]) for t in eligible)
  active_users={r['user_id'] for r in x['tasks'] if r['eligible']};user_rows={r['user_id']:r for r in x['users']}
  f.update(task_key=['task_id'],attempt_key=['attempt_id'],call_key=['call_id'],user_key=['user_id'],relationship='1:M',tasks=len(x['tasks']),eligible_tasks=len(eligible),
   attempts=len(x['attempts']),final_success=final,any_success=any_success,success_final=ratio(final,len(eligible)),success_any=ratio(any_success,len(eligible)),
   pending=sum(not tg[t['task_id']] for t in eligible),completed=sum(bool(tg[t['task_id']]) for t in eligible),
   active_users=len(active_users),active_accounts=len({user_rows[u]['account_id'] for u in active_users}),
   cost=str(total(x['tool_calls'],'cost_cents')),calls=len(x['tool_calls']),multiplied_success=sum(len(cg[r['attempt_id']]) for r in x['attempts'] if r['status']=='succeeded' and r['approved']),
   known_feedback=sum(r['score'] is not None for r in x['feedback']),unknown_feedback=sum(r['score'] is None for r in x['feedback']),missing_feedback=len(x['tasks'])-len({r['task_id'] for r in x['feedback']}),
   false_status_success=sum(r['status']=='succeeded' and not r['approved'] for r in x['attempts']),large_attempts=sum(r['model_version']=='M2' for r in x['attempts']))
 else:raise ValueError('Unknown reasoning business domain')
 return f
