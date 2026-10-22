"""Authoring source for 116 distinct scenarios; emits the Step 1 problem contract.

Run after editing this file. Runtime reads curriculum/sql-bank.json, not a
parallel engine. References are private; validation executes them in PostgreSQL.
"""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.sql_lab.datasets import DOMAINS, fixture
from lab.sql_lab.bank_oracles import expected_bank
from lab.sql_lab.contracts import fingerprint

SPECS=[]
def add(area,n,domain,title,inputs,output,key,requirement,query,tags,*,level=None,broken=None,transfer=None,joins=None,window=False,predict=None,stage=None):
    levels={'FND':[1]*10,'AGG':[1]*2+[2]*6+[3]*2,'GRN':[2]*7+[3]*5,'JOIN':[2]*3+[3]*7+[4]*2,
      'CTE':[2]*5+[3]*3+[4]*2,'WIN':[3]*8+[4]*4,'DED':[3]*4+[4]*4,'DATE':[2]*2+[4]*6,'PAT':[4]*5+[5]*3,'ADV':[5]*8+[6]*2}
    SPECS.append(dict(id=f'SQL-{area}-{n:03d}',area=area,level=level or levels[area][n-1],domain=domain,title=title,
      inputs=inputs.split(),output=output.split(),key=key.split(),requirement=requirement,sql=query,tags=tags.split(),
      broken=broken,transfer=transfer,joins=joins or {},window=window,predict=predict,stage=stage))

# Foundations: distinct decisions, not ten renamed SELECTs.
add('FND',1,'retail','Return receipt lines','sales','sale_id sku return_cents','sale_id',
 'Return only negative-quantity receipt lines. return_cents is the negation of the signed cents column; cents is already the complete line amount, not a unit price.',
 'SELECT sale_id,sku,-cents AS return_cents FROM sales WHERE quantity<0','sql.filtering.expressions sql.filtering.predicates')
add('FND',2,'marketplace','Completed purchase population','purchases','purchase_id','purchase_id',
 'Include completed purchases with cents >= 1000; cancelled and refunded states do not count.',
 "SELECT purchase_id FROM purchases WHERE status='completed' AND cents>=1000",'sql.filtering.boolean_logic sql.filtering.in_between')
add('FND',3,'support','Open escalation queue','tickets','ticket_id','ticket_id',
 'Include open tickets that are urgent OR were opened before 2026-10-03 00:00 UTC. Every returned ticket must be open.',
 "SELECT ticket_id FROM tickets WHERE closed_at IS NULL AND (priority='urgent' OR opened_at<TIMESTAMPTZ '2026-10-03 00:00+00')",'sql.filtering.and_or_precedence sql.nulls.is_null',
 broken="SELECT ticket_id FROM tickets WHERE closed_at IS NULL AND priority='urgent' OR opened_at<TIMESTAMPTZ '2026-10-03 00:00+00'")
add('FND',4,'travel','Booked destination shortlist','bookings','booking_id','booking_id',
 'Include confirmed coast or hill bookings whose total cents is between 5000 and 10000 inclusive.',
 "SELECT booking_id FROM bookings WHERE status='confirmed' AND destination IN ('coast','hill') AND cents BETWEEN 5000 AND 10000",'sql.filtering.in_between')
add('FND',5,'insurance','Policy population at renewal boundary','policies','policy_id','policy_id',
 'Report policies active on 2026-11-01: starts_at <= date < ends_at; NULL ends_at means no scheduled end.',
 "SELECT policy_id FROM policies WHERE starts_at<=DATE '2026-11-01' AND (ends_at IS NULL OR DATE '2026-11-01'<ends_at)",'sql.nulls.three_valued_logic sql.dates.half_open')
add('FND',6,'wallet','Unknown ledger observations','wallet_events','event_id','event_id',
 'Return received events with unknown cents. A known zero is not unknown. Do not remove repeated arrivals in this observation report.',
 'SELECT event_id FROM wallet_events WHERE cents IS NULL','sql.nulls.unknown_vs_zero sql.nulls.is_null',
 broken='SELECT event_id FROM wallet_events WHERE cents = NULL')
add('FND',7,'retail','Receipt lifecycle buckets','sales','sale_id bucket','sale_id',
 'Classify every line with priority: quantity < 0 => return; otherwise unknown discount => unknown_discount; positive discount => discounted; otherwise regular.',
 "SELECT sale_id,CASE WHEN quantity<0 THEN 'return' WHEN discount_cents IS NULL THEN 'unknown_discount' WHEN discount_cents>0 THEN 'discounted' ELSE 'regular' END AS bucket FROM sales",'sql.filtering.case_priority sql.nulls.is_null')
add('FND',8,'retail','Product labels and external identities','products','sku clean_label external_code','sku',
 'Trim and lowercase label into clean_label. Preserve external_code as text, including leading zeros and NULL; 00123 and 123 are different source identities.',
 'SELECT sku,LOWER(TRIM(label)) AS clean_label,external_code FROM products','sql.strings.trim_case sql.types.identifier_semantics')
add('FND',9,'travel','Traveler email domains','travelers','traveler_id email_domain','traveler_id',
 'For non-NULL emails containing @, return the lowercase trimmed part after @. Fixture emails contain exactly one @ when valid.',
 "SELECT traveler_id,SPLIT_PART(LOWER(TRIM(email)),'@',2) AS email_domain FROM travelers WHERE email LIKE '%@%'",'sql.strings.split_domain sql.strings.like_regex')
add('FND',10,'commerce','Largest two order commitments','orders','order_id gross_cents','order_id',
 'Return exactly the two largest gross_cents orders, all statuses. Break ties by order_id ascending and return rows in that same order.',
 'SELECT order_id,gross_cents FROM orders ORDER BY gross_cents DESC,order_id ASC LIMIT 2','sql.filtering.sorting sql.filtering.limit sql.deduplication.deterministic_ties')

# Aggregation and NULL: known zero, unknown measurement and absent entity differ.
add('AGG',1,'support','Rated and unrated workload','tickets','scope tickets rated avg_score','scope',
 'One row labeled scope=all. Count all tickets, count non-NULL CSAT, and average known scores including zero. Round avg_score to 2 decimals; no known scores means NULL.',
 "SELECT 'all' AS scope,COUNT(*) AS tickets,COUNT(csat) AS rated,ROUND(AVG(csat),2) AS avg_score FROM tickets",'sql.aggregation.count_star_column sql.nulls.aggregate_nulls',predict='SELECT COUNT(*) AS tickets, COUNT(csat) AS rated FROM tickets')
add('AGG',2,'retail','Net receipt value by active store','sales','store_id net_cents','store_id',
 'For stores with receipt lines, sum signed cents minus discount_cents. cents is line total. For this receipt KPI only, an unknown discount contributes zero; returns remain negative.',
 'SELECT store_id,SUM(cents-COALESCE(discount_cents,0)) AS net_cents FROM sales GROUP BY store_id','sql.aggregation.group_by sql.nulls.coalesce')
add('AGG',3,'payments','Authorization success denominator','merchants attempts','merchant_id success_rate','merchant_id',
 'Include every merchant. success_rate = known successful attempts / attempts with known success (0 or 1), rounded to 2 decimals. No known attempts => NULL, not zero.',
 'SELECT m.merchant_id,ROUND(COUNT(a.attempt_id) FILTER(WHERE a.success=1)::numeric/NULLIF(COUNT(a.success),0),2) AS success_rate FROM merchants m LEFT JOIN attempts a USING(merchant_id) GROUP BY m.merchant_id',
 'sql.aggregation.ratios_zero sql.nulls.nullif sql.types.integer_division',joins={'merchants:attempts':'1:M'})
add('AGG',4,'advertising','Campaign click-through rate','ad_daily','campaign_id ctr','campaign_id',
 'Compute lifetime sum(clicks)/sum(impressions) by observed campaign, rounded to 2 decimals. A zero denominator yields NULL. Do not average daily ratios.',
 'SELECT campaign_id,ROUND(SUM(clicks)::numeric/NULLIF(SUM(impressions),0),2) AS ctr FROM ad_daily GROUP BY campaign_id','sql.aggregation.weighted_averages sql.aggregation.ratios_zero')
add('AGG',5,'commerce','High-value fulfilled customers','orders','customer_id fulfilled_cents','customer_id',
 'Sum gross_cents for fulfilled orders only, then retain customers with fulfilled_cents >= 5000.',
 "SELECT customer_id,SUM(gross_cents) AS fulfilled_cents FROM orders WHERE status='fulfilled' GROUP BY customer_id HAVING SUM(gross_cents)>=5000",'sql.aggregation.having sql.aggregation.group_by')
add('AGG',6,'lending','Arrival volume versus transaction volume','payment_transactions','loan_id logical_transactions arrivals','loan_id',
 'For loans observed in arrivals, count all received rows and distinct transaction_id values, across all states. This is source volume, not paid principal.',
 'SELECT loan_id,COUNT(DISTINCT transaction_id) AS logical_transactions,COUNT(*) AS arrivals FROM payment_transactions GROUP BY loan_id','sql.aggregation.distinct_counts sql.deduplication.business_keys')
add('AGG',7,'support','Agent queue counters','tickets','agent_id tickets open_tickets rated','agent_id',
 'For assigned agents observed in tickets, report total tickets, open tickets, and known CSAT count. Exclude unassigned tickets from agent-grain output.',
 'SELECT agent_id,COUNT(*) AS tickets,COUNT(*) FILTER(WHERE closed_at IS NULL) AS open_tickets,COUNT(csat) AS rated FROM tickets WHERE agent_id IS NOT NULL GROUP BY agent_id','sql.aggregation.multi_metric sql.aggregation.conditional_aggregation')
add('AGG',8,'travel','Stay-length bounds by destination','bookings','destination min_nights max_nights','destination',
 'For confirmed bookings, compute minimum and maximum nights by destination. Nights = check_out - check_in; same-day stays have zero nights.',
 "SELECT destination,MIN(check_out-check_in) AS min_nights,MAX(check_out-check_in) AS max_nights FROM bookings WHERE status='confirmed' GROUP BY destination",'sql.aggregation.sum_avg_min_max sql.dates.intervals')
add('AGG',9,'retail','Average active trading day','sales','store_id avg_active_day_cents','store_id',
 'For each observed store, sum signed cents per UTC day, then average those daily totals. Average only days with receipt lines, not calendar days. Round to 2 decimals.',
 'WITH daily AS (SELECT store_id,sold_at::date AS day,SUM(cents) AS cents FROM sales GROUP BY store_id,sold_at::date) SELECT store_id,ROUND(AVG(cents),2) AS avg_active_day_cents FROM daily GROUP BY store_id','sql.aggregation.aggregation_levels sql.ctes.decomposition')
add('AGG',10,'insurance','Known and uncertified open reserves','claims','policy_id known_reserve_cents unknown_claims total_reserve_cents','policy_id',
 'For policies with currently open claims, return sum of known signed reserves, count unknown reserves, and total_reserve_cents. The total is NULL if any open claim reserve is unknown; otherwise the known sum. Zero is known, negatives remain adjustments.',
 "SELECT policy_id,COALESCE(SUM(reserve_cents),0) AS known_reserve_cents,COUNT(*) FILTER(WHERE reserve_cents IS NULL) AS unknown_claims,CASE WHEN COUNT(*) FILTER(WHERE reserve_cents IS NULL)>0 THEN NULL ELSE COALESCE(SUM(reserve_cents),0) END AS total_reserve_cents FROM claims WHERE status='open' GROUP BY policy_id",'sql.nulls.unknown_vs_zero sql.aggregation.conditional_aggregation')

# Grain: measures belong to an entity and sometimes to a reporting instant.
add('GRN',1,'retail','Most recent stock position','inventory','store_id sku on_hand','store_id sku',
 'Return the latest dated on_hand for each store x SKU observed in inventory. Stock snapshots must not be summed across dates.',
 'SELECT DISTINCT ON(store_id,sku) store_id,sku,on_hand FROM inventory ORDER BY store_id,sku,day DESC','sql.grain.semi_additive sql.deduplication.latest_version')
