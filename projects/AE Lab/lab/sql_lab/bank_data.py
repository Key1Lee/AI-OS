"""Original operational datasets for the SQL bank. No learner state lives here.

Each business has its own entities and rules. Clean rows stay small; adversarial
rows test stated requirements, not undisclosed accounting conventions.
"""
from copy import deepcopy
from .contracts import Domain, ForeignKey, Table

def t(name, entity, columns, key, *, refs=(), natural=None, pattern='transaction_fact', note=None):
    return Table(name, entity, 'one row per '+', '.join(key.split()),
        dict(x.split(':',1) for x in columns.split()), tuple(key.split()), tuple((natural or key).split()), pattern,
        tuple(ForeignKey((col,), parent, (target,)) for col,parent,target in refs),
        aggregation=note or 'Amounts add only at the declared grain and within currency; attributes and identifiers are not additive.')

DEFINITIONS=[
 Domain('commerce','E-commerce / Parcel Pine',(
  t('customers','customer','customer_id:text email:text signup_at:timestamptz','customer_id',pattern='dimension'),
  t('orders','placed order','order_id:text customer_id:text ordered_at:timestamptz fulfilled_at:timestamptz status:text gross_cents:bigint','order_id',refs=[('customer_id','customers','customer_id')]),
  t('items','order line','item_id:text order_id:text product:text quantity:integer line_cents:bigint','item_id',refs=[('order_id','orders','order_id')]),
  t('refunds','final refund transaction','refund_id:text order_id:text refund_at:timestamptz amount_cents:bigint status:text','refund_id',refs=[('order_id','orders','order_id')]),
  t('calendar','calendar date','day:date','day',pattern='dimension'),
  t('events','received product event','event_id:bigint customer_id:text event_type:text event_at:timestamptz','event_id',refs=[('customer_id','customers','customer_id')],pattern='event_fact'),
 )),
 Domain('retail','Retail / Cedar Counter',(
  t('stores','store','store_id:text region:text','store_id',pattern='dimension'),
  t('sales','receipt line','sale_id:text store_id:text sku:text sold_at:timestamptz quantity:integer cents:bigint discount_cents:bigint','sale_id',refs=[('store_id','stores','store_id')]),
  t('inventory','end-of-day stock snapshot','store_id:text sku:text day:date on_hand:integer','store_id sku day',refs=[('store_id','stores','store_id')],pattern='periodic_snapshot',note='Stock adds across SKUs/stores at one date; never sum stock across dates.'),
  t('products','product identifier','sku:text external_code:text label:text','sku',pattern='dimension'),
  t('calendar','calendar date','day:date','day',pattern='dimension'),
 )),
 Domain('marketplace','Marketplace / Loom Exchange',(
  t('sellers','seller','seller_id:text region:text parent_id:text','seller_id',pattern='dimension'),
  t('purchases','buyer purchase','purchase_id:text seller_id:text buyer_id:text bought_at:timestamptz cents:bigint status:text','purchase_id',refs=[('seller_id','sellers','seller_id')]),
  t('payouts','seller payout','payout_id:text seller_id:text paid_at:timestamptz cents:bigint','payout_id',refs=[('seller_id','sellers','seller_id')]),
  t('tags','seller membership bridge','seller_id:text tag:text weight:numeric(12,6)','seller_id tag',refs=[('seller_id','sellers','seller_id')],pattern='bridge',note='Allocation weights sum to one per seller; allocate seller value before tag aggregation.'),
 )),
 Domain('lending','Lending / Beacon Credit',(
  t('borrowers','borrower','borrower_id:text risk:text','borrower_id',pattern='dimension'),
  t('loans','originated loan','loan_id:text borrower_id:text principal_cents:bigint currency:text originated_at:timestamptz','loan_id',refs=[('borrower_id','borrowers','borrower_id')]),
  t('payment_transactions','received payment transaction version','event_id:bigint transaction_id:text loan_id:text principal_cents:bigint status:text event_at:timestamptz received_at:timestamptz','event_id',refs=[('loan_id','loans','loan_id')],natural='transaction_id',pattern='event_fact'),
  t('scheduled_payments','scheduled installment','schedule_id:text loan_id:text due_at:timestamptz due_cents:bigint','schedule_id',refs=[('loan_id','loans','loan_id')]),
  t('loan_status_history','loan state change','event_id:bigint loan_id:text status:text event_at:timestamptz','event_id',refs=[('loan_id','loans','loan_id')],pattern='event_fact'),
  t('charge_offs','approved charge-off adjustment','charge_id:text loan_id:text charged_at:timestamptz cents:bigint','charge_id',refs=[('loan_id','loans','loan_id')]),
  t('payments','final recorded payment allocation','payment_id:text loan_id:text schedule_id:text principal_paid_cents:bigint','payment_id',refs=[('loan_id','loans','loan_id'),('schedule_id','scheduled_payments','schedule_id')]),
  t('delinquencies','reported delinquency snapshot','loan_id:text as_of:date days_past_due:integer','loan_id as_of',refs=[('loan_id','loans','loan_id')],pattern='periodic_snapshot'),
 )),
 Domain('banking','Banking / Slate Bank',(
  t('accounts','bank account','account_id:text owner_id:text currency:text','account_id',pattern='dimension'),
  t('transactions','posted signed account movement','transaction_id:text account_id:text posted_at:timestamptz cents:bigint category:text counterparty:text','transaction_id',refs=[('account_id','accounts','account_id')]),
  t('balances','end-of-day account balance','account_id:text day:date balance_cents:bigint','account_id day',refs=[('account_id','accounts','account_id')],pattern='periodic_snapshot',note='Balances add across same-currency accounts at one instant, not across dates.'),
  t('statement','external statement line','statement_id:text transaction_id:text cents:bigint','statement_id'),
 )),
 Domain('payments','Payments / KitePay',(
  t('merchants','merchant','merchant_id:text region:text','merchant_id',pattern='dimension'),
  t('attempts','payment authorization attempt','attempt_id:text payment_id:text merchant_id:text attempted_at:timestamptz success:integer amount_cents:bigint latency_ms:integer metadata:jsonb','attempt_id',refs=[('merchant_id','merchants','merchant_id')],natural='payment_id'),
  t('captures','settled capture','capture_id:text payment_id:text merchant_id:text captured_at:timestamptz cents:bigint','capture_id',refs=[('merchant_id','merchants','merchant_id')]),
  t('disputes','dispute claim','dispute_id:text payment_id:text status:text cents:bigint','dispute_id'),
 )),
 Domain('wallet','Fintech / Pebble Wallet',(
  t('wallets','wallet owner','wallet_id:text email:text opened_at:timestamptz','wallet_id',pattern='dimension'),
  t('wallet_events','received wallet ledger version','event_id:bigint transfer_id:text wallet_id:text cents:bigint status:text event_at:timestamptz received_at:timestamptz','event_id',refs=[('wallet_id','wallets','wallet_id')],natural='transfer_id',pattern='event_fact'),
  t('risk_events','wallet risk observation','risk_id:text wallet_id:text score:integer event_at:timestamptz signals:text[]','risk_id',refs=[('wallet_id','wallets','wallet_id')],pattern='event_fact'),
 )),
 Domain('advertising','Advertising / Signal Grove',(
  t('campaigns','campaign','campaign_id:text channel:text','campaign_id',pattern='dimension'),
  t('ad_daily','campaign day counters','campaign_id:text day:date impressions:bigint clicks:bigint spend_cents:bigint','campaign_id day',refs=[('campaign_id','campaigns','campaign_id')],pattern='aggregate_fact'),
  t('conversions','attributed conversion','conversion_id:text campaign_id:text user_id:text converted_at:timestamptz value_cents:bigint','conversion_id',refs=[('campaign_id','campaigns','campaign_id')]),
  t('touches','user ad touch','touch_id:text campaign_id:text user_id:text touched_at:timestamptz','touch_id',refs=[('campaign_id','campaigns','campaign_id')],pattern='event_fact'),
 )),
 Domain('logistics','Logistics / North Parcel',(
  t('shipments','shipment promise','shipment_id:text route:text promised_at:timestamptz','shipment_id'),
  t('shipment_events','received shipment status','event_id:bigint shipment_id:text status:text event_at:timestamptz received_at:timestamptz','event_id',refs=[('shipment_id','shipments','shipment_id')],pattern='event_fact'),
  t('legs','shipment route leg','leg_id:text shipment_id:text sequence:integer km:integer cost_cents:bigint','leg_id',refs=[('shipment_id','shipments','shipment_id')]),
 )),
 Domain('travel','Travel / Drift Rooms',(
  t('travelers','traveler','traveler_id:text email:text joined_at:timestamptz','traveler_id',pattern='dimension'),
  t('bookings','hotel booking','booking_id:text traveler_id:text destination:text booked_at:timestamptz check_in:date check_out:date cents:bigint status:text','booking_id',refs=[('traveler_id','travelers','traveler_id')]),
  t('booking_events','booking status version','event_id:bigint booking_id:text status:text event_at:timestamptz','event_id',refs=[('booking_id','bookings','booking_id')],pattern='event_fact'),
 )),
 Domain('support','Support Operations / Relay Desk',(
  t('agents','support agent','agent_id:text team:text','agent_id',pattern='dimension'),
  t('tickets','support case','ticket_id:text agent_id:text opened_at:timestamptz closed_at:timestamptz priority:text csat:integer','ticket_id',refs=[('agent_id','agents','agent_id')]),
  t('ticket_events','case activity','event_id:bigint ticket_id:text action:text event_at:timestamptz','event_id',refs=[('ticket_id','tickets','ticket_id')],pattern='event_fact'),
 )),
 Domain('healthcare','Healthcare Operations / Willow Clinics',(
  t('clinics','clinic site','clinic_id:text timezone:text','clinic_id',pattern='dimension'),
  t('appointments','scheduled appointment','appointment_id:text clinic_id:text patient_id:text scheduled_at:timestamptz status:text minutes:integer','appointment_id',refs=[('clinic_id','clinics','clinic_id')]),
  t('procedures','operational procedure line','procedure_id:text appointment_id:text code:text minutes:integer','procedure_id',refs=[('appointment_id','appointments','appointment_id')]),
  t('calendar','calendar date','day:date','day',pattern='dimension'),
 )),
 Domain('insurance','Insurance / Alder Cover',(
  t('policies','policy contract','policy_id:text holder_id:text starts_at:date ends_at:date premium_cents:bigint','policy_id'),
  t('claims','filed claim','claim_id:text policy_id:text filed_at:timestamptz reserve_cents:bigint status:text','claim_id',refs=[('policy_id','policies','policy_id')]),
  t('claim_events','claim status version','event_id:bigint claim_id:text status:text event_at:timestamptz','event_id',refs=[('claim_id','claims','claim_id')],pattern='event_fact'),
 )),
 Domain('subscription','Subscriptions / Fern Box',(
  t('subscribers','subscriber','subscriber_id:text joined_at:timestamptz segment:text','subscriber_id',pattern='dimension'),
  t('subscription_events','subscriber state event','event_id:bigint subscriber_id:text status:text event_at:timestamptz','event_id',refs=[('subscriber_id','subscribers','subscriber_id')],pattern='event_fact'),
  t('invoices','subscription invoice','invoice_id:text subscriber_id:text invoiced_at:timestamptz cents:bigint status:text','invoice_id',refs=[('subscriber_id','subscribers','subscriber_id')]),
  t('activity','subscriber activity day','subscriber_id:text day:date','subscriber_id day',refs=[('subscriber_id','subscribers','subscriber_id')],pattern='factless_fact'),
 )),
]
BANK_DOMAINS={d.id:d for d in DEFINITIONS}