add('GRN',2,'banking','Account balances at close','accounts balances','account_id balance_cents','account_id',
 'Include every account. Use its latest balance on or before 2026-10-03; no snapshot means NULL. Do not add snapshots or convert currencies.',
 "WITH last AS (SELECT DISTINCT ON(account_id) account_id,balance_cents FROM balances WHERE day<=DATE '2026-10-03' ORDER BY account_id,day DESC) SELECT a.account_id,l.balance_cents FROM accounts a LEFT JOIN last l USING(account_id)",
 'sql.grain.semi_additive sql.nulls.missing_row_vs_value',transfer='SQL-GRN-001',joins={'accounts:balances':'1:M'})
add('GRN',3,'commerce','Order lines into commitments','orders items','order_id line_cents','order_id',
 'Include every order. Sum line_cents once per item; line_cents already includes quantity. Orders without lines contribute zero. Ignore order header gross for this line reconciliation.',
 'SELECT o.order_id,COALESCE(SUM(i.line_cents),0) AS line_cents FROM orders o LEFT JOIN items i USING(order_id) GROUP BY o.order_id',
 'sql.grain.additive sql.joins.one_to_many',joins={'orders:items':'1:M'},stage='SQL-JOIN-006')
add('GRN',4,'healthcare','Completed appointment capacity','clinics appointments','clinic_id completed_minutes','clinic_id',
 'Include every clinic and sum appointment minutes for completed appointments. Canceled/no-show visits do not consume completed capacity; zero minutes stays zero.',
 "SELECT c.clinic_id,COALESCE(SUM(a.minutes) FILTER(WHERE a.status='completed'),0) AS completed_minutes FROM clinics c LEFT JOIN appointments a USING(clinic_id) GROUP BY c.clinic_id",'sql.grain.additive sql.joins.filtering_semantics',joins={'clinics:appointments':'1:M'})
add('GRN',5,'marketplace','Distinct buyer reach','purchases','seller_id buyers','seller_id',
 'For sellers with completed purchases, count distinct buyer_id values, not purchase rows.',
 "SELECT seller_id,COUNT(DISTINCT buyer_id) AS buyers FROM purchases WHERE status='completed' GROUP BY seller_id",'sql.grain.non_additive sql.aggregation.distinct_counts')
add('GRN',6,'lending','Borrower exposure without FX invention','loans','borrower_id currency exposure_cents','borrower_id currency',
 'Sum original principal by borrower x currency. Do not combine currencies or subtract payments in this origination exposure report.',
 'SELECT borrower_id,currency,SUM(principal_cents) AS exposure_cents FROM loans GROUP BY borrower_id,currency','sql.grain.output_keys business.finance.currency')
add('GRN',7,'advertising','Monthly campaign denominator','ad_daily','campaign_id month ctr','campaign_id month',
 'One row per observed campaign x calendar month. Month is its first date. CTR = summed clicks / summed impressions, rounded to 2 decimals; zero denominator => NULL.',
 "SELECT campaign_id,DATE_TRUNC('month',day)::date AS month,ROUND(SUM(clicks)::numeric/NULLIF(SUM(impressions),0),2) AS ctr FROM ad_daily GROUP BY campaign_id,DATE_TRUNC('month',day)::date",'sql.grain.non_additive sql.aggregation.weighted_averages')
add('GRN',8,'retail','Store calendar grid','stores calendar sales','store_id day cents','store_id day',
 'Every store x every calendar date must exist. Sum signed receipt cents on that UTC date, or zero with no receipts. Ignore receipts outside the calendar.',
 'WITH daily AS (SELECT store_id,sold_at::date AS day,SUM(cents) AS cents FROM sales GROUP BY store_id,sold_at::date) SELECT s.store_id,c.day,COALESCE(d.cents,0) AS cents FROM stores s CROSS JOIN calendar c LEFT JOIN daily d ON d.store_id=s.store_id AND d.day=c.day',
 'sql.grain.output_keys sql.dates.date_spine sql.joins.missing_records' if False else 'sql.grain.output_keys sql.dates.date_spine sql.joins.left',joins={'stores:sales':'1:M','stores:calendar':'M:M'})
add('GRN',9,'insurance','Active policy commitment by holder','policies','holder_id premium_cents','holder_id',
 'At 2026-11-01, sum premiums of active policies by holder. Active means starts_at <= date < ends_at, with NULL end unbounded. Include only holders with active policies.',
 "SELECT holder_id,SUM(premium_cents) AS premium_cents FROM policies WHERE starts_at<=DATE '2026-11-01' AND (ends_at IS NULL OR DATE '2026-11-01'<ends_at) GROUP BY holder_id",'sql.grain.entity_keys sql.dates.half_open')
add('GRN',10,'payments','Payment-level final latency','attempts','payment_id latency_ms','payment_id',
 'Return each logical payment once using its latest attempted_at, then greatest attempt_id as tie-breaker. Preserve NULL latency; this is not an average of retry latencies.',
 'SELECT DISTINCT ON(payment_id) payment_id,latency_ms FROM attempts ORDER BY payment_id,attempted_at DESC,attempt_id DESC','sql.deduplication.business_keys sql.deduplication.deterministic_ties')
add('GRN',11,'banking','Owner movements with currency identity','accounts transactions','owner_id currency movement_cents','owner_id currency',
 'For owner x currency combinations with transactions, sum signed cents including both sides of internal transfers. Unknown cents contributes zero only to this known-movement report.',
 'SELECT a.owner_id,a.currency,COALESCE(SUM(t.cents),0) AS movement_cents FROM accounts a JOIN transactions t USING(account_id) GROUP BY a.owner_id,a.currency','sql.grain.output_keys sql.joins.multi_table business.finance.currency',joins={'accounts:transactions':'1:M'})
add('GRN',12,'lending','Loan principal after approved write-downs','loans payment_transactions charge_offs','loan_id outstanding_cents','loan_id',
 'Every loan: original principal minus latest posted logical payment principal minus all approved charge-off cents. Choose payment by event_at then greatest event_id before filtering status. Signed negative payments reduce paid principal; unknown payment cents contributes zero to this explicitly known-balance exercise. No interest/fees/FX. All arrivals available.',
 "WITH latest AS (SELECT DISTINCT ON(transaction_id) * FROM payment_transactions ORDER BY transaction_id,event_at DESC,event_id DESC), p AS (SELECT loan_id,SUM(principal_cents) AS cents FROM latest WHERE status='posted' GROUP BY loan_id), c AS (SELECT loan_id,SUM(cents) AS cents FROM charge_offs GROUP BY loan_id) SELECT l.loan_id,l.principal_cents-COALESCE(p.cents,0)-COALESCE(c.cents,0) AS outstanding_cents FROM loans l LEFT JOIN p USING(loan_id) LEFT JOIN c USING(loan_id)",
 'sql.joins.preaggregation sql.deduplication.latest_version business.finance.refunds_reversals',joins={'loans:payment_transactions':'1:M','loans:charge_offs':'1:M'})

# Joins: empty parents, two independent many-sides, bridges, and full reconciliation.
add('JOIN',1,'commerce','Customers without placed orders','customers orders','customer_id','customer_id',
 'Return customers with no order rows of any status. A customer with a canceled order has an order and is excluded.',
 'SELECT c.customer_id FROM customers c WHERE NOT EXISTS(SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id)','sql.joins.semi_anti sql.nulls.missing_row_vs_value',joins={'customers:orders':'1:M'})
add('JOIN',2,'retail','Receipt coverage for every store','stores sales','store_id receipt_lines','store_id',
 'Include every store with its count of receipt-line rows, including returns and zero-quantity lines. A store with no rows has count zero.',
 'SELECT s.store_id,COUNT(v.sale_id) AS receipt_lines FROM stores s LEFT JOIN sales v USING(store_id) GROUP BY s.store_id','sql.joins.left sql.aggregation.count_star_column',joins={'stores:sales':'1:M'},
 broken='SELECT s.store_id,COUNT(*) AS receipt_lines FROM stores s LEFT JOIN sales v USING(store_id) GROUP BY s.store_id')
add('JOIN',3,'support','CSAT for every agent','agents tickets','agent_id avg_csat','agent_id',
 'Include every agent. Average known CSAT including zero, rounded to 2 decimals. Agents with no ratings get NULL, whether they have tickets or none.',
 'SELECT a.agent_id,ROUND(AVG(t.csat),2) AS avg_csat FROM agents a LEFT JOIN tickets t USING(agent_id) GROUP BY a.agent_id','sql.joins.left sql.nulls.aggregate_nulls',joins={'agents:tickets':'1:M'},transfer='SQL-AGG-003')
add('JOIN',4,'marketplace','Seller organization width','sellers','seller_id direct_children','seller_id',
 'Include every seller with the number of sellers whose parent_id directly references it. Do not count descendants recursively or count a missing child as one.',
 'SELECT p.seller_id,COUNT(c.seller_id) AS direct_children FROM sellers p LEFT JOIN sellers c ON c.parent_id=p.seller_id GROUP BY p.seller_id','sql.joins.self sql.aggregation.count_star_column',joins={'sellers:sellers':'1:M'})
add('JOIN',5,'marketplace','Seller unpaid commitment','sellers purchases payouts','seller_id unpaid_cents','seller_id',
 'Every seller: completed purchase cents minus payout cents. Each purchase and each payout contributes once. Missing activity contributes zero; no fee assumptions.',
 "WITH p AS (SELECT seller_id,SUM(cents) AS cents FROM purchases WHERE status='completed' GROUP BY seller_id), y AS (SELECT seller_id,SUM(cents) AS cents FROM payouts GROUP BY seller_id) SELECT s.seller_id,COALESCE(p.cents,0)-COALESCE(y.cents,0) AS unpaid_cents FROM sellers s LEFT JOIN p USING(seller_id) LEFT JOIN y USING(seller_id)",
 'sql.joins.fanout sql.joins.preaggregation',joins={'sellers:purchases':'1:M','sellers:payouts':'1:M'},
 broken="SELECT s.seller_id,COALESCE(SUM(p.cents) FILTER(WHERE p.status='completed'),0)-COALESCE(SUM(y.cents),0) AS unpaid_cents FROM sellers s LEFT JOIN purchases p USING(seller_id) LEFT JOIN payouts y USING(seller_id) GROUP BY s.seller_id")
add('JOIN',6,'commerce','Fulfilled order net commitment','orders refunds','order_id net_cents','order_id',
 'For fulfilled orders only, subtract sum of final posted refund amounts from header gross_cents. A header amount belongs to one order, not every refund. Missing refunds => zero; posted amounts are known in fixtures.',
 "WITH r AS (SELECT order_id,SUM(amount_cents) AS cents FROM refunds WHERE status='posted' GROUP BY order_id) SELECT o.order_id,o.gross_cents-COALESCE(r.cents,0) AS net_cents FROM orders o LEFT JOIN r USING(order_id) WHERE o.status='fulfilled'",'sql.joins.fanout sql.joins.preaggregation',joins={'orders:refunds':'1:M'},transfer='SQL-JOIN-005',stage='SQL-JOIN-012')
add('JOIN',7,'payments','Capture exposure per logical payment','attempts captures disputes','payment_id net_exposure_cents','payment_id',
 'Include each payment_id observed in attempts exactly once. Net exposure = all capture cents minus open dispute cents. Count each capture/dispute once, and do not weight by retry count. No captures or disputes => zero.',
 "WITH p AS (SELECT DISTINCT payment_id FROM attempts), c AS (SELECT payment_id,SUM(cents) AS cents FROM captures GROUP BY payment_id), d AS (SELECT payment_id,SUM(cents) AS cents FROM disputes WHERE status='open' GROUP BY payment_id) SELECT p.payment_id,COALESCE(c.cents,0)-COALESCE(d.cents,0) AS net_exposure_cents FROM p LEFT JOIN c USING(payment_id) LEFT JOIN d USING(payment_id)",
 'sql.joins.many_to_many sql.joins.preaggregation sql.deduplication.business_keys',joins={'attempts:captures':'M:M','captures:disputes':'M:M'})
add('JOIN',8,'banking','Statement and ledger exceptions','transactions statement','transaction_id difference_cents','transaction_id',
 'Include the union of transaction IDs from posted movements and statement lines. Difference = known ledger cents minus sum of statement cents. Keep repeated physical statement lines for this reconciliation. Missing side or unknown ledger cents contributes zero to this known-value difference.',
 'WITH s AS (SELECT transaction_id,SUM(cents) AS cents FROM statement GROUP BY transaction_id) SELECT COALESCE(t.transaction_id,s.transaction_id) AS transaction_id,COALESCE(t.cents,0)-COALESCE(s.cents,0) AS difference_cents FROM transactions t FULL JOIN s USING(transaction_id)',
 'sql.joins.full sql.analytics.reconciliation sql.joins.duplicate_matches',joins={'transactions:statement':'1:M'})
add('JOIN',9,'insurance','Open-claim coverage per policy','policies claims','policy_id open_claims','policy_id',
 'Include every policy, counting claim rows whose current status column is open. Policies with only closed/denied claims or no claims get zero.',
 "SELECT p.policy_id,COUNT(c.claim_id) AS open_claims FROM policies p LEFT JOIN claims c ON c.policy_id=p.policy_id AND c.status='open' GROUP BY p.policy_id",'sql.joins.filtering_semantics sql.joins.left',joins={'policies:claims':'1:M'},
 broken="SELECT p.policy_id,COUNT(c.claim_id) AS open_claims FROM policies p LEFT JOIN claims c USING(policy_id) WHERE c.status='open' GROUP BY p.policy_id")
add('JOIN',10,'marketplace','Category allocation without duplication','purchases tags','tag allocated_cents','tag',
 'Sum completed purchase value by seller, then allocate to tags using that seller’s weights. Weights are exact decimals and sum to one. Include tags even when their sellers have zero value. Round allocated_cents to 2 decimals.',
 "WITH p AS (SELECT seller_id,SUM(cents) AS cents FROM purchases WHERE status='completed' GROUP BY seller_id) SELECT t.tag,ROUND(SUM(COALESCE(p.cents,0)*t.weight),2) AS allocated_cents FROM tags t LEFT JOIN p USING(seller_id) GROUP BY t.tag",'sql.joins.bridge_allocation sql.types.precision',joins={'purchases:tags':'M:M'})
add('JOIN',11,'healthcare','Capacity report after procedure enrichment','clinics appointments procedures','clinic_id completed_appointments completed_minutes patients','clinic_id',
 'Include every clinic. Count completed appointments, sum their appointment minutes once, and count distinct completed patients. Procedure rows can multiply an appointment and must not weight any measure. Procedure enrichment is optional for these outputs.',
 "SELECT c.clinic_id,COUNT(a.appointment_id) AS completed_appointments,COALESCE(SUM(a.minutes),0) AS completed_minutes,COUNT(DISTINCT a.patient_id) AS patients FROM clinics c LEFT JOIN appointments a ON a.clinic_id=c.clinic_id AND a.status='completed' GROUP BY c.clinic_id",'sql.joins.fanout sql.grain.non_additive',joins={'clinics:appointments':'1:M','appointments:procedures':'1:M'})
add('JOIN',12,'commerce','Recognition calendar introduced','orders','month recognized_gross_cents','month',
 'Finance now recognizes gross revenue only at fulfilled_at for fulfilled orders. Aggregate all dates by UTC calendar month (first date). Empty months need not exist. Refund recognition is not included yet.',
 "SELECT DATE_TRUNC('month',fulfilled_at)::date AS month,SUM(gross_cents) AS recognized_gross_cents FROM orders WHERE status='fulfilled' GROUP BY DATE_TRUNC('month',fulfilled_at)::date",'sql.dates.buckets business.finance.recognition',stage='SQL-PAT-007')

# Logical decomposition, set semantics and PostgreSQL semi-structured sources.
add('CTE',1,'saas','Account recurring commitment','accounts subscriptions subscription_versions','account_id mrr_cents','account_id',
 'Include every account at 2026-10-03 00:00 UTC. Match subscription versions valid_from <= instant < valid_to (NULL infinity), sum active monthly_cents. Missing active subscriptions => zero. MRR snapshots must not be summed across time.',
 "SELECT a.account_id,COALESCE(SUM(v.monthly_cents) FILTER(WHERE v.status='active'),0) AS mrr_cents FROM accounts a LEFT JOIN subscriptions s USING(account_id) LEFT JOIN subscription_versions v ON v.subscription_id=s.subscription_id AND v.valid_from<=TIMESTAMPTZ '2026-10-03 00:00+00' AND (v.valid_to IS NULL OR TIMESTAMPTZ '2026-10-03 00:00+00'<v.valid_to) GROUP BY a.account_id",'sql.ctes.decomposition sql.dates.as_of sql.grain.semi_additive',joins={'accounts:subscriptions':'1:M','subscriptions:subscription_versions':'1:M'})
add('CTE',2,'subscription','Subscriber lifetime collection','subscribers invoices','subscriber_id ltv_cents','subscriber_id',
 'Every subscriber: sum paid invoice cents, including signed credit invoices. Pending and void invoices do not count. No paid invoices => zero.',
 "WITH paid AS (SELECT subscriber_id,SUM(cents) AS cents FROM invoices WHERE status='paid' GROUP BY subscriber_id) SELECT s.subscriber_id,COALESCE(p.cents,0) AS ltv_cents FROM subscribers s LEFT JOIN paid p USING(subscriber_id)",'sql.ctes.decomposition sql.analytics.ltv',joins={'subscribers:invoices':'1:M'})
add('CTE',3,'travel','Travelers without confirmed bookings','travelers bookings','traveler_id','traveler_id',
 'Return travelers for whom no booking has status confirmed. Canceled bookings do not disqualify them.',
 "SELECT t.traveler_id FROM travelers t WHERE NOT EXISTS(SELECT 1 FROM bookings b WHERE b.traveler_id=t.traveler_id AND b.status='confirmed')",'sql.ctes.not_exists sql.joins.semi_anti',joins={'travelers:bookings':'1:M'},transfer='SQL-JOIN-001')
add('CTE',4,'retail','Products observed on both sides','sales','sku','sku',
 'Return distinct SKUs with both a positive-quantity sale and a negative-quantity return. Same physical receipt row cannot satisfy both conditions.',
 'SELECT sku FROM sales WHERE quantity>0 INTERSECT SELECT sku FROM sales WHERE quantity<0','sql.sets.intersect sql.ctes.subqueries')
add('CTE',5,'banking','Statement-only identities','statement transactions','transaction_id','transaction_id',
 'Return distinct transaction IDs present in statements and absent in account transactions. Amount comparison is outside this population check.',
 'SELECT transaction_id FROM statement EXCEPT SELECT transaction_id FROM transactions','sql.sets.except sql.joins.semi_anti')
add('CTE',6,'payments','Channel attempt union','attempts','payment_id attempt_id','attempt_id',
 'Combine web attempts and app attempts. Retain every physical attempt; do not deduplicate logical payment_id. Missing/NULL/other channels are excluded.',
 "SELECT payment_id,attempt_id FROM attempts WHERE metadata->>'channel'='web' UNION ALL SELECT payment_id,attempt_id FROM attempts WHERE metadata->>'channel'='app'",'sql.sets.union_all sql.semi_structured.json',predict="SELECT payment_id FROM attempts WHERE metadata->>'channel'='web' UNION ALL SELECT payment_id FROM attempts WHERE metadata->>'channel'='app'")
add('CTE',7,'commerce','Observed customer population','orders events','customer_id','customer_id',
 'Combine customers appearing in any orders or product events. Return each customer_id once, irrespective of event count and order state.',
 'SELECT customer_id FROM orders UNION SELECT customer_id FROM events','sql.sets.union sql.deduplication.exact_rows')
add('CTE',8,'payments','Risk extraction under schema drift','attempts','attempt_id risk','attempt_id',
 'For every attempt, extract metadata risk as integer only when its text consists entirely of digits. Missing key, JSON null and malformed strings produce NULL. Fixture digit values fit integer range.',
 "SELECT attempt_id,CASE WHEN metadata->>'risk' ~ '^[0-9]+$' THEN (metadata->>'risk')::integer ELSE NULL END AS risk FROM attempts",'sql.types.safe_casts sql.semi_structured.schema_variability sql.strings.like_regex')
add('CTE',9,'wallet','Risk signal frequency','risk_events','signal observations','signal',
 'Expand signals arrays and count signal occurrences across risk observations. Empty arrays contribute no rows. Each array element is an occurrence; do not count one row per wallet.',
 'SELECT signal,COUNT(*) AS observations FROM risk_events CROSS JOIN LATERAL UNNEST(signals) AS u(signal) GROUP BY signal','sql.semi_structured.arrays sql.semi_structured.unnesting')
add('CTE',10,'advertising','Conversion touch assignment','conversions touches','conversion_id campaign_id','conversion_id',
 'Every conversion gets its latest touch for the same user within [conversion time - 7 days, conversion time], breaking tied times by greatest touch_id. No eligible touch => campaign_id NULL. A future touch is ineligible.',
 "SELECT c.conversion_id,(SELECT t.campaign_id FROM touches t WHERE t.user_id=c.user_id AND t.touched_at BETWEEN c.converted_at-INTERVAL '7 days' AND c.converted_at ORDER BY t.touched_at DESC,t.touch_id DESC LIMIT 1) AS campaign_id FROM conversions c",'sql.ctes.correlated sql.analytics.last_touch sql.deduplication.deterministic_ties',joins={'conversions:touches':'M:M'})

# Windows preserve the event grain while making the partition/frame explicit.
add('WIN',1,'banking','Account movement timeline','transactions','transaction_id running_cents','transaction_id',
 'For every movement, cumulative signed known cents within account ordered by posted_at then transaction_id ascending. Unknown cents contributes zero. Use a row-based cumulative frame.',
 'SELECT transaction_id,SUM(COALESCE(cents,0)) OVER(PARTITION BY account_id ORDER BY posted_at,transaction_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cents FROM transactions','sql.windows.running_totals sql.windows.frames',window=True)
add('WIN',2,'retail','Product value positions','sales','store_id sku value_rank','store_id sku',
 'Sum signed receipt cents by store x SKU. Rank values descending within store with equal values sharing the same rank and no rank gaps.',
 'WITH g AS (SELECT store_id,sku,SUM(cents) AS cents FROM sales GROUP BY store_id,sku) SELECT store_id,sku,DENSE_RANK() OVER(PARTITION BY store_id ORDER BY cents DESC) AS value_rank FROM g','sql.windows.rank_dense_rank sql.windows.ranking_ties',window=True)
add('WIN',3,'marketplace','Two sellers per region','sellers purchases','region seller_id position','seller_id',
 'For every region, return up to exactly two sellers with greatest completed purchase value, including zero-value sellers. Ties break by seller_id ascending. Position starts at one within each region.',
 "WITH g AS (SELECT s.seller_id,s.region,COALESCE(SUM(p.cents) FILTER(WHERE p.status='completed'),0) AS cents FROM sellers s LEFT JOIN purchases p USING(seller_id) GROUP BY s.seller_id,s.region), ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY region ORDER BY cents DESC,seller_id) AS position FROM g) SELECT region,seller_id,position FROM ranked WHERE position<=2",'sql.windows.row_number sql.deduplication.deterministic_ties',window=True,joins={'sellers:purchases':'1:M'})
add('WIN',4,'support','First response timeline','tickets ticket_events','ticket_id first_reply_at','ticket_id',
 'Every ticket: earliest event_at whose action is replied. No reply => NULL. Multiple replies or reopened tickets do not change the first response.',
 "WITH r AS (SELECT DISTINCT ticket_id,FIRST_VALUE(event_at) OVER(PARTITION BY ticket_id ORDER BY event_at,event_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_reply_at FROM ticket_events WHERE action='replied') SELECT t.ticket_id,r.first_reply_at FROM tickets t LEFT JOIN r USING(ticket_id)",'sql.windows.first_last sql.windows.partition_order',window=True,joins={'tickets:ticket_events':'1:M'})
add('WIN',5,'logistics','Next observed shipment event','shipment_events','event_id next_event_at','event_id',
 'Keep every received shipment event. Return the next event_at within the same shipment ordered by event_at then event_id ascending. Last event in its shipment has NULL; do not deduplicate.',
 'SELECT event_id,LEAD(event_at) OVER(PARTITION BY shipment_id ORDER BY event_at,event_id) AS next_event_at FROM shipment_events','sql.windows.lag_lead sql.windows.partition_order',window=True)
add('WIN',6,'subscription','Two-invoice collection average','invoices','invoice_id moving_cents','invoice_id',
 'For paid invoices only, average current and previous paid invoice cents within subscriber ordered by invoiced_at then invoice_id. Signed credits count. First invoice averages itself. Round to 2 decimals.',
 "SELECT invoice_id,ROUND(AVG(cents) OVER(PARTITION BY subscriber_id ORDER BY invoiced_at,invoice_id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW),2) AS moving_cents FROM invoices WHERE status='paid'",'sql.windows.moving_average sql.windows.frames',window=True)