def d(day, hour=0, minute=0):return f'2026-10-{day:02d}T{hour:02d}:{minute:02d}:00+00:00'

def bank_fixture(domain, variant='clean', seed=1):
    if variant not in ('clean','adversarial','recall') or seed not in (1,2,3):raise ValueError('Unknown deterministic fixture')
    definition=BANK_DOMAINS[domain];data={};bad=variant!='clean'
    def put(name, values, extra=()):
        cols=definition.table(name).columns
        data[name]=[dict(zip(cols,row)) for row in list(values)+(list(extra) if bad else [])]
    if domain=='commerce':
        put('customers',[('C1',' Ava@North.Test ',d(1)),('C2','BO@NORTH.TEST',d(1)),('C3',None,d(2))],[('C4','zero@quiet.test',d(3))])
        put('orders',[('O1','C1',d(1,10),d(2),'fulfilled',5000),('O2','C1',d(2,10),d(3),'fulfilled',5000),('O3','C2',d(3,10),None,'open',2000)],
            [('O4','C2',d(3,10),None,'cancelled',2000),('O5','C3',d(1),d(2),'fulfilled',0),('O6','C1','2026-11-01T00:00:00+00:00','2026-11-02T00:00:00+00:00','fulfilled',7000)])
        put('items',[('X1','O1','book',1,2000),('X2','O1','lamp',1,3000),('X3','O2','lamp',2,5000),('X4','O3','book',1,2000)],
            [('X5','O4','book',1,2000),('X6','O5','gift',1,0),('X7','O6','desk',1,7000)])
        put('refunds',[('R1','O1',d(3),1000,'posted')],[('R2','O1',d(4),500,'posted'),('R3','O2',d(4),500,'reversed'),('R4','O3',d(4),None,'pending')])
        put('calendar',[(f'2026-10-{i:02d}',) for i in range(1,8)])
        put('events',[(1,'C1','view',d(1,9)),(2,'C1','cart',d(1,9,5)),(3,'C1','purchase',d(1,9,20)),(4,'C2','view',d(1,10))],
            [(5,'C2','purchase',d(1,9)),(6,'C2','cart',d(1,10,5)),(7,'C1','cart',d(1,9,5)),(8,'C3','view',d(1,23)),(9,'C3','cart',d(2,1)),(10,'C3','purchase',d(2,2)),(11,'C1','view',d(2,9)),(12,'C1','view',d(2,9,30)),(13,'C1','view',d(2,10,1))])
    elif domain=='retail':
        put('stores',[('S1','north'),('S2','south'),('S3','quiet')])
        put('sales',[('A1','S1','P1',d(1,10),2,1000,100),('A2','S1','P2',d(1,11),1,1000,None),('A3','S2','P1',d(2),3,3000,0)],
            [('A4','S1','P1',d(2),-1,-500,0),('A5','S2','P2',d(3),0,0,None),('A6','S2','P2',d(3),1,1000,100),('A7','S1','P2',d(3),1,1000,0),('A8','S1','P2',d(3),1,1000,0),('A9','S2','P1','2026-06-30T23:59:00+00:00',1,500,0),('A10','S2','P1','2026-07-01T00:00:00+00:00',1,500,0)])
        put('inventory',[('S1','P1','2026-10-01',5),('S1','P1','2026-10-02',3),('S2','P1','2026-10-02',8)],
            [('S1','P1','2026-10-03',0),('S1','P2','2026-10-03',2),('S2','P1','2026-10-03',7)])
        put('products',[('P1','00123',' Book '),('P2','123','lamp')],[('P3','bad-7',' Gift '),('P4',None,'Unknown')])
        put('calendar',[(f'2026-10-{i:02d}',) for i in range(1,6)])
    elif domain=='marketplace':
        put('sellers',[('V1','north',None),('V2','north','V1'),('V3','south',None)],[('V4','north','V1')])
        put('purchases',[('P1','V1','B1',d(1),1000,'completed'),('P2','V1','B2',d(2),1000,'completed'),('P3','V2','B1',d(1),2000,'completed')],
            [('P4','V1','B1',d(3),-100,'refunded'),('P5','V2','B3',d(2),0,'cancelled'),('P6','V2','B2',d(3),1000,'completed')])
        put('payouts',[('Y1','V1',d(2),500),('Y2','V2',d(3),1000)],[('Y3','V1',d(3),500)])
        put('tags',[('V1','home','0.5'),('V1','craft','0.5'),('V2','craft','1'),('V3','home','1')],[('V4','home','1')])
    elif domain=='lending':
        put('borrowers',[('B1','low'),('B2','high'),('B3','unknown')])
        put('loans',[('L1','B1',100000,'USD',d(1)),('L2','B1',50000,'USD',d(2)),('L3','B2',20000,'USD',d(1)),('L4','B3',30000,'EUR',d(1))])
        put('payment_transactions',[(1,'T1','L1',10000,'posted',d(2),d(2)),(2,'T2','L2',5000,'posted',d(3),d(3))],
            [(3,'T1','L1',10000,'posted',d(2),d(3)),(4,'T2','L2',6000,'posted',d(3),d(3)),(5,'T3','L1',5000,'posted',d(2),d(2)),(6,'T3','L1',5000,'reversed',d(3),d(3)),(7,'T4','L2',None,'posted',d(3),d(4)),(8,'T5','L1',-2000,'posted',d(4),d(4)),(9,'T6','L1',10000,'posted',d(2),d(6)),(10,'T7','L4',0,'pending',d(3),d(3))])
        put('scheduled_payments',[('D1','L1',d(2),20000),('D2','L1',d(4),15000),('D3','L2',d(3),9000),('D4','L3',d(2),5000)])
        put('loan_status_history',[(1,'L1','active',d(1)),(2,'L2','active',d(2)),(3,'L3','active',d(1)),(4,'L4','active',d(1))],[(5,'L1','late',d(3)),(6,'L1','active',d(3)),(7,'L3','charged_off',d(4))])
        put('charge_offs',[('Z1','L3',d(4),1000)],[('Z2','L3',d(5),500)])
        put('payments',[('P1','L1','D1',10000),('P2','L2','D3',None),('P3','L4',None,0)], [('P4','L1','D1',-2000),('P5','L2',None,1000)])
        put('delinquencies',[('L1','2026-10-06',4),('L2','2026-10-06',3)],[('L1','2026-10-05',3)])
    elif domain=='banking':
        put('accounts',[('A1','U1','USD'),('A2','U1','USD'),('A3','U2','EUR'),('A4','U3','USD')])
        put('transactions',[('T1','A1',d(1),1000,'deposit','cash'),('T2','A1',d(2),-200,'purchase','shop'),('T3','A2',d(2),300,'deposit','cash')],
            [('T4','A1',d(2),-300,'transfer','A2'),('T5','A2',d(2),300,'transfer','A1'),('T6','A3',d(3),None,'pending','unknown'),('T7','A1',d(3),0,'fee','bank')])
        put('balances',[('A1','2026-10-01',1000),('A1','2026-10-02',800),('A2','2026-10-02',300)],[('A1','2026-10-03',500),('A2','2026-10-03',600),('A3','2026-10-03',0)])
        put('statement',[('E1','T1',1000),('E2','T2',-200)],[('E3','T2',-200),('E4','UNKNOWN',70)])
    elif domain=='payments':
        put('merchants',[('M1','north'),('M2','south'),('M3','quiet')])
        put('attempts',[('A1','P1','M1',d(1),1,1000,100,{'channel':'web','risk':2}),('A2','P2','M1',d(2),0,2000,300,{'channel':'app'}),('A3','P3','M2',d(2),1,1000,200,{'channel':'web','risk':None})],
            [('A4','P2','M1',d(2),1,2000,300,{'channel':'app','risk':'bad'}),('A5','P4','M2',d(3),0,0,1000,{}),('A6','P5','M1',d(3),None,None,None,{'channel':None}),('A7','P6','M2',d(3),1,1000,200,{'channel':'web','risk':9})])
        put('captures',[('C1','P1','M1',d(2),1000),('C2','P3','M2',d(3),1000)],[('C3','P2','M1',d(3),2000),('C4','P2','M1',d(4),500)])
        put('disputes',[('D1','P1','open',200)],[('D2','P1','closed',100),('D3','P3','open',0)])
    elif domain=='wallet':
        put('wallets',[('W1',' Ava@Pebble.Test ',d(1)),('W2','bad-email',d(2)),('W3',None,d(3))])
        put('wallet_events',[(1,'T1','W1',1000,'posted',d(2),d(2)),(2,'T2','W2',0,'posted',d(3),d(3))],
            [(3,'T1','W1',1000,'posted',d(2),d(3)),(4,'T3','W1',-200,'posted',d(3),d(3)),(5,'T4','W2',None,'posted',d(3),d(4)),(6,'T5','W1',500,'reversed',d(4),d(4))])
        put('risk_events',[('R1','W1',10,d(2),['velocity','device']),('R2','W2',90,d(3),['device'])],[('R3','W1',20,d(3),[]),('R4','W3',None,d(3),['unknown','velocity'])])
    elif domain=='advertising':
        put('campaigns',[('K1','search'),('K2','social'),('K3','quiet')])
        put('ad_daily',[('K1','2026-10-01',100,10,500),('K1','2026-10-02',900,9,600),('K2','2026-10-01',100,10,500)],
            [('K2','2026-10-02',0,0,0),('K2','2026-10-03',100,1,100),('K1','2026-10-03',100,0,0),('K1','2027-01-01',50,1,10)])
        put('conversions',[('C1','K1','U1',d(2),1000),('C2','K2','U2',d(2),2000)],[('C3','K1','U1',d(3),1000)])
        put('touches',[('H1','K1','U1',d(1)),('H2','K2','U2',d(1))],[('H3','K2','U1',d(1,1)),('H4','K1','U1',d(2,1)),('H5','K2','U2',d(3))])
    elif domain=='logistics':
        put('shipments',[('S1','north',d(3)),('S2','south',d(4)),('S3','north',d(4))])
        put('shipment_events',[(1,'S1','collected',d(1),d(1)),(2,'S1','delivered',d(3),d(3)),(3,'S2','collected',d(2),d(2))],
            [(4,'S1','returned',d(4),d(4)),(5,'S2','delivered',d(5),d(5)),(6,'S2','delivered',d(5),d(6)),(7,'S1','collected',d(2),d(7))])
        put('legs',[('G1','S1',1,10,100),('G2','S1',2,20,200),('G3','S2',1,10,100)],[('G4','S2',2,0,0)])
    elif domain=='travel':
        put('travelers',[('U1','a@drift.test',d(1)),('U2','B@DRIFT.TEST',d(1)),('U3',None,d(2))])
        put('bookings',[('B1','U1','coast',d(1),'2026-10-03','2026-10-05',10000,'confirmed'),('B2','U1','hill',d(2),'2026-10-05','2026-10-06',6000,'confirmed'),('B3','U2','coast',d(2),'2026-10-03','2026-10-04',5000,'cancelled')],
            [('B4','U2','hill',d(3),'2026-10-04','2026-10-04',0,'confirmed'),('B5','U2','coast',d(3),'2026-10-04','2026-10-06',10000,'confirmed')])
        put('booking_events',[(1,'B1','confirmed',d(1)),(2,'B2','confirmed',d(2)),(3,'B3','cancelled',d(2))],[(4,'B1','cancelled',d(3)),(5,'B1','confirmed',d(3)),(6,'B4','confirmed',d(3)),(7,'B5','confirmed',d(3))])
    elif domain=='support':
        put('agents',[('A1','alpha'),('A2','beta'),('A3','quiet')])
        put('tickets',[('T1','A1',d(1),d(2),'urgent',5),('T2','A1',d(2),None,'normal',None),('T3','A2',d(1),d(3),'normal',3)],
            [('T4','A1',d(3),d(3),'urgent',0),('T5','A2',d(3),d(4),'unknown',None),('T6','A1',d(3),None,'urgent',None),('T7',None,d(3),d(4),'normal',3)])
        put('ticket_events',[(1,'T1','opened',d(1)),(2,'T1','replied',d(1,1)),(3,'T1','closed',d(2)),(4,'T2','opened',d(2))],
            [(5,'T1','reopened',d(3)),(6,'T1','replied',d(3,1)),(7,'T2','replied',d(3)),(8,'T3','opened',d(1)),(9,'T3','replied',d(2))])
    elif domain=='healthcare':
        put('clinics',[('C1','America/New_York'),('C2','Asia/Seoul'),('C3','UTC')])
        put('appointments',[('A1','C1','P1',d(1,12),'completed',30),('A2','C1','P2',d(2,12),'no_show',20),('A3','C2','P1',d(2,16),'completed',40)],
            [('A4','C1','P1','2026-11-01T05:30:00+00:00','completed',30),('A5','C1','P3','2026-11-01T06:30:00+00:00','completed',30),('A6','C2','P4',d(3),'cancelled',20),('A7','C2','P4',d(4),'completed',0)])
        put('procedures',[('X1','A1','check',10),('X2','A1','prep',20),('X3','A3','check',40)],[('X4','A4','check',30),('X5','A5','check',30),('X6','A7','check',0)])
        put('calendar',[(f'2026-10-{i:02d}',) for i in range(1,6)])
    elif domain=='insurance':
        put('policies',[('P1','U1','2026-10-01','2026-11-01',10000),('P2','U2','2026-10-02',None,20000),('P3','U1','2026-11-01',None,15000)], [('P4','U3','2024-02-28','2024-03-01',0)])
        put('claims',[('C1','P1',d(2),5000,'open'),('C2','P1',d(3),5000,'closed'),('C3','P2',d(3),None,'open')],[('C4','P2',d(4),0,'denied'),('C5','P1',d(4),-100,'open')])
        put('claim_events',[(1,'C1','open',d(2)),(2,'C2','closed',d(3)),(3,'C3','open',d(3))],[(4,'C1','closed',d(4)),(5,'C1','open',d(4)),(6,'C4','denied',d(4)),(7,'C5','open',d(4))])
    elif domain=='subscription':
        put('subscribers',[('S1',d(1),'home'),('S2',d(2),'office'),('S3',d(3),'home')])
        put('subscription_events',[(1,'S1','active',d(1)),(2,'S2','active',d(2))],[(3,'S1','cancelled',d(3)),(4,'S1','active',d(3)),(5,'S3','trial',d(3)),(6,'S2','cancelled',d(4))])
        put('invoices',[('I1','S1',d(1),1000,'paid'),('I2','S1',d(2),1000,'paid'),('I3','S2',d(2),2000,'paid')],
            [('I4','S1',d(3),-200,'paid'),('I5','S2',d(3),2000,'void'),('I6','S3',d(3),None,'pending')])
        put('activity',[('S1','2026-10-01'),('S1','2026-10-02'),('S2','2026-10-02')],
            [('S1','2026-10-03'),('S1','2026-10-05'),('S2','2026-10-04'),('S3','2026-10-03')])
    else:raise ValueError(f'Unknown bank business {domain}')
    if variant=='recall':
        if domain=='lending':data['payment_transactions'].append(dict(event_id=11,transaction_id='T2',loan_id='L2',principal_cents=3000,status='posted',event_at=d(3),received_at=d(7)))
        if domain=='logistics':data['shipment_events'].append(dict(event_id=8,shipment_id='S2',status='returned',event_at=d(5),received_at=d(7)))
        if domain=='wallet':data['wallet_events'].append(dict(event_id=7,transfer_id='T1',wallet_id='W1',cents=600,status='posted',event_at=d(2),received_at=d(7)))
        if domain=='commerce':data['refunds'].append(dict(refund_id='R5',order_id='O2',refund_at=d(5),amount_cents=800,status='posted'))
    if domain=='subscription' and bad:
        data['activity'] += [{'subscriber_id':'S1','day':'2026-10-06'}, {'subscriber_id':'S1','day':'2026-11-02'}, {'subscriber_id':'S2','day':'2026-10-07'}]
    if domain=='commerce' and bad:
        data['orders'].append(dict(order_id='O7',customer_id='C1',ordered_at='2027-01-01T00:00:00+00:00',fulfilled_at='2027-01-02T00:00:00+00:00',status='fulfilled',gross_cents=8000))
        data['refunds'].append(dict(refund_id='R6',order_id='O1',refund_at='2026-11-03T00:00:00+00:00',amount_cents=200,status='posted'))
        data['events'] += [{'event_id':20,'customer_id':'C4','event_type':'view','event_at':d(3,9)},
                          {'event_id':21,'customer_id':'C4','event_type':'purchase','event_at':d(3,9,30)},
                          {'event_id':22,'customer_id':'C4','event_type':'purchase','event_at':d(3,9,30)}]
    if domain=='advertising' and bad:
        data['ad_daily'] += [{'campaign_id':'K1','day':'2026-10-08','impressions':100,'clicks':12,'spend_cents':100},
                            {'campaign_id':'K1','day':'2026-10-15','impressions':100,'clicks':0,'spend_cents':100},
                            {'campaign_id':'K2','day':'2026-10-15','impressions':100,'clicks':5,'spend_cents':100}]
    if domain=='retail' and bad:
        data['sales'] += [dict(sale_id='Y1',store_id='S1',sku='P1',sold_at='2025-10-01T00:00:00+00:00',quantity=1,cents=600,discount_cents=0),
                         dict(sale_id='Y2',store_id='S1',sku='P1',sold_at='2025-11-01T00:00:00+00:00',quantity=1,cents=200,discount_cents=0),
                         dict(sale_id='Y3',store_id='S1',sku='P1',sold_at='2026-11-01T00:00:00+00:00',quantity=1,cents=100,discount_cents=0)]
    if domain=='payments':
        data['attempts'][0]['metadata']['items']=[{'product':'book','units':'2'},{'product':'lamp','units':None}]
        for row,amount in zip(data['attempts'],['90071992547409.91','0.01','12.30','-0.02']):row['metadata']['settled_amount']=amount
        if bad:data['attempts'][1]['metadata']['items']=[]
    factor=seed if variant!='recall' else seed+3
    for name,records in data.items():
        for row in records:
            for col,v in row.items():
                if col.endswith('cents') and v is not None:row[col]=v*factor
        if seed==2:records.reverse()
    return deepcopy(data)