add('WIN',7,'payments','Attempt workload alongside events','attempts','attempt_id merchant_attempts','attempt_id',
 'Return every attempt and the total number of attempts for its merchant, without collapsing event rows or excluding unknown success.',
 'SELECT attempt_id,COUNT(*) OVER(PARTITION BY merchant_id) AS merchant_attempts FROM attempts','sql.windows.count_over sql.grain.output_keys',window=True)
add('WIN',8,'commerce','Previous order commitment','orders','order_id prior_gross_cents','order_id',
 'For every order of any status, return the previous order gross_cents within customer ordered by ordered_at then order_id ascending. First order has NULL, not zero.',
 'SELECT order_id,LAG(gross_cents) OVER(PARTITION BY customer_id ORDER BY ordered_at,order_id) AS prior_gross_cents FROM orders','sql.windows.lag_lead sql.nulls.unknown_vs_zero',window=True,transfer='SQL-WIN-005')
add('WIN',9,'banking','Final movement visible on every row','transactions','transaction_id final_cents','transaction_id',
 'Keep every movement. Show the cents of the final movement in that account ordered by posted_at then transaction_id ascending. Respect NULL if the final cents is unknown; the frame must cover the entire partition.',
 'SELECT transaction_id,LAST_VALUE(cents) OVER(PARTITION BY account_id ORDER BY posted_at,transaction_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS final_cents FROM transactions','sql.windows.first_last sql.windows.frames',window=True,
 broken='SELECT transaction_id,LAST_VALUE(cents) OVER(PARTITION BY account_id ORDER BY posted_at,transaction_id) AS final_cents FROM transactions')
add('WIN',10,'payments','Merchant latency median','attempts','merchant_id median_ms','merchant_id',
 'For merchants with known latencies, compute the continuous median of latency_ms across all attempts. Even populations interpolate the two central values; unknown values are excluded. Round to 2 decimals.',
 'SELECT merchant_id,ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP(ORDER BY latency_ms))::numeric,2) AS median_ms FROM attempts WHERE latency_ms IS NOT NULL GROUP BY merchant_id','sql.analytics.percentiles sql.nulls.aggregate_nulls')
add('WIN',11,'retail','Sequential and peer-visible revenue','sales','sale_id row_total peer_total','sale_id',
 'Keep every receipt line. row_total sums signed cents within store ordered by sold_at then sale_id with a ROWS cumulative frame. peer_total sums all same-store rows whose sold_at <= current sold_at, including timestamp peers.',
 'SELECT sale_id,SUM(cents) OVER(PARTITION BY store_id ORDER BY sold_at,sale_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS row_total,SUM(cents) OVER(PARTITION BY store_id ORDER BY sold_at RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS peer_total FROM sales','sql.windows.rows_range sql.windows.frames',window=True,transfer='SQL-WIN-001')
add('WIN',12,'payments','Operational latency quartiles','attempts','attempt_id quartile','attempt_id',
 'Exclude unknown latency and assign NTILE(4) over all known attempts ordered by latency_ms then attempt_id ascending. Larger buckets come first when row counts are uneven; this is a row-count bucket, not percentile boundaries.',
 'SELECT attempt_id,NTILE(4) OVER(ORDER BY latency_ms,attempt_id) AS quartile FROM attempts WHERE latency_ms IS NOT NULL','sql.windows.ntile sql.deduplication.deterministic_ties',window=True)

# Survivor semantics differ from raw ingestion and from historical availability.
add('DED',1,'lending','Principal payment balance','loans payment_transactions','loan_id paid_cents','loan_id',
 'Include every loan. Latest event_at then greatest event_id wins per transaction_id; select before filtering posted. Sum signed posted principal_cents; NULL contributes zero to this known-paid KPI. Reversals remove the whole transaction, not a new negative payment. All arrivals available.',
 "WITH p AS (SELECT DISTINCT ON(transaction_id) * FROM payment_transactions ORDER BY transaction_id,event_at DESC,event_id DESC) SELECT l.loan_id,COALESCE(SUM(p.principal_cents) FILTER(WHERE p.status='posted'),0) AS paid_cents FROM loans l LEFT JOIN p USING(loan_id) GROUP BY l.loan_id",'sql.deduplication.latest_version sql.deduplication.status_after_resolution sql.windows.row_number',joins={'loans:payment_transactions':'1:M'},transfer='SQL-GRN-010',
 broken="SELECT l.loan_id,COALESCE(SUM(p.principal_cents) FILTER(WHERE p.status='posted'),0) AS paid_cents FROM loans l LEFT JOIN payment_transactions p USING(loan_id) GROUP BY l.loan_id")
add('DED',2,'wallet','Final posted transfer records','wallet_events','transfer_id wallet_id cents','transfer_id',
 'Resolve each transfer_id by event_at descending then event_id descending, then keep only posted. Preserve NULL cents; zero and unknown differ. A later reversed state disqualifies the transfer.',
 "WITH p AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY transfer_id ORDER BY event_at DESC,event_id DESC) AS rn FROM wallet_events) SELECT transfer_id,wallet_id,cents FROM p WHERE rn=1 AND status='posted'",'sql.deduplication.latest_version sql.deduplication.deterministic_ties sql.windows.row_number',window=True,transfer='SQL-DED-001')
add('DED',3,'logistics','Currently delivered shipments','shipments shipment_events','shipment_id','shipment_id',
 'Return shipments whose latest business event status is delivered. Order by event_at then greatest event_id, not received_at. Select the state before filtering delivered; a later returned state supersedes delivery.',
 "WITH e AS (SELECT DISTINCT ON(shipment_id) * FROM shipment_events ORDER BY shipment_id,event_at DESC,event_id DESC) SELECT s.shipment_id FROM shipments s JOIN e USING(shipment_id) WHERE e.status='delivered'",'sql.deduplication.latest_version sql.deduplication.status_after_resolution sql.dates.event_processing',joins={'shipments:shipment_events':'1:M'},transfer='SQL-DED-002')
add('DED',4,'insurance','Open claims under final state','claims claim_events','claim_id reserve_cents','claim_id',
 'Return claims whose latest event status is open, choosing event_at then greatest event_id. Preserve the original reserve_cents including NULL. The claims status column is a prior snapshot and is not the final event state.',
 "WITH e AS (SELECT DISTINCT ON(claim_id) * FROM claim_events ORDER BY claim_id,event_at DESC,event_id DESC) SELECT c.claim_id,c.reserve_cents FROM claims c JOIN e USING(claim_id) WHERE e.status='open'",'sql.deduplication.latest_version sql.deduplication.status_after_resolution',joins={'claims:claim_events':'1:M'},transfer='SQL-DED-003')
add('DED',5,'subscription','Subscriber state population','subscription_events','status subscribers','status',
 'Resolve one final state per subscriber by event_at then greatest event_id, and count subscribers by that state. Subscribers without any event are not in this observed-state report.',
 'WITH e AS (SELECT DISTINCT ON(subscriber_id) * FROM subscription_events ORDER BY subscriber_id,event_at DESC,event_id DESC) SELECT status,COUNT(*) AS subscribers FROM e GROUP BY status','sql.deduplication.latest_version sql.deduplication.deterministic_ties',transfer='SQL-DED-004')
add('DED',6,'commerce','Unique logical product observations','events','customer_id event_type event_at','customer_id event_type event_at',
 'Delivery IDs are transport identities. For this telemetry producer, identical customer_id x event_type x event_at tuples are repeat deliveries of one observation. Return distinct tuples, preserving event time. Different times are different observations.',
 'SELECT DISTINCT customer_id,event_type,event_at FROM events','sql.deduplication.exact_rows sql.deduplication.ingestion_retries')
add('DED',7,'lending','What the report could know at close','loans payment_transactions','loan_id known_paid_cents','loan_id',
 'At processing cutoff 2026-10-04 00:00 UTC, include only arrivals with received_at < cutoff, then choose latest event_at/event_id per transaction. Sum posted signed principal by every loan, unknown => zero in this known-paid report. Events received later were unavailable even if their event time is old.',
 "WITH e AS (SELECT DISTINCT ON(transaction_id) * FROM payment_transactions WHERE received_at<TIMESTAMPTZ '2026-10-04 00:00+00' ORDER BY transaction_id,event_at DESC,event_id DESC) SELECT l.loan_id,COALESCE(SUM(e.principal_cents) FILTER(WHERE e.status='posted'),0) AS known_paid_cents FROM loans l LEFT JOIN e USING(loan_id) GROUP BY l.loan_id",'sql.deduplication.late_duplicates sql.dates.event_processing sql.deduplication.latest_version',joins={'loans:payment_transactions':'1:M'})
add('DED',8,'lending','State before a historical boundary','loans loan_status_history','loan_id status','loan_id',
 'For every loan, report the last status strictly before 2026-10-03 00:00 UTC by event_at then greatest event_id. No earlier state => NULL. Do not use the final present-day state.',
 "WITH e AS (SELECT DISTINCT ON(loan_id) * FROM loan_status_history WHERE event_at<TIMESTAMPTZ '2026-10-03 00:00+00' ORDER BY loan_id,event_at DESC,event_id DESC) SELECT l.loan_id,e.status FROM loans l LEFT JOIN e USING(loan_id)",'sql.dates.as_of sql.deduplication.max_timestamp_join sql.deduplication.deterministic_ties',joins={'loans:loan_status_history':'1:M'})

# Calendar boundaries and business clocks.
add('DATE',1,'commerce','October order intake','orders','order_id','order_id',
 'Return orders placed during October 2026 UTC, including midnight on October 1 and excluding midnight on November 1. Include every status.',
 "SELECT order_id FROM orders WHERE ordered_at>=TIMESTAMPTZ '2026-10-01 00:00+00' AND ordered_at<TIMESTAMPTZ '2026-11-01 00:00+00'",'sql.dates.half_open',
 broken="SELECT order_id FROM orders WHERE ordered_at BETWEEN TIMESTAMPTZ '2026-10-01 00:00+00' AND TIMESTAMPTZ '2026-11-01 00:00+00'")
add('DATE',2,'advertising','ISO reporting weeks','ad_daily','campaign_id iso_year iso_week clicks','campaign_id iso_year iso_week',
 'Sum clicks by campaign x ISO week-year x ISO week. ISO week-year can differ from calendar year. Include all observed dates.',
 'SELECT campaign_id,EXTRACT(ISOYEAR FROM day)::integer AS iso_year,EXTRACT(WEEK FROM day)::integer AS iso_week,SUM(clicks) AS clicks FROM ad_daily GROUP BY campaign_id,EXTRACT(ISOYEAR FROM day),EXTRACT(WEEK FROM day)','sql.dates.iso_week')
add('DATE',3,'retail','July fiscal reporting','sales','store_id fiscal_year fiscal_quarter cents','store_id fiscal_year fiscal_quarter',
 'Fiscal years start July 1 and are labeled by starting year. Fiscal quarter 1 is July–September. Sum signed cents by store x fiscal year x quarter.',
 "SELECT store_id,EXTRACT(YEAR FROM sold_at-INTERVAL '6 months')::integer AS fiscal_year,EXTRACT(QUARTER FROM sold_at-INTERVAL '6 months')::integer AS fiscal_quarter,SUM(cents) AS cents FROM sales GROUP BY store_id,EXTRACT(YEAR FROM sold_at-INTERVAL '6 months'),EXTRACT(QUARTER FROM sold_at-INTERVAL '6 months')",'sql.dates.calendar_fiscal')
add('DATE',4,'healthcare','Local hourly clinic workload','clinics appointments','clinic_id local_day local_hour appointments','clinic_id local_day local_hour',
 'Count completed appointments by clinic x local calendar date x local wall-clock hour using clinics.timezone. During the autumn repeated hour, both occurrences belong to the same displayed hourly bucket. Exclude canceled/no-show.',
 "SELECT c.clinic_id,(a.scheduled_at AT TIME ZONE c.timezone)::date AS local_day,EXTRACT(HOUR FROM a.scheduled_at AT TIME ZONE c.timezone)::integer AS local_hour,COUNT(*) AS appointments FROM clinics c JOIN appointments a USING(clinic_id) WHERE a.status='completed' GROUP BY c.clinic_id,(a.scheduled_at AT TIME ZONE c.timezone)::date,EXTRACT(HOUR FROM a.scheduled_at AT TIME ZONE c.timezone)", 'sql.dates.timezones sql.dates.dst',joins={'clinics:appointments':'1:M'})
add('DATE',5,'healthcare','Clinic service-day calendar','clinics appointments','clinic_id service_day appointments','clinic_id service_day',
 'A clinic service day begins at 09:00 local wall-clock time. Completed appointments before 09:00 belong to the previous date. Group by clinic x service_day, using each clinic timezone.',
 "SELECT c.clinic_id,((a.scheduled_at AT TIME ZONE c.timezone)-INTERVAL '9 hours')::date AS service_day,COUNT(*) AS appointments FROM clinics c JOIN appointments a USING(clinic_id) WHERE a.status='completed' GROUP BY c.clinic_id,((a.scheduled_at AT TIME ZONE c.timezone)-INTERVAL '9 hours')::date",'sql.dates.timezones sql.dates.intervals',joins={'clinics:appointments':'1:M'})
add('DATE',6,'commerce','Seven-day recognized commitments','calendar orders','day rolling_cents','day',
 'For every calendar date, sum fulfilled order gross recognized on fulfilled_at UTC date during [day-6 days, day]. Include recognized orders outside the displayed calendar if they fall in a rolling interval. No activity => zero.',
 "SELECT c.day,COALESCE(SUM(o.gross_cents),0) AS rolling_cents FROM calendar c LEFT JOIN orders o ON o.status='fulfilled' AND o.fulfilled_at>=c.day-INTERVAL '6 days' AND o.fulfilled_at<c.day+INTERVAL '1 day' GROUP BY c.day",'sql.dates.rolling_period sql.dates.date_spine',joins={'calendar:orders':'M:M'})
add('DATE',7,'subscription','Activity streak boundaries','activity','subscriber_id start_day end_day streak_days','subscriber_id start_day',
 'Identify maximal consecutive-calendar-date activity streaks per subscriber. Activity is already unique by subscriber x day. Output inclusive start/end and day count. A missing date starts a new streak.',
 "WITH a AS (SELECT *,day-ROW_NUMBER() OVER(PARTITION BY subscriber_id ORDER BY day)::integer AS island FROM activity) SELECT subscriber_id,MIN(day) AS start_day,MAX(day) AS end_day,COUNT(*) AS streak_days FROM a GROUP BY subscriber_id,island",'sql.analytics.gaps_islands sql.windows.row_number',window=True)
add('DATE',8,'insurance','Covered calendar days','policies','policy_id coverage_days','policy_id',
 'For policies with finite ends_at, return number of covered dates in [starts_at, ends_at). Include leap day when within the interval. Exclude open-ended policies; this is elapsed days, not inclusive endpoint count.',
 'SELECT policy_id,ends_at-starts_at AS coverage_days FROM policies WHERE ends_at IS NOT NULL','sql.dates.leap_year sql.dates.half_open')

# Analytical questions include their eligibility, denominators and clocks.
add('PAT',1,'commerce','Ordered checkout conversion','customers events','customer_id eligible converted','customer_id',
 'Every customer: eligible=1 if any view exists, else 0. converted=1 if there is a strictly time-ordered view < cart < purchase with purchase <= view+24 hours. Delivery duplicates do not create conversions. Optional unrelated events may occur between steps.',
 "SELECT u.customer_id,CASE WHEN EXISTS(SELECT 1 FROM events v WHERE v.customer_id=u.customer_id AND v.event_type='view') THEN 1 ELSE 0 END AS eligible,CASE WHEN EXISTS(SELECT 1 FROM events v JOIN events c ON c.customer_id=v.customer_id AND c.event_type='cart' AND c.event_at>v.event_at JOIN events p ON p.customer_id=v.customer_id AND p.event_type='purchase' AND p.event_at>c.event_at AND p.event_at<=v.event_at+INTERVAL '24 hours' WHERE v.customer_id=u.customer_id AND v.event_type='view') THEN 1 ELSE 0 END AS converted FROM customers u",'sql.analytics.ordered_funnels sql.analytics.funnels sql.ctes.exists',joins={'customers:events':'1:M','events:events':'M:M'})
for n,window,tag in [(2,"a.day=s.joined_at::date+1",'sql.analytics.retention'),(3,"a.day BETWEEN s.joined_at::date+1 AND s.joined_at::date+3",'sql.analytics.cohort_denominators')]:
 add('PAT',n,'subscription','Signup return measurement '+str(n),'subscribers activity','cohort_day subscribers retained retention_rate','cohort_day',
  ('Group all subscribers by UTC signup date. Retained means activity exactly on signup date+1.' if n==2 else 'Group all subscribers by UTC signup date. Retained means any activity on days 1 through 3 after signup, inclusive.')+' Denominator is all cohort subscribers, including never active. All cohort windows are fully observed in this synthetic extract. Round rate to 2 decimals.',
  f"WITH s AS (SELECT s.*,CASE WHEN EXISTS(SELECT 1 FROM activity a WHERE a.subscriber_id=s.subscriber_id AND {window}) THEN 1 ELSE 0 END AS retained FROM subscribers s) SELECT joined_at::date AS cohort_day,COUNT(*) AS subscribers,SUM(retained) AS retained,ROUND(SUM(retained)::numeric/COUNT(*),2) AS retention_rate FROM s GROUP BY joined_at::date",f'sql.analytics.cohorts {tag}',joins={'subscribers:activity':'1:M'})
add('PAT',4,'subscription','Signup cohort lifetime collections','subscribers invoices','cohort_month subscribers ltv_cents avg_ltv_cents','cohort_month',
 'Group every subscriber by UTC signup month (first date). LTV is signed paid invoice cents across all available lifetime, excluding void/pending. Include subscribers with no collections in both population and average denominator. No activity => zero. Round average cents to 2 decimals.',
 "WITH i AS (SELECT subscriber_id,SUM(cents) AS cents FROM invoices WHERE status='paid' GROUP BY subscriber_id) SELECT DATE_TRUNC('month',s.joined_at)::date AS cohort_month,COUNT(*) AS subscribers,SUM(COALESCE(i.cents,0)) AS ltv_cents,ROUND(AVG(COALESCE(i.cents,0)),2) AS avg_ltv_cents FROM subscribers s LEFT JOIN i USING(subscriber_id) GROUP BY DATE_TRUNC('month',s.joined_at)::date",'sql.analytics.cohorts sql.analytics.ltv sql.analytics.cohort_denominators',joins={'subscribers:invoices':'1:M'})
add('PAT',5,'advertising','Last-touch campaign return','campaigns ad_daily conversions touches','campaign_id attributed_cents roas','campaign_id',
 'Include every campaign. Assign each conversion to its latest same-user touch within inclusive trailing 7 days, tie-break greatest touch_id; no eligible touch means unattributed. attributed_cents sums assigned conversion values. ROAS divides by lifetime campaign spend_cents; no spend => NULL. Round ratio to 2 decimals. The conversions campaign_id field is legacy and must not determine attribution.',
 "WITH attributed AS (SELECT c.value_cents,(SELECT t.campaign_id FROM touches t WHERE t.user_id=c.user_id AND t.touched_at BETWEEN c.converted_at-INTERVAL '7 days' AND c.converted_at ORDER BY t.touched_at DESC,t.touch_id DESC LIMIT 1) AS campaign_id FROM conversions c), a AS (SELECT campaign_id,SUM(value_cents) AS cents FROM attributed GROUP BY campaign_id), s AS (SELECT campaign_id,SUM(spend_cents) AS cents FROM ad_daily GROUP BY campaign_id) SELECT c.campaign_id,COALESCE(a.cents,0) AS attributed_cents,ROUND(COALESCE(a.cents,0)::numeric/NULLIF(s.cents,0),2) AS roas FROM campaigns c LEFT JOIN a USING(campaign_id) LEFT JOIN s USING(campaign_id)",'sql.analytics.last_touch sql.joins.preaggregation sql.aggregation.ratios_zero',joins={'campaigns:ad_daily':'1:M','conversions:touches':'M:M'})
add('PAT',6,'lending','Collection age under an explicit allocation rule','loans scheduled_payments payment_transactions','loan_id days_past_due','loan_id',
 'As of 2026-10-06 UTC date: latest transaction event_at/event_id wins, then posted signed principal is allocated oldest installment first, including partial payments. All arrivals are available in this retrospective report; unknown principal contributes zero to known-paid allocation. Installments with due date strictly before as-of are due. Earliest installment whose cumulative due exceeds known paid defines days_past_due; none => 0. Ignore interest, fees, charge-offs, grace periods and supplied delinquency snapshots. State why this fixture rule needs Finance approval for production.',
 "WITH e AS (SELECT DISTINCT ON(transaction_id) * FROM payment_transactions ORDER BY transaction_id,event_at DESC,event_id DESC), p AS (SELECT loan_id,SUM(principal_cents) AS cents FROM e WHERE status='posted' GROUP BY loan_id), s AS (SELECT *,SUM(due_cents) OVER(PARTITION BY loan_id ORDER BY due_at,schedule_id ROWS UNBOUNDED PRECEDING) AS due FROM scheduled_payments), d AS (SELECT s.loan_id,MIN(due_at::date) AS first_due FROM s LEFT JOIN p USING(loan_id) WHERE due_at::date<DATE '2026-10-06' AND s.due>COALESCE(p.cents,0) GROUP BY s.loan_id) SELECT l.loan_id,COALESCE(DATE '2026-10-06'-d.first_due,0) AS days_past_due FROM loans l LEFT JOIN d USING(loan_id)",'sql.windows.running_totals business.finance.refunds_reversals sql.dates.as_of',joins={'loans:scheduled_payments':'1:M','loans:payment_transactions':'1:M'},window=True)
add('PAT',7,'commerce','Finance recognition after refunds','orders refunds','month recognized_net_cents','month',
 'Finance policy: fulfilled order gross recognized in UTC month of fulfillment; final posted refunds of fulfilled orders recognized in UTC month of refund_at. Open/canceled orders and their refunds excluded. Months with qualifying recognition events exist even if net zero. Return first date of each month. Do not backdate refunds to fulfillment. No FX.',
 "WITH e AS (SELECT fulfilled_at AS at,gross_cents AS cents FROM orders WHERE status='fulfilled' UNION ALL SELECT r.refund_at,-r.amount_cents FROM refunds r JOIN orders o USING(order_id) WHERE o.status='fulfilled' AND r.status='posted') SELECT DATE_TRUNC('month',at)::date AS month,SUM(cents) AS recognized_net_cents FROM e GROUP BY DATE_TRUNC('month',at)::date",'business.finance.recognition sql.sets.union_all sql.joins.fanout',joins={'orders:refunds':'1:M'},stage='SQL-ADV-009')
add('PAT',8,'marketplace','Purchase cohort repeat behavior','purchases','cohort_month buyers repeat_buyers repeat_rate','cohort_month',
 'Completed purchases define buyer cohort by first purchase UTC month. Repeat means another completed purchase strictly later than the first timestamp and within 7 elapsed days inclusive. Same-time purchases are not returns. Denominator is all buyers in cohort. All windows are fully observed; exclude refunded/canceled. Round rate to 2 decimals.',
 "WITH f AS (SELECT buyer_id,MIN(bought_at) AS first_at FROM purchases WHERE status='completed' GROUP BY buyer_id), r AS (SELECT f.*,CASE WHEN EXISTS(SELECT 1 FROM purchases p WHERE p.buyer_id=f.buyer_id AND p.status='completed' AND p.bought_at>f.first_at AND p.bought_at<=f.first_at+INTERVAL '7 days') THEN 1 ELSE 0 END AS repeated FROM f) SELECT DATE_TRUNC('month',first_at)::date AS cohort_month,COUNT(*) AS buyers,SUM(repeated) AS repeat_buyers,ROUND(SUM(repeated)::numeric/COUNT(*),2) AS repeat_rate FROM r GROUP BY DATE_TRUNC('month',first_at)::date",'sql.analytics.cohorts sql.analytics.retention sql.analytics.cohort_denominators')

# Staff/Principal: executable candidates plus independently reviewed judgment.
add('ADV',1,'support','Review the team closure report','agents tickets','agent_id closed_tickets','agent_id',
 'Pull request: every agent needs a count of closed tickets. Include agents with no closed tickets as zero. Review correctness, grain, joins, readability, maintenance, edge cases, performance, business definition and tests before repairing.',
 'SELECT a.agent_id,COUNT(t.ticket_id) AS closed_tickets FROM agents a LEFT JOIN tickets t ON t.agent_id=a.agent_id AND t.closed_at IS NOT NULL GROUP BY a.agent_id','sql.joins.filtering_semantics sql.performance.join_aggregation',joins={'agents:tickets':'1:M'},
 broken='SELECT a.agent_id,COUNT(t.ticket_id) AS closed_tickets FROM agents a LEFT JOIN tickets t USING(agent_id) WHERE t.closed_at IS NOT NULL GROUP BY a.agent_id')
add('ADV',2,'banking','Review the movement timeline','transactions','transaction_id running_cents','transaction_id',
 'Every transaction needs cumulative known signed cents within its account by posted_at then transaction_id ascending, row-based frame. Unknown contributes zero. Review the submitted report and propose a reusable validated model under late arrivals.',
 'SELECT transaction_id,SUM(COALESCE(cents,0)) OVER(PARTITION BY account_id ORDER BY posted_at,transaction_id ROWS UNBOUNDED PRECEDING) AS running_cents FROM transactions','sql.windows.partition_order sql.windows.frames sql.performance.sort_window',window=True,
 broken='SELECT transaction_id,SUM(COALESCE(cents,0)) OVER(ORDER BY posted_at RANGE UNBOUNDED PRECEDING) AS running_cents FROM transactions')
add('ADV',3,'healthcare','Review enriched capacity accounting','clinics appointments procedures','clinic_id completed_appointments completed_minutes patients','clinic_id',
 'Every clinic needs count of completed appointments, sum of appointment minutes once, distinct completed patients. Procedure lines enrich appointments; assess whether they belong in this metric query at all, and define checks that catch future grain drift.',
 "SELECT c.clinic_id,COUNT(a.appointment_id) AS completed_appointments,COALESCE(SUM(a.minutes),0) AS completed_minutes,COUNT(DISTINCT a.patient_id) AS patients FROM clinics c LEFT JOIN appointments a ON a.clinic_id=c.clinic_id AND a.status='completed' GROUP BY c.clinic_id",'sql.joins.fanout sql.grain.non_additive sql.performance.join_aggregation',joins={'clinics:appointments':'1:M','appointments:procedures':'1:M'},
 broken="SELECT c.clinic_id,COUNT(a.appointment_id) AS completed_appointments,COALESCE(SUM(a.minutes),0) AS completed_minutes,COUNT(DISTINCT a.patient_id) AS patients FROM clinics c LEFT JOIN appointments a ON a.clinic_id=c.clinic_id AND a.status='completed' LEFT JOIN procedures p USING(appointment_id) GROUP BY c.clinic_id")
add('ADV',4,'support','Agents needing closure support','agents tickets','agent_id','agent_id',
 'Return agents with no closed ticket. Unassigned tickets have NULL agent_id and do not exclude every agent. Explain the relevant missing-value semantics and whether a semi/anti-join reduces unnecessary intermediate rows.',
 'SELECT a.agent_id FROM agents a WHERE NOT EXISTS(SELECT 1 FROM tickets t WHERE t.agent_id=a.agent_id AND t.closed_at IS NOT NULL)','sql.nulls.not_in_null sql.ctes.not_exists sql.performance.plans',joins={'agents:tickets':'1:M'},
 broken='SELECT agent_id FROM agents WHERE agent_id NOT IN(SELECT agent_id FROM tickets WHERE closed_at IS NOT NULL)')
add('ADV',5,'payments','Merchant disputed capture ratio','merchants attempts captures disputes','merchant_id dispute_rate','merchant_id',
 'Every merchant: sum cents of open disputes / all capture cents, rounded to 2 decimals, no captures => NULL. Each payment belongs to one merchant; attempts may repeat. Resolve merchant identity once per payment. No currency conversion or netting of closed disputes. Defend metric ownership and reconciliation checks.',
 "WITH p AS (SELECT DISTINCT payment_id,merchant_id FROM attempts), d AS (SELECT p.merchant_id,SUM(d.cents) AS cents FROM p JOIN disputes d USING(payment_id) WHERE d.status='open' GROUP BY p.merchant_id), c AS (SELECT merchant_id,SUM(cents) AS cents FROM captures GROUP BY merchant_id) SELECT m.merchant_id,ROUND(COALESCE(d.cents,0)::numeric/NULLIF(c.cents,0),2) AS dispute_rate FROM merchants m LEFT JOIN d USING(merchant_id) LEFT JOIN c USING(merchant_id)",'sql.joins.many_to_many sql.aggregation.ratios_zero sql.performance.materialization',joins={'attempts:captures':'M:M','captures:disputes':'M:M'})
add('ADV',6,'retail','October scan budget','sales','store_id cents','store_id',
 'Sum signed receipt cents per store for October 2026 UTC only. Hypothetical production source has 5B receipt lines partitioned by UTC sold_at day. Explain scan/filter/aggregate operations, predicate pushdown, pruning conditions and how you would verify the actual warehouse plan. CTE organization alone proves no speedup.',
 "SELECT store_id,SUM(cents) AS cents FROM sales WHERE sold_at>=TIMESTAMPTZ '2026-10-01 00:00+00' AND sold_at<TIMESTAMPTZ '2026-11-01 00:00+00' GROUP BY store_id",'sql.performance.scan_filter sql.performance.plans sql.ctes.physical_vs_logical')
add('ADV',7,'support','Latest-two rating review','tickets','ticket_id moving_csat','ticket_id',
 'For every rated ticket including unassigned tickets, average its and the preceding rated ticket CSAT within agent_id, ordered by opened_at then ticket_id, round 2 decimals. NULL agent_id is one unassigned partition for this operational report. Explain sort cost and stable ordering.',
 'SELECT ticket_id,ROUND(AVG(csat) OVER(PARTITION BY agent_id ORDER BY opened_at,ticket_id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW),2) AS moving_csat FROM tickets WHERE csat IS NOT NULL','sql.windows.frames sql.windows.partition_order sql.performance.sort_window',window=True,
 broken='SELECT ticket_id,ROUND(AVG(csat) OVER(PARTITION BY agent_id ORDER BY opened_at DESC,ticket_id DESC ROWS BETWEEN 1 PRECEDING AND CURRENT ROW),2) AS moving_csat FROM tickets WHERE csat IS NOT NULL')
add('ADV',8,'lending','Known versus certifiable borrower balance','loans payment_transactions charge_offs','borrower_id currency known_outstanding_cents unknown_payments certified_outstanding_cents','borrower_id currency',
 'By borrower x currency: principal minus latest posted signed logical principal minus approved charge-offs. Latest event_at then event_id, resolve before status. known_outstanding uses zero for unknown posted principal, but certified_outstanding is NULL if any selected posted principal is unknown. unknown_payments counts those logical transactions. No fees/FX. Defend semantic ownership, late-arrival repair and Finance reconciliation.',
 "WITH e AS (SELECT DISTINCT ON(transaction_id) * FROM payment_transactions ORDER BY transaction_id,event_at DESC,event_id DESC), p AS (SELECT loan_id,COALESCE(SUM(principal_cents),0) AS cents,COUNT(*) FILTER(WHERE principal_cents IS NULL) AS unknowns FROM e WHERE status='posted' GROUP BY loan_id), c AS (SELECT loan_id,SUM(cents) AS cents FROM charge_offs GROUP BY loan_id), b AS (SELECT l.borrower_id,l.currency,l.principal_cents-COALESCE(p.cents,0)-COALESCE(c.cents,0) AS cents,COALESCE(p.unknowns,0) AS unknowns FROM loans l LEFT JOIN p USING(loan_id) LEFT JOIN c USING(loan_id)) SELECT borrower_id,currency,SUM(cents) AS known_outstanding_cents,SUM(unknowns) AS unknown_payments,CASE WHEN SUM(unknowns)>0 THEN NULL ELSE SUM(cents) END AS certified_outstanding_cents FROM b GROUP BY borrower_id,currency",'sql.nulls.unknown_vs_zero sql.joins.preaggregation sql.performance.materialization',joins={'loans:payment_transactions':'1:M','loans:charge_offs':'1:M'})
add('ADV',9,'commerce','Recognition model at warehouse scale','orders refunds','month recognized_net_cents','month',
 'Use Finance policy: fulfilled order gross at fulfillment UTC month; posted refunds of fulfilled orders at refund UTC month. Preserve months with net zero. Produce first-date month and net cents. Production has 5B orders and 20B events; propose reusable recognition grain, incremental repair under late arrivals, semantic definition, reconciliation, and dialect portability. Local fixture timing is not a production benchmark.',
 "WITH e AS (SELECT fulfilled_at AS at,gross_cents AS cents FROM orders WHERE status='fulfilled' UNION ALL SELECT r.refund_at,-r.amount_cents FROM refunds r JOIN orders o USING(order_id) WHERE o.status='fulfilled' AND r.status='posted') SELECT DATE_TRUNC('month',at)::date AS month,SUM(cents) AS recognized_net_cents FROM e GROUP BY DATE_TRUNC('month',at)::date",'business.finance.recognition sql.performance.materialization sql.performance.portability sql.performance.plans',joins={'orders:refunds':'1:M'})
add('ADV',10,'insurance','Reserve certification design','policies claims','holder_id known_reserve_cents unknown_claims','holder_id',
 'Every policy holder: sum known reserves for currently open claims across all their policies; zero if none. Count unknown open reserves separately. Do not certify a total when unknown_claims>0. Review whether this report should own the reserve definition, snapshot semantics, reconciliation, and accepted-value tests.',
 "WITH c AS (SELECT policy_id,SUM(reserve_cents) AS cents,COUNT(*) FILTER(WHERE reserve_cents IS NULL) AS unknowns FROM claims WHERE status='open' GROUP BY policy_id) SELECT p.holder_id,SUM(COALESCE(c.cents,0)) AS known_reserve_cents,SUM(COALESCE(c.unknowns,0)) AS unknown_claims FROM policies p LEFT JOIN c USING(policy_id) GROUP BY p.holder_id",'sql.nulls.unknown_vs_zero sql.joins.preaggregation sql.performance.materialization',joins={'policies:claims':'1:M'})

# Additional independent situations close reasoning gaps rather than rename queries.
add('XFR',1,'lending','Payment presence is not a known amount','loans payments','loan_id payment_rows known_rows known_cents state','loan_id',
 'Every loan: count payment rows, count non-NULL principal_paid_cents, sum known signed cents with zero when none. state=no_records if no rows; unknown if any amount is NULL; zero if all known and sum=0; otherwise known. Priority is as listed. These are final recorded payments, distinct from webhook versions.',
 "SELECT l.loan_id,COUNT(p.payment_id) AS payment_rows,COUNT(p.principal_paid_cents) AS known_rows,COALESCE(SUM(p.principal_paid_cents),0) AS known_cents,CASE WHEN COUNT(p.payment_id)=0 THEN 'no_records' WHEN COUNT(p.principal_paid_cents)<COUNT(p.payment_id) THEN 'unknown' WHEN SUM(p.principal_paid_cents)=0 THEN 'zero' ELSE 'known' END AS state FROM loans l LEFT JOIN payments p USING(loan_id) GROUP BY l.loan_id",'sql.nulls.missing_row_vs_value sql.nulls.unknown_vs_zero sql.nulls.propagation',level=2,joins={'loans:payments':'1:M'})
add('XFR',2,'commerce','Visit session sequence','events','event_id session_no','event_id',
 'Keep each received event. Within customer order by event_at then event_id. First event starts session 1; a gap strictly greater than 30 minutes starts another. Exactly 30 minutes remains in session. Identical timestamps remain in the same session.',
 "WITH e AS (SELECT *,LAG(event_at) OVER(PARTITION BY customer_id ORDER BY event_at,event_id) AS prior FROM events), f AS (SELECT *,CASE WHEN prior IS NULL OR event_at>prior+INTERVAL '30 minutes' THEN 1 ELSE 0 END AS new FROM e) SELECT event_id,SUM(new) OVER(PARTITION BY customer_id ORDER BY event_at,event_id ROWS UNBOUNDED PRECEDING) AS session_no FROM f",'sql.analytics.sessionization sql.windows.lag_lead sql.windows.running_totals',level=3,window=True)
add('XFR',3,'commerce','Revenue compared with previous calendar month','orders','month cents prior_cents mom_rate','month',
 'Sum fulfilled gross at UTC fulfillment month. Output observed months only, with previous calendar month sum or NULL if absent. mom_rate=(current-prior)/prior rounded 2 decimals; absent/zero prior => NULL. A previous observed month may not be the previous calendar month.',
 "WITH m AS (SELECT DATE_TRUNC('month',fulfilled_at)::date AS month,SUM(gross_cents) AS cents FROM orders WHERE status='fulfilled' GROUP BY DATE_TRUNC('month',fulfilled_at)::date) SELECT m.month,m.cents,p.cents AS prior_cents,ROUND((m.cents-p.cents)::numeric/NULLIF(p.cents,0),2) AS mom_rate FROM m LEFT JOIN m p ON p.month=(m.month-INTERVAL '1 month')::date",'sql.dates.period_comparison sql.nulls.unknown_vs_zero sql.aggregation.ratios_zero',level=4,joins={'orders:orders':'M:M'})
add('XFR',4,'retail','Receipt identity normalization','products','sku normalized_code display_prefix','sku',
 'For every product: normalized_code = uppercase trimmed external_code with hyphens removed. Preserve leading zeros and NULL. display_prefix = first 3 characters of trimmed label concatenated with colon then sku. This normalization is for display only; explain why casting identifiers for a join can collapse distinct products.',
 "SELECT sku,REPLACE(UPPER(TRIM(external_code)),'-','') AS normalized_code,SUBSTRING(TRIM(label) FROM 1 FOR 3)||':'||sku AS display_prefix FROM products",'sql.strings.replace_substring sql.strings.normalized_identifiers sql.types.identifier_semantics',level=2)
add('XFR',5,'retail','Two price positions with ties','sales','store_id sku value_rank','store_id sku',
 'Sum signed receipt cents by store x SKU. Return all products whose RANK by cents descending within store is <=2, including ties and rank gaps. A tie at first rank can cause the next rank to exceed two.',
 'WITH g AS (SELECT store_id,sku,SUM(cents) AS cents FROM sales GROUP BY store_id,sku), r AS (SELECT store_id,sku,RANK() OVER(PARTITION BY store_id ORDER BY cents DESC) AS value_rank FROM g) SELECT * FROM r WHERE value_rank<=2','sql.windows.rank_dense_rank sql.windows.ranking_ties',level=3,window=True)
add('XFR',6,'subscription','Calendar week return after signup','subscribers activity','cohort_week subscribers retained','cohort_week',
 'Group subscribers by UTC signup calendar week starting Monday. Retained means any activity in the immediately following Monday–Monday week. Denominator includes never-active subscribers. All windows are observed in this synthetic extract.',
 "WITH s AS (SELECT *,DATE_TRUNC('week',joined_at)::date AS week FROM subscribers) SELECT s.week AS cohort_week,COUNT(*) AS subscribers,COUNT(*) FILTER(WHERE EXISTS(SELECT 1 FROM activity a WHERE a.subscriber_id=s.subscriber_id AND a.day>=s.week+7 AND a.day<s.week+14)) AS retained FROM s GROUP BY s.week",'sql.analytics.retention sql.analytics.cohorts sql.dates.iso_week',level=3,joins={'subscribers:activity':'1:M'})
add('XFR',7,'subscription','Calendar month return after signup','subscribers activity','cohort_month subscribers retained','cohort_month',
 'Group subscribers by UTC signup month. Retained means any activity in the immediately following calendar month. Include every subscriber in denominator. All windows are fully observed; this is calendar retention, not 30-day retention.',
 "WITH s AS (SELECT *,DATE_TRUNC('month',joined_at)::date AS month FROM subscribers) SELECT s.month AS cohort_month,COUNT(*) AS subscribers,COUNT(*) FILTER(WHERE EXISTS(SELECT 1 FROM activity a WHERE a.subscriber_id=s.subscriber_id AND a.day>=s.month+INTERVAL '1 month' AND a.day<s.month+INTERVAL '2 months')) AS retained FROM s GROUP BY s.month",'sql.analytics.retention sql.dates.buckets sql.analytics.cohort_denominators',level=4,joins={'subscribers:activity':'1:M'})
add('XFR',8,'payments','Nested product observations','attempts','attempt_id product units','attempt_id product',
 'metadata.items may be absent or an array of objects. Flatten present array objects into attempt x product rows; each product occurs at most once per attempt. Extract product as text and units as integer; fixtures units are valid bounded integer strings. Missing items => no rows. Preserve NULL units. Ignore top-level risk/channel.',
 "SELECT a.attempt_id,j.item->>'product' AS product,(j.item->>'units')::integer AS units FROM attempts a CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(COALESCE(a.metadata->'items','[]'::jsonb)) AS j(item)",'sql.semi_structured.json sql.semi_structured.unnesting sql.semi_structured.schema_variability',level=4)
add('XFR',9,'lending','Missed installments and supplied snapshot','scheduled_payments payments delinquencies','schedule_id unpaid_cents snapshot_dpd','schedule_id',
 'For installments due strictly before 2026-10-06 UTC, unpaid_cents=greatest(due_cents - sum known final payments explicitly allocated to that schedule_id, 0). Include paid installments with zero. Do not allocate unassigned payments. snapshot_dpd comes from the same-loan delinquency snapshot at as_of=2026-10-06, NULL when absent; it is an external reported value, not derived DPD. Unknown payment amounts contribute zero only to known-paid measure.',
 "WITH p AS (SELECT schedule_id,SUM(principal_paid_cents) AS cents FROM payments GROUP BY schedule_id) SELECT s.schedule_id,GREATEST(s.due_cents-COALESCE(p.cents,0),0) AS unpaid_cents,d.days_past_due AS snapshot_dpd FROM scheduled_payments s LEFT JOIN p USING(schedule_id) LEFT JOIN delinquencies d ON d.loan_id=s.loan_id AND d.as_of=DATE '2026-10-06' WHERE s.due_at<TIMESTAMPTZ '2026-10-06 00:00+00'",'sql.joins.preaggregation sql.nulls.missing_row_vs_value sql.dates.as_of',level=5,joins={'scheduled_payments:payments':'1:M','scheduled_payments:delinquencies':'M:1'})
add('XFR',10,'logistics','Second observed event','shipment_events','shipment_id second_event_id','shipment_id',
 'Return shipments with at least two received events, using the second event ordered by event_at then event_id ascending. Repeated deliveries remain distinct observations. Describe the partition and deterministic order.',
 'WITH e AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY shipment_id ORDER BY event_at,event_id) AS n FROM shipment_events) SELECT shipment_id,event_id AS second_event_id FROM e WHERE n=2','sql.windows.nth_event sql.windows.row_number',level=3,window=True)
add('XFR',11,'payments','Success percentages for stakeholder review','attempts','merchant_id success_pct','merchant_id',
 'For merchants observed in attempts, success_pct = 100 times known successes / known outcomes, rounded 2 decimals. Unknown success is excluded from denominator. No known outcomes => NULL. Explain why integer division and floating point money are different concerns.',
 'SELECT merchant_id,ROUND(100.0*SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(success),0),2) AS success_pct FROM attempts GROUP BY merchant_id','sql.aggregation.percentages sql.types.integer_division sql.types.precision',level=2,
 broken='SELECT merchant_id,ROUND(100*(SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(success),0)),2) AS success_pct FROM attempts GROUP BY merchant_id')
add('XFR',12,'banking','Join identity under changing contracts','accounts transactions','transaction_id owner_id','transaction_id',
 'Every posted transaction row must map to its account owner. Account_id and owner_id are distinct identities. Review a PR using a superficially plausible key; explain contract/version checks, one-to-many versus many-to-one direction, and how to preserve coverage at 150M accounts. Propose validation before accepting a source-key migration.',
 'SELECT t.transaction_id,a.owner_id FROM transactions t JOIN accounts a ON a.account_id=t.account_id','sql.joins.inner sql.joins.cardinality sql.performance.plans',level=6,joins={'transactions:accounts':'M:1'},
 broken='SELECT t.transaction_id,a.owner_id FROM transactions t JOIN accounts a ON a.owner_id=t.account_id')

add('XFR',13,'payments','Exact settlement money from export text','merchants attempts','merchant_id settled_amount','merchant_id',
 'Every merchant: sum metadata.settled_amount as exact decimal currency units (all USD), not amount_cents. Present strings are valid signed decimal amounts with 2 fractional digits. Missing/JSON null amounts are unknown and ignored by SUM; a merchant without any known amount gets NULL, not zero. Preserve cent precision even for very large settlements. Explain why casting through binary floating point can lose cents.',
 "SELECT m.merchant_id,SUM((a.metadata->>'settled_amount')::numeric(20,2)) AS settled_amount FROM merchants m LEFT JOIN attempts a USING(merchant_id) GROUP BY m.merchant_id",'sql.types.precision sql.types.explicit_casts sql.semi_structured.json sql.nulls.aggregate_nulls',level=3,joins={'merchants:attempts':'1:M'},
 broken="SELECT m.merchant_id,SUM((a.metadata->>'settled_amount')::double precision) AS settled_amount FROM merchants m LEFT JOIN attempts a USING(merchant_id) GROUP BY m.merchant_id")

add('XFR',14,'advertising','Calendar-week click comparison','ad_daily','campaign_id week clicks prior_clicks wow_rate','campaign_id week',
 'Sum clicks by campaign x UTC week starting Monday (week is that Monday date). Return observed weeks only. prior_clicks is the immediately preceding calendar week for that campaign, NULL if absent. wow_rate=(current-prior)/prior rounded to 2 decimals; missing/zero prior => NULL. A previous observed row may be several weeks earlier.',
 "WITH w AS (SELECT campaign_id,DATE_TRUNC('week',day)::date AS week,SUM(clicks) AS clicks FROM ad_daily GROUP BY campaign_id,DATE_TRUNC('week',day)::date) SELECT w.campaign_id,w.week,w.clicks,p.clicks AS prior_clicks,ROUND((w.clicks-p.clicks)::numeric/NULLIF(p.clicks,0),2) AS wow_rate FROM w LEFT JOIN w p ON p.campaign_id=w.campaign_id AND p.week=w.week-7",'sql.dates.period_comparison sql.dates.iso_week sql.aggregation.ratios_zero',level=4)
add('XFR',15,'retail','Comparable-month annual growth','sales','store_id month cents prior_year_cents yoy_rate','store_id month',
 'Sum signed receipt cents by store x observed UTC calendar month, represented by first date. Compare with the same calendar month exactly one year earlier for that store. Missing prior year => NULL, not zero. yoy_rate=(current-prior)/prior rounded to 2 decimals; missing/zero prior => NULL. Do not compare with the previous observed month.',
 "WITH m AS (SELECT store_id,DATE_TRUNC('month',sold_at)::date AS month,SUM(cents) AS cents FROM sales GROUP BY store_id,DATE_TRUNC('month',sold_at)::date) SELECT m.store_id,m.month,m.cents,p.cents AS prior_year_cents,ROUND((m.cents-p.cents)::numeric/NULLIF(p.cents,0),2) AS yoy_rate FROM m LEFT JOIN m p ON p.store_id=m.store_id AND p.month=(m.month-INTERVAL '1 year')::date",'sql.dates.period_comparison sql.dates.buckets sql.aggregation.ratios_zero',level=4)
add('XFR',16,'commerce','Eligible checkout with optional cart','customers events','customer_id eligible converted','customer_id',
 'Every customer: eligible=1 if any view occurred at or after their signup_at, otherwise 0. converted=1 if an eligible view has a strictly later purchase within 24 elapsed hours inclusive. Cart is optional and never required. Repeated event deliveries must not create multiple output rows or conversion counts. Ignore purchases before the eligible view, even if a cart exists later.',
 "SELECT u.customer_id,CASE WHEN EXISTS(SELECT 1 FROM events v WHERE v.customer_id=u.customer_id AND v.event_type='view' AND v.event_at>=u.signup_at) THEN 1 ELSE 0 END AS eligible,CASE WHEN EXISTS(SELECT 1 FROM events v JOIN events p ON p.customer_id=v.customer_id AND p.event_type='purchase' AND p.event_at>v.event_at AND p.event_at<=v.event_at+INTERVAL '24 hours' WHERE v.customer_id=u.customer_id AND v.event_type='view' AND v.event_at>=u.signup_at) THEN 1 ELSE 0 END AS converted FROM customers u",'sql.analytics.funnels sql.analytics.ordered_funnels sql.analytics.cohort_denominators sql.ctes.exists',level=3,joins={'customers:events':'1:M','events:events':'M:M'})

# Mutants are intentionally runnable where possible, and validated to fail.
by_id={s['id']:s for s in SPECS}
by_id['SQL-AGG-009']['broken']="SELECT store_id,ROUND(AVG(cents),2) AS avg_active_day_cents FROM sales GROUP BY store_id"
by_id['SQL-WIN-005']['broken']="SELECT event_id,LEAD(event_at) OVER(ORDER BY event_at,event_id) AS next_event_at FROM shipment_events"
by_id['SQL-WIN-006']['broken']="SELECT invoice_id,ROUND(AVG(cents) OVER(PARTITION BY subscriber_id ORDER BY invoiced_at,invoice_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),2) AS moving_cents FROM invoices WHERE status='paid'"
by_id['SQL-DED-007']['broken']=by_id['SQL-DED-007']['sql'].replace("WHERE received_at<TIMESTAMPTZ '2026-10-04 00:00+00' ","")
by_id['SQL-JOIN-007']['broken']="SELECT a.payment_id,COALESCE(SUM(c.cents),0)-COALESCE(SUM(d.cents) FILTER(WHERE d.status='open'),0) AS net_exposure_cents FROM attempts a LEFT JOIN captures c USING(payment_id) LEFT JOIN disputes d USING(payment_id) GROUP BY a.payment_id"
by_id['SQL-WIN-003']['broken']=by_id['SQL-WIN-003']['sql'].replace('cents DESC,seller_id','cents DESC,seller_id DESC')
by_id['SQL-JOIN-011']['broken']=by_id['SQL-ADV-003']['broken']
by_id['SQL-ADV-005']['broken']="SELECT m.merchant_id,ROUND(SUM(d.cents) FILTER(WHERE d.status='open')::numeric/NULLIF(SUM(c.cents),0),2) AS dispute_rate FROM merchants m LEFT JOIN attempts a USING(merchant_id) LEFT JOIN captures c USING(payment_id,merchant_id) LEFT JOIN disputes d USING(payment_id) GROUP BY m.merchant_id"
by_id['SQL-ADV-006']['broken']=by_id['SQL-ADV-006']['sql'].replace("sold_at<TIMESTAMPTZ '2026-11-01 00:00+00'","sold_at<TIMESTAMPTZ '2026-10-03 00:00+00'")
by_id['SQL-ADV-008']['broken']=by_id['SQL-ADV-008']['sql'].replace('CASE WHEN SUM(unknowns)>0 THEN NULL ELSE SUM(cents) END','SUM(cents)')
by_id['SQL-ADV-009']['broken']=by_id['SQL-ADV-009']['sql'].replace('SELECT r.refund_at,-r.amount_cents','SELECT o.fulfilled_at,-r.amount_cents')
by_id['SQL-ADV-010']['broken']=by_id['SQL-ADV-010']['sql'].replace("WHERE status='open' ",'')
by_id['SQL-FND-001']['tags']+=['sql.filtering.select_aliases']
by_id['SQL-DED-006']['tags']+=['sql.filtering.distinct']
by_id['SQL-CTE-008']['tags']+=['sql.types.explicit_casts']
by_id['SQL-JOIN-009']['sql']="SELECT p.policy_id,COUNT(c.claim_id) AS open_claims FROM claims c RIGHT JOIN policies p ON c.policy_id=p.policy_id AND c.status='open' GROUP BY p.policy_id"
by_id['SQL-JOIN-009']['tags']+=['sql.joins.right']
by_id['SQL-JOIN-008']['tags']+=['sql.joins.one_to_one']
by_id['SQL-JOIN-008']['requirement']+=' Explain why the two sides become 1:1 after statement pre-aggregation.'
by_id['SQL-CTE-001']['sql']="WITH active AS (SELECT * FROM subscription_versions WHERE valid_from<=TIMESTAMPTZ '2026-10-03 00:00+00' AND (valid_to IS NULL OR TIMESTAMPTZ '2026-10-03 00:00+00'<valid_to)) SELECT a.account_id,COALESCE(SUM(v.monthly_cents) FILTER(WHERE v.status='active'),0) AS mrr_cents FROM accounts a LEFT JOIN subscriptions s USING(account_id) LEFT JOIN active v USING(subscription_id) GROUP BY a.account_id"
by_id['SQL-CTE-001']['tags']+=['sql.ctes.scope']

RECALL={
 'sql.windows.row_number':('Does ROW_NUMBER alone remove duplicate rows?',['no']),
 'sql.windows.frames':('Does a window ORDER BY guarantee the frame covers the whole partition?',['no']),
 'sql.windows.partition_order':('Must tied business timestamps have an explicit ordering rule when one survivor is required?',['yes']),
 'sql.deduplication.latest_version':('Should a current-status filter run before or after version resolution?',['after','after version resolution']),
 'sql.deduplication.deterministic_ties':('Do equal timestamps alone identify a deterministic survivor?',['no']),
 'sql.joins.fanout':('Two child rows join three independent child rows on the same parent. How many matched rows?',[6,'6']),
 'sql.joins.left':('Can a WHERE equality on a nullable right-side field remove unmatched LEFT JOIN rows?',['yes']),
 'sql.nulls.unknown_vs_zero':('Does an unknown amount necessarily mean zero?',['no']),
 'sql.nulls.missing_row_vs_value':('Are no payment rows and a payment row with NULL amount the same observation?',['no']),
 'sql.aggregation.weighted_averages':('Is averaging daily ratios always equal to the ratio of summed numerators and denominators?',['no']),
 'sql.dates.half_open':('Does a half-open interval include its end boundary?',['no']),
 'sql.performance.materialization':('Does introducing a CTE guarantee materialization or faster execution?',['no']),
 'sql.analytics.cohort_denominators':('Should never-active eligible cohort members stay in the retention denominator?',['yes']),
}

MANUAL=['business_interpretation','query_clarity','performance_awareness']
REVIEW=['correctness','grain','join_safety','readability','maintainability','edge_cases','performance','business_semantics','tests_needed']
CASES=[('clean',1),('adversarial',1),('adversarial',2),('recall',3)]

def build():
    problems=[]
    for s in SPECS:
        domain=DOMAINS[s['domain']];data=fixture(s['domain'],'clean');lv=s['level']
        tags=s['tags']
        # Reasoning tasks assess explanation independently from executable output.
        criteria=REVIEW if s['area']=='ADV' or s['broken'] else MANUAL
        modes=['LEARN','PRACTICE','INTERVIEW']
        if s['broken']:modes+=['DEBUG','REVIEW']
        elif s['area']=='ADV':modes+=['REVIEW']
        if lv>=4:modes+=['PERFORMANCE']
        if s['area']=='ADV' or lv>=5:modes+=['SYSTEM_DESIGN']
        requirements=[s['requirement'],'Return exactly these columns: '+', '.join(s['output'])+'.']
        prompts=['What does one input row represent?','What should one output row represent?']
        if lv>=3:prompts+=['Who consumes this result and what decision does it support?','What time window, exclusions, and NULL meanings apply?']
        if s['joins']:prompts+=['For each listed join: left table grain, right table grain, relationship (1:1 / 1:M / M:1 / M:M), expected output grain.']
        if s['window']:prompts+=['What defines the partition, order, and rows visible to the calculation?']
        duplicate=any(t.startswith('sql.deduplication') and t!='sql.deduplication.deterministic_ties' for t in tags)
        if duplicate:prompts+=['What makes two records represent the same logical entity?']
        if s['broken']:prompts.insert(0,'What is wrong? Diagnose before fixing the query.')
        artifacts={'provenance':'Original AE Lab scenario; authored requirements, fixtures and independent Python oracle.',
          'diagram':'flowchart TD\n source[Source rows] --> query[Candidate query]\n query --> quality[Quality checks]\n quality --> consumer[Business consumer]',
          'dialect':'PostgreSQL 17','response_type':'sql','join_pairs':list(s['joins']),
          'window_reasoning':s['window'],'duplicate_reasoning':duplicate,
          'manual_criteria':criteria}
        if s['broken']:artifacts['broken_sql']=s['broken']
        if s['predict']:artifacts['prediction_sql']=s['predict']
        if s['stage']:artifacts['next_stage']=s['stage']
        if lv>=4:artifacts['scale_context']={'source_rows':'5B facts; 150M entities; 20B events (hypothetical production scenario)',
          'questions':['What is scanned, filtered, joined, aggregated, sorted or windowed?','Which physical partitioning could allow pruning?','Would pre-aggregation or a reusable model help?','How will you verify the actual warehouse plan?'],
          'caveat':'Local fixture EXPLAIN is real; production cardinalities and costs are hypothetical.'}
        p={'contract_version':'ae-problem-v1','problem_id':s['id'],'title':domain.title.split(' / ')[-1]+': '+s['title'],
          'neutral_title':domain.title.split(' / ')[-1]+': '+s['title'],'domain':s['domain'],
          'business_context':domain.title.split(' / ')[-1]+' needs '+s['title'].lower()+' for its operational reporting consumer.',
          'difficulty':{'level':f'L{lv}','rationale':s['requirement'] if lv>=5 else 'Business population, row meaning and edge cases determine difficulty.',
           'dimensions':{'code_complexity':min(3,max(0,lv-1)),'business_semantics':min(3,lv),'hidden_edge_cases':min(3,lv),
                         'scale':2 if lv>=4 else 0,'requirement_ambiguity':2 if lv>=5 else 0}},
          'kind':'debug' if s['broken'] else 'sql','skills_tested':tags,'mastery_tags':tags,
          'tables':[domain.table(t).public() for t in s['inputs']],
          'sample_rows':{t:data[t][:8] for t in s['inputs']},'requirements':requirements,
          'expected_output_grain':'one row per '+ ' x '.join(s['key']),
          'hidden_edge_cases':['Stated populations under missing activity, NULLs, zero/signed values, tied timestamps, changed amounts, boundaries and retries as applicable.'],
          'learner_prompt':{'prediction':'What rows does the displayed query return? Predict the sample output before SQL.' if s['predict'] else 'What should one row of your final result represent, and how would you approach the problem?',
            'requirements':prompts,'proposal':'Explain your plan in 2–4 sentences before writing SQL.','answer_fields':['sql','inputs','output_key','requirements','proposal']},
          'learner_answer':None,'evaluation_rules':{'adapter':'postgresql','sql_challenge_id':s['id'],'required_columns':s['output'],
            'criteria':['result_correctness','grain_correctness','edge_case_robustness']+criteria,'manual_criteria':criteria,
            'output_key':s['key'],'joins':s['joins'],'window_reasoning':s['window'],'ordered':s['id']=='SQL-FND-010'},
          'hidden_tests':[{'fixture':v,'seed':seed,'fixture_sha256':fingerprint(fixture(s['domain'],v,seed)),
            'oracle_sha256':fingerprint(expected_bank(s['id'],fixture(s['domain'],v,seed)))} for v,seed in CASES],
          'followups':['How could this calculation silently become wrong, and which independent check would catch it?'],
          'hints':['Read the consumer contract and define one output row.','Track one entity through the stated filters and source row meanings.',
            'Compare the first differing entity against the stated time, identity and missing-value rules.',
            'Calculate each measure at its own entity grain; combine only compatible populations, preserving the explicit business meaning.'],
          'solution':s['sql'],'transfer_from':s['transfer'],'modes':modes,'artifacts':artifacts,
          'recall':[{'prompt':'What does the output grain describe?','accepted':['what one row represents','one row meaning','row meaning'],
                    'concepts':['sql.grain.output_keys']}]}
        # Grain evidence is assessed on every query, including recall.
        if 'sql.grain.output_keys' not in tags:tags.append('sql.grain.output_keys')
        for tag in tags:
            if tag in RECALL and len(p['recall'])<3:
                prompt,accepted=RECALL[tag];p['recall'].append({'prompt':prompt,'accepted':accepted,'concepts':[tag]})
        if lv>=5:p['followups']=['Should this metric live in a reusable model or semantic definition? How would late arrivals change it, and how would you reconcile against Finance?']
        problems.append(p)
    return problems

if __name__=='__main__':
    path=ROOT/'curriculum/sql-bank.json'
    path.write_text(json.dumps(build(),indent=2,default=str)+'\n')
    print(f'{len(SPECS)} original SQL definitions written to {path}')
