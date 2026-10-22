"""Author 60 business reasoning cases in the existing ae-problem-v1 contract."""
import json,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.reasoning_fixtures import fixture,facts,schemas,VARIANTS
from lab.sql_lab.contracts import fingerprint

AREAS={
 'translate':('Business Problem Translation',[],['decision','clarification','acceptance']),
 'grain':('Grain & Cardinality',['translate'],['row_meaning','relationships','output_grain']),
 'entities':('Entity & Event Reasoning',['grain'],['identity','events','population']),
 'metrics':('Metric Definitions',['translate','entities'],['numerator_denominator','eligibility','contract']),
 'fanout':('Join Fanout & Aggregation',['grain','metrics'],['multiplicity','allocation','preaggregation']),
 'temporal':('Temporal Reasoning',['entities'],['business_time','availability','boundaries']),
 'integrity':('Data Integrity',['entities'],['missing_unknown','duplicates','source_truth']),
 'dimensions':('Business Dimensions',['grain','temporal'],['historical_attributes','classification','segments']),
 'validation':('Analytical Validation',['metrics','integrity'],['invariants','reconciliation','anomalies']),
 'communication':('Stakeholder Communication',['translate','validation'],['assumptions','uncertainty','recommendations'])}
NAMES={'iot':'Mile Lantern connected-vehicle SaaS','commerce':'Parcel Pine e-commerce and retail','saas':'Orbit Desk B2B SaaS',
 'payments':'KitePay payments','logistics':'North Parcel logistics','marketing':'Signal Grove marketing',
 'workforce':'Cedar Works workforce','ai':'Beacon Agent AI product'}
SPECS=[]
def add(area,n,domain,title,request,inputs,checks,reason,pitfall,*,level=3,metric=False,alternative=None,diagnose=False):
 SPECS.append(dict(id=f'REASON-{area.upper()}-{n:03d}',area=area,domain=domain,title=title,request=request,inputs=inputs.split(),
  checks=checks,reason=reason,pitfall=pitfall,level=level,metric=metric,alternative=alternative,diagnose=diagnose))
# Each check is (neutral field label, question, fixture calculation or literal).
def c(label,prompt,calc):return (label,prompt,calc)

add('translate',1,'iot','The board asks for fleet health','The COO asks: “How healthy was our connected fleet this month? I need one number for the board.”','devices heartbeats intervals',
 [c('entity_count','How many commissioned devices are represented?', 'devices'),c('unknown_duration','How many monitored minutes have unknown uptime?', 'unknown_minutes')],
 'Health could mean coverage, heartbeat freshness, healthy devices or duration-weighted uptime. Establish the board decision, population and observation rules before choosing a number.',
 'Missing observation is not evidence of an outage; healthy-event counts are not duration-weighted uptime.',level=3,metric=True,
 alternative={'known_observation':'Report uptime over known intervals and disclose coverage.','strict_contract':'Withhold a certified total if any monitored interval has unknown uptime.'})
add('translate',2,'marketing','Which campaigns produced qualified leads?','The VP of Marketing asks: “Which campaigns produced the most qualified leads?”','campaigns leads lead_states lead_credit',
 [c('current_population','How many distinct leads are qualified in the final observed state?','qualified'),c('historical_population','How many were qualified strictly before October 3 UTC?','historical_qualified')],
 'Produced needs an attribution definition; qualified needs a status clock. State both, include eligible zero-result campaigns and reconcile allocated credit to eligible leads.',
 'Counting campaign memberships as distinct leads can exceed the eligible population.',level=3,metric=True,
 alternative={'current':'Use final observed qualification status.','historical':'Use status strictly before October 3 UTC.'})
add('translate',3,'saas','Revenue operations and Finance disagree','Revenue Operations asks: “Can you give us recurring revenue? Finance sent a different number.”','accounts subscriptions subscription_versions invoices invoice_events',
 [c('contract_value','What is active contract MRR at October 3 00:00 UTC, in cents?','mrr'),c('paid_population_value','What is the amount of invoices whose final observed event is paid, in cents?','invoice_paid')],
 'Contract MRR and paid invoice amounts answer different questions and use different clocks. Identify the consumer and label both definitions before reconciling.',
 'Treating a collected invoice total as a monthly recurring run rate mixes stock and flow.',level=3,metric=True)
add('translate',4,'commerce','A growth conversion request','Growth asks: “What percentage of our customers converted?”','customers orders',
 [c('denominator','How many customers are in the displayed registered population?','customers'),c('numerator','How many distinct customers have at least one fulfilled order?','buyers'),c('sample_rate','Under registered-customer eligibility, what is the ratio, rounded to 2 decimals?','conversion')],
 'Define conversion event, eligible population, observation window and maturity. A buyer can place several orders and still contributes once to this customer-level ratio.',
 'Dividing fulfilled orders by customers can exceed a customer conversion rate.',level=2,metric=True)
add('translate',5,'workforce','An ambiguous hiring plan baseline','The People team asks: “How many people do we have on October 3? Hiring plans depend on this.”','people employments assignments',
 [c('staff_people','Distinct people with active employee relationships at October 3 UTC?','headcount'),c('relationships','Active employment relationships of any kind at that instant?','active_relationships')],
 'Confirm people versus employment relationships, employee versus contractor scope, effective boundary and headcount versus FTE.',
 'A person can have multiple assignments or relationships; neither row count is automatically headcount.',level=2,metric=True)
add('translate',6,'ai','Does the agent succeed?','The product lead asks: “What is our agent success rate? Retries should not make us look worse.”','tasks attempts users',
 [c('eligible_population','How many tasks are marked eligible?','eligible_tasks'),c('final_successes','Eligible tasks whose final attempt succeeded and was approved?','final_success'),c('any_successes','Eligible tasks with any succeeded, approved attempt?','any_success')],
 'Agree on task versus attempt, evaluation maturity, approval, and whether recovery or final state is the product promise. Both policies can be reported if labeled.',
 'A status of succeeded alone does not establish approved task success; retries change the attempt denominator.',level=3,metric=True,
 alternative={'final':'Final observed attempt must succeed and be approved.','any':'At least one observed attempt must succeed and be approved.'})

add('grain',1,'commerce','Order headers meet line detail','Finance wants an order-level reconciliation after an item table is attached.','orders items',
 [c('header_key','Which columns identify one order source row?','order_key'),c('detail_key','Which columns identify one item source row?','item_key'),c('joined_rows','How many rows does a LEFT JOIN from orders to items produce?','joined_rows')],
 'An order header becomes one joined row per matching item; an order with no item still produces one row in a left join.',
 'The order amount belongs to the header and repeats on every detail row.',level=1)
add('grain',2,'marketing','A lead can have several contacts','An analyst wants a lead report enriched with all ad touches for the same user.','leads touches',
 [c('lead_identity','Which columns identify a lead?','lead_key'),c('joined_rows','How many rows are produced by a LEFT JOIN of leads to touches on user_id?','lead_touch_rows')],
 'Lead rows and user-touch rows have different grains. Count the matched rows before deciding whether a lead measure remains additive.',
 'Distinct campaign names do not restore lead grain if one user touched the same campaign repeatedly.',level=2)
add('grain',3,'iot','A retry is still a received row','The ingestion team says every heartbeat delivery has a new delivery_id. Product wants actual device events.','heartbeats',
 [c('received_key','Which columns identify one received delivery?','delivery_key'),c('logical_key','Which columns identify one logical event under this producer contract?','logical_key'),c('logical_count','How many logical events are displayed?','logical_events')],
 'The fixture producer defines event_id as business identity and delivery_id as transport identity. Retries add deliveries without adding logical events.',
 'A unique delivery key proves receipt uniqueness, not uniqueness of business events.',level=1)
add('grain',4,'workforce','People, jobs and allocations','A staffing dashboard counts assignment rows and labels the result employees.','people employments assignments',
 [c('person_key','Which column identifies one person?','person_key'),c('assignment_key','Which column identifies one allocation record?','assignment_key'),c('headcount','Distinct active employee people at October 3 UTC?','headcount')],
 'A person can hold multiple employment relationships, and a relationship can be split among teams. Declare which entity the consumer needs.',
 'COUNT(assignments) measures allocations and can inflate people.',level=2,diagnose=True)
add('grain',5,'saas','Account report over subscription contracts','Customer Success needs one row per account while Billing supplies subscription versions.','accounts subscriptions subscription_versions',
 [c('account_key','Which columns identify the intended account output entity?','account_key'),c('subscription_key','Which columns identify one subscription?','subscription_key'),c('relationship','What is the account-to-subscription relationship?','relationship')],
 'First identify account, subscription and effective-version grains. Aggregate or select effective subscriptions before returning to account grain.',
 'A version key is not a subscription key, and a subscription key is not an account key.',level=2)
add('grain',6,'ai','Tool activity changes the denominator','Engineering proposes counting tool calls as the denominator for agent task success.','tasks attempts tool_calls',
 [c('task_key','Which columns identify a logical task?','task_key'),c('attempt_key','Which columns identify an execution attempt?','attempt_key'),c('call_count','How many tool-call records are displayed?','calls')],
 'One task can have retries, and one attempt can have several tool calls. These are nested grains, not interchangeable units of success.',
 'More tool calls can change an operational cost metric without changing task completion.',level=2)

add('entities',1,'payments','Authorization retries versus purchases','Payments Operations asks whether increased authorization volume means more customer payments.','attempts',
 [c('attempts','Received authorization attempts?','attempts'),c('payments','Distinct logical payment identities?','payments'),c('identity','Which columns define the logical payment population?','payment_key')],
 'Payment identity groups authorization retries. Attempt-level reliability and payment-level completion need separate denominators.',
 'Counting successful attempt rows does not prove the same number of successful payments.',level=2)
add('entities',2,'logistics','Delivered once versus currently delivered','Operations wants to distinguish shipments that ever reached a destination from shipments whose final state is delivered.','shipments shipment_events',
 [c('ever_delivered','Shipments with at least one delivered business event?','delivered'),c('currently_delivered','Shipments whose final observed business state is delivered?','current_delivered')],
 'A later return changes current state without erasing the earlier delivery event. Ask which entity-state question the report supports.',
 'Filtering delivered events before selecting current state can conceal later returns.',level=3)
add('entities',3,'ai','Users and paying accounts','Product reports active users; Sales reports active accounts. The counts disagree.','users tasks',
 [c('active_users','Distinct users with eligible task creation activity?','active_users'),c('active_accounts','Distinct accounts containing those users?','active_accounts')],
 'Users and accounts have different identities and a many-to-one relationship. The discrepancy can be legitimate rather than a data defect.',
 'Renaming account activity as MAU hides the unit being measured.',level=2)
add('entities',4,'iot','Trips do not equal connected devices','The fleet team wants to know whether trip growth means fleet adoption increased.','devices trips',
 [c('trips','How many trip records are present?','trips'),c('trip_devices','How many distinct devices have trips?','active_trip_devices'),c('registered_devices','How many devices are commissioned in this extract?','devices')],
 'Trips measure usage events; devices measure adopted entities; registered devices define a broader population. Report the relationship explicitly.',
 'A heavy-use device can increase trips without increasing adoption.',level=2)
add('entities',5,'workforce','A returning worker has another relationship','People Operations asks whether each active job relationship represents a different person.','people employments',
 [c('relationships','Active relationships of all kinds on October 3?','active_relationships'),c('people','Distinct people behind those active relationships?','all_worker_people')],
 'Person identity survives changes in employment relationship. Establish whether the report counts people, jobs or employee-only headcount.',
 'Distinct employment_id can still double-count a person.',level=3)
add('entities',6,'commerce','Repeat buyers and demand','Merchandising sees several orders per customer and wants both order demand and buyer reach.','orders',
 [c('orders','Number of fulfilled orders?','fulfilled'),c('buyers','Distinct buyers of fulfilled orders?','buyers')],
 'Both measures are useful but have different additive behavior. Buyer counts cannot be added across overlapping product or time segments without distinct identity.',
 'Adding distinct buyers from separate groups can count a cross-group buyer twice.',level=2)

add('metrics',1,'ai','Monthly active users for an AI product','Product defines monthly activity as creating at least one eligible task in this October extract; internal-only tasks are ineligible.','users tasks',
 [c('mau','Distinct active eligible users?','active_users'),c('accounts','Distinct active eligible accounts, reported separately?','active_accounts')],
 'MAU counts distinct users, not attempts or accounts. Define the activity event, calendar timezone, exclusions and the extract completeness cutoff.',
 'Counting every task inflates active users when a user creates several tasks.',level=3,metric=True)
add('metrics',2,'saas','Customer churn for the opening book','Finance wants customer churn among accounts with positive opening MRR. Zero closing MRR is churn; unknown closing MRR is unresolved.','revenue_movements',
 [c('opening_accounts','How many accounts have positive opening MRR?','eligible_accounts'),c('churned','How many have known zero closing MRR?','churned'),c('observed_rate','Known churned accounts divided by the full opening population, rounded to 2 decimals?','churn')],
 'The denominator is the opening customer book. Report unknown closing states as unresolved; a known observed churn fraction is not a fully certified churn estimate.',
 'New customers do not belong in the opening denominator, and NULL closing MRR is not a cancellation.',level=3,metric=True)
add('metrics',3,'saas','Revenue retention without new-logo growth','The CFO asks for GRR and NRR on the positive opening-MRR customer book. Expansion belongs only in NRR; new logos belong in neither. Unknown closing MRR blocks certification.','revenue_movements',
 [c('opening','Opening MRR cents?','opening'),c('nrr','Certified NRR as a ratio rounded to 2 decimals, or null if unresolved?','nrr'),c('grr','Certified GRR as a ratio rounded to 2 decimals, or null if unresolved?','grr')],
 'NRR includes expansion within the opening book; GRR caps each retained account at its opening value. Separate new revenue and unresolved source observations.',
 'Comparing total company closing revenue with opening revenue confounds new-logo acquisition and retention.',level=4,metric=True)
add('metrics',4,'commerce','Average order value after status changes','Finance defines AOV as fulfilled order-header gross cents divided by fulfilled order count. Return signed adjustments through a separately labeled net metric.','orders refunds',
 [c('numerator','Fulfilled order gross cents?','gross'),c('denominator','Fulfilled order count?','fulfilled'),c('aov','AOV in cents rounded to 2 decimals?','aov')],
 'The numerator and denominator must cover the same order population. Refund treatment and canceled/open exclusions are definition choices, not formatting choices.',
 'An item-weighted average order amount overweights orders with many lines.',level=3,metric=True)
add('metrics',5,'logistics','An on-time delivery denominator','Operations asks for on-time rate based on the first delivered event and each shipment promise. Returns do not erase first delivery.','shipments shipment_events',
 [c('on_time','Shipments first delivered by their promised time?','ontime'),c('delivered','Shipments with a first delivered event?','delivered')],
 'Delivered-only and all-promised-shipment denominators can answer different questions. Label the population and separately expose missing delivery evidence.',
 'Silently removing undelivered shipments can make service performance appear stronger.',level=3,metric=True,
 alternative={'delivered':'Divide on-time first deliveries by shipments with a delivered event.','all_promises':'Divide on-time first deliveries by all displayed shipment promises.'})
add('metrics',6,'iot','Duration-weighted device uptime','Customer Success needs an uptime measure across devices with different observed durations.','devices intervals',
 [c('known_up','Known uptime minutes?','known_up_minutes'),c('known_duration','Monitored minutes whose uptime is known?','known_minutes'),c('coverage','Known monitored minutes / all monitored minutes, rounded to 2 decimals?','coverage')],
 'Weight by duration. Unknown observed duration affects certification and coverage; devices without intervals are a separate population gap.',
 'Averaging device percentages can misweight different durations; replacing unknown uptime with zero invents downtime.',level=3,metric=True,
 alternative={'known_observation':'Report known-duration uptime and separate coverage.','strict_contract':'Withhold a certified fleet uptime if any monitored duration has unknown uptime.'})

add('fanout',1,'commerce','A header measure after item enrichment','A proposed report sums order-header gross after joining fulfilled orders to items.','orders items',
 [c('true_total','Correct fulfilled header gross cents?','gross'),c('candidate_total','What would the item-enriched header sum return?','multiplied_gross')],
 'The join repeats header measures. Either aggregate from the authoritative header grain or use correctly defined line measures and reconcile them.',
 'SUM(DISTINCT amount) drops different orders that happen to have equal amounts.',level=3,diagnose=True)
add('fanout',2,'marketing','Attribution credits and lead counts','Marketing proposes counting lead-credit rows as the number of qualified leads under final observed state.','leads lead_states lead_credit',
 [c('leads','Distinct qualified leads?','qualified'),c('memberships','Qualified lead-credit rows?','qualified_credit_rows'),c('credit','Sum of qualified attribution weights?','allocated')],
 'A lead may contribute several memberships but only one total allocated unit when weights reconcile. Expose invalid or missing allocations.',
 'A bridge row count can double-count a multi-campaign lead.',level=4,diagnose=True)
add('fanout',3,'iot','Fleet duration meets driving events','An engineer joins devices to interval rows and trips before summing availability.','devices intervals trips',
 [c('rows','How many rows does the pair of LEFT JOINs create?','joined_rows'),c('minutes','Correct known monitored minutes before trip enrichment?','known_minutes')],
 'Intervals and trips are independent many sides of a device. Their combinations weight interval measures by trip count.',
 'Pre-aggregate each independently or avoid an irrelevant enrichment; device DISTINCT does not repair a repeated measure.',level=4,diagnose=True)
add('fanout',4,'workforce','Hours repeated across team allocations','A staffing PR sums time-entry hours after joining to every effective assignment for the same employment on the work date.','assignments time_entries',
 [c('correct_hours','Actual time-entry hours?','hours'),c('candidate_hours','Hours summed after that join?','multiplied_hours')],
 'Time entries belong to an employment/day and allocation rows split a different measure. Decide whether to allocate hours or report them before joining team detail.',
 'Copying full hours into every team silently inflates total work.',level=4,diagnose=True)
add('fanout',5,'ai','Successes after attaching tool costs','The proposed task report counts succeeded approved attempt rows after joining attempts to tool calls.','tasks attempts tool_calls',
 [c('candidate_successes','How many succeeded approved rows does that enrichment produce?','multiplied_success'),c('final_tasks','Correct eligible final-attempt task successes?','final_success'),c('cost','Actual tool cost cents?','cost')],
 'Cost is additive at call grain; task success must be resolved at task grain. Pre-aggregate costs without changing the success population.',
 'A tool-intensive successful task can contribute several apparent successes.',level=4,diagnose=True)
add('fanout',6,'payments','Captures attached to every authorization','Finance receives a report summing capture cents after joining captures to all authorization attempts by payment_id.','attempts captures',
 [c('captures','Correct settled capture cents?','capture_total'),c('candidate','Capture cents after attachment to every attempt?','repeated_capture_total')],
 'Logical payment identity can have several attempts and captures. Resolve the payment population, then independently aggregate captures.',
 'Deduplicating by amount instead of capture identity loses legitimate equal-value captures.',level=3,diagnose=True)

add('temporal',1,'iot','What the report could know at close','The October 2 activity report closes at October 3 00:00 UTC. Operations distinguishes retrospective event truth from data known at close.','heartbeats',
 [c('event_truth','Distinct logical events with event_at strictly before close, using all arrivals?','pre_close_events'),c('known_at_close','Distinct such events also received strictly before close?','known_at_close')],
 'Event time places activity in its business period; receipt time limits what could have been known. Restatement policy determines later revisions.',
 'Filtering only event time lets a historical operational report use information that arrived later.',level=4)
add('temporal',2,'marketing','Qualification at campaign close','A campaign report closes strictly before October 3 UTC; Sales wants the latest observed qualification status as another report.','leads lead_states',
 [c('at_close','Qualified leads under the historical boundary?','historical_qualified'),c('current','Qualified leads under final observed state?','qualified')],
 'Historical qualification and current qualification are different governed questions even when their totals happen to agree.',
 'Matching totals can hide a change in which individual leads qualify.',level=4)
add('temporal',3,'saas','The midnight contract boundary','The revenue report is exactly at October 3 00:00 UTC. Contract versions use start-inclusive, end-exclusive validity; null end means unbounded.','accounts subscriptions subscription_versions',
 [c('snapshot','Active account MRR cents at that instant?','mrr'),c('open_versions','How many source versions have an unbounded end?','null_end_versions')],
 'A shared boundary must select one valid version, not both. A reporting instant is not a period sum.',
 'BETWEEN includes both ends and can match old and new versions at midnight.',level=3)
add('temporal',4,'logistics','A late courier upload','Operations needs a corrected first-delivery report and an explanation of arrivals after business events.','shipments shipment_events',
 [c('late_rows','How many matched event deliveries have received_at after event_at?','late_arrivals'),c('delivered','How many shipments have a delivered event in the full observed extract?','delivered')],
 'Retain both clocks, identify affected reporting periods and distinguish a correction from an on-time original publication.',
 'Treating ingestion date as delivery date moves work into the wrong operational day.',level=3)
add('temporal',5,'workforce','A worker exits when another begins','People Operations reports an employee snapshot at October 3 00:00 UTC. Employment intervals are [starts_at, ends_at).','people employments',
 [c('before','Employee relationships active at October 2?','before_boundary'),c('leavers','Employee relationships ending exactly at October 3?','employee_leavers'),c('at_boundary','Distinct employee people active at October 3?','headcount')],
 'An ending relationship is not active at its exclusive end. A new relationship starts at its inclusive start.',
 'Inclusive ends can make headcount briefly contain both the departing and arriving worker.',level=3)
add('temporal',6,'commerce','Ordered conversion within a business window','Product requires view then cart then purchase, strictly ordered in event time, with purchase no later than 24 hours after the view.','customers events',
 [c('eligible','Customers with any view?','funnel_eligible'),c('converted','Customers with at least one qualifying ordered path?','funnel_converted'),c('optional_cart','Customers converted if cart is optional and views must occur after signup?','optional_converted')],
 'Order, eligibility and elapsed window all matter. Duplicate deliveries must not create another customer conversion.',
 'Independent step counts can include a purchase that happened before the qualifying view.',level=4,metric=True)

add('integrity',1,'iot','No observation, unknown observation, known down','Support wants a device health report that preserves missing and unknown states.','devices heartbeats',
 [c('missing','Devices with no heartbeat observation?','no_observation'),c('unknown','Logical event observations whose healthy value is unknown?','unknown_observations'),c('down','Logical event observations explicitly marked unhealthy?','known_down')],
 'No row, an observed null and an observed false are separate evidence states. Keep coverage separate from the health result.',
 'COALESCE of every missing state to false invents outages.',level=2)
add('integrity',2,'payments','Unknown authorization amount versus no capture','Payments Operations needs a source-completeness explanation before signing off settlement totals.','attempts captures',
 [c('unknown_amounts','Attempt rows with unknown amount?','unknown_amounts'),c('known_zero','Attempt rows with known zero amount?','zero_amounts'),c('without_capture','Logical payments without any capture row?','no_capture')],
 'A missing monetary value, a known zero and no settled record have different business meaning. The capture ledger remains a separate source.',
 'Filling all three with zero can make a technically valid sum look fully reconciled.',level=2)
add('integrity',3,'ai','A missing review is not a failed review','The product team proposes treating absent or null feedback as a failed task.','tasks feedback attempts',
 [c('known','Known human feedback scores?','known_feedback'),c('unknown','Feedback records with unknown score?','unknown_feedback'),c('absent','Tasks without any feedback record?','missing_feedback')],
 'Observation coverage differs from observed quality. Keep task outcomes and feedback evidence separate, and disclose unresolved reviews.',
 'Absence of human feedback does not prove either success or failure.',level=3,diagnose=True)
add('integrity',4,'marketing','Repeated lead deliveries and messy emails','A CRM feed sends repeated lead deliveries with case and whitespace differences. The producer guarantees lead_id is logical identity.','lead_deliveries leads',
 [c('transport_key','Which field identifies a received delivery?','delivery_key'),c('business_key','Which field identifies a logical lead?','lead_key'),c('extra_deliveries','Deliveries beyond one per logical lead?','duplicate_deliveries')],
 'Normalize display comparisons while respecting the producer identity contract. An email is not automatically a unique person or lead.',
 'Deduplicating on normalized email can merge separate legitimate business leads.',level=2)
add('integrity',5,'saas','Invoice state disagrees with a paid-event filter','Billing asks for invoices whose final observed state is paid, not invoices that were ever paid. Use event_at then event_id to select state.','invoices invoice_events',
 [c('event_rows','How many source invoice event rows?','invoice_event_rows'),c('paid_value','Correct final-paid invoice cents?','invoice_paid')],
 'Resolve one state per invoice before filtering paid. Document which source and revision order own the business truth.',
 'Filtering paid events first can resurrect an invoice whose newer state is failed.',level=3,diagnose=True)
add('integrity',6,'logistics','A delivery event has no shipment promise','Operations receives events whose shipment_id does not exist in the promise extract.','shipments shipment_events',
 [c('orphan_count','Event rows without a matching shipment promise?','orphan_events'),c('promise_population','How many shipment promises exist?','shipments')],
 'Investigate source timing versus referential defects. Quarantine or disclose unmatched evidence without silently changing the promise denominator.',
 'An inner join can hide data loss while leaving a plausible rate.',level=3)

add('dimensions',1,'saas','Historical price versus today’s subscription','Customer Success wants the contract value at a past reporting instant rather than the latest version of each subscription.','accounts subscriptions subscription_versions',
 [c('version_identity','Which source field identifies an effective version?','version_key'),c('past_mrr','Active MRR cents at October 3 UTC?','mrr')],
 'Join subscription identity to the version effective at the reporting instant. Current attributes cannot substitute for historical terms.',
 'The latest version can change the meaning of a previously published snapshot.',level=4)
add('dimensions',2,'workforce','Historic work remains with an old employee','A manager wants hours performed on October 2, even for an employee whose relationship ends October 3.','employments assignments time_entries',
 [c('work_hours','Recorded source hours on October 2?','hours'),c('current_staff','Employee headcount at October 3, a separate snapshot?','headcount')],
 'A current employment filter can remove real historical work. Attribute work using the effective work date and explicit allocation rules.',
 'Current eligibility and historical activity are different dimensions of the question.',level=4)
add('dimensions',3,'marketing','Segment at qualification versus current segment','The marketing report labels lead L1 by its segment at qualification on October 2. Sales uses today’s lead segment.','leads lead_states segment_history',
 [c('historical_segment','L1 segment at October 2 under the effective history?','historical_l1_segment'),c('current_enterprise','Number of leads currently labeled enterprise in the source dimension?','enterprise_now')],
 'Pin the classification clock. A current dimension can recategorize past conversion without changing the conversion event.',
 'A historical segment report must not silently use the current label.',level=4)
add('dimensions',4,'iot','A device changes account ownership','Fleet Billing needs the account responsible for trip T1 at its start, while Support needs the current device owner.','devices memberships trips',
 [c('historical_owner','T1 responsible account at trip start?','historic_first_account'),c('current_owner','Current D1 account in the devices source?','current_first_account')],
 'Responsibility follows the effective membership at the event time. Current ownership answers a different support question.',
 'A device-to-current-account join can move old billable work to the new owner.',level=4)
add('dimensions',5,'ai','A task spans model upgrades','Product wants to attribute task outcomes to the model version used by each attempt, including retries after an upgrade.','tasks attempts model_versions',
 [c('attempt_grain','What identifies the execution version observation?','attempt_key'),c('large_attempts','How many attempts used M2?','large_attempts')],
 'Model version belongs to an attempt. Define whether a task rollup uses first, final or all attempted versions, and label that choice.',
 'Attributing every past attempt to the current model family rewrites experiment evidence.',level=4)
add('dimensions',6,'payments','Merchant population versus payment attempts','Operations wants one output per merchant while the authorization source contains repeated logical payment attempts.','merchants attempts captures',
 [c('merchant_key','Which field identifies the consumer entity?','merchant_key'),c('logical_payments','Distinct payment identities in attempts?','payments'),c('attempts','Physical authorization attempts?','attempts')],
 'Keep stable merchant identity and payment identity separate from status events. Zero-activity merchants are still a consumer population decision.',
 'A transactional activity filter can silently omit an eligible merchant.',level=3)

add('validation',1,'commerce','A finance reconciliation identity','Finance approves the synthetic definition: fulfilled header gross minus posted refunds for fulfilled orders equals lifetime net cents.','orders refunds items',
 [c('gross','Gross cents?','gross'),c('refunds','Eligible refund cents?','refunds'),c('net','Net cents?','net')],
 'Reconcile the same population and currency at compatible grains. Check net = gross - refunds and header gross = eligible line gross.',
 'Two matching totals do not prove the same entity set; compare keys and independent components.',level=3,metric=True,diagnose=True)
add('validation',2,'ai','Cost reconciles while success does not','Engineering shows a correct tool-cost total as evidence that task success is also correct.','tasks attempts tool_calls',
 [c('cost_total','Total tool cost cents?','cost'),c('final_successes','Eligible final-attempt approved task successes?','final_success')],
 'A monetary reconciliation does not validate an outcome denominator. Validate each metric with its own entity, eligibility and evidence.',
 'One passing invariant cannot certify unrelated business semantics.',level=4,diagnose=True)
add('validation',3,'iot','Can unknown intervals certify an SLA?','The SLA draft declares all monitored minutes fully measured, even when up_minutes is null.','devices intervals',
 [c('monitored','All monitored minutes?','total_minutes'),c('unknown','Monitored minutes with unknown uptime?','unknown_minutes'),c('strict_result','Certified uptime ratio, rounded to 2 decimals, or null if unknown duration exists?','uptime_strict')],
 'Validate 0 <= known up <= monitored duration and separately prove completeness. Unknown duration blocks a fully certified SLA result.',
 'A bounded ratio can look plausible while omitting unobserved time.',level=4,diagnose=True)
add('validation',4,'marketing','Attribution weights must conserve one lead','The attribution contract says each observed lead-credit group must sum to one.','leads lead_credit',
 [c('invalid_groups','How many lead-credit groups violate sum(weight)=1?','invalid_weights'),c('lead_population','Number of leads in the base extract?','leads')],
 'Test both existing allocation sums and leads with no allocation. These are distinct failures; a sum test alone does not prove population coverage.',
 'A fractional allocation total can exceed distinct leads if bridge weights drift.',level=3,diagnose=True)
add('validation',5,'logistics','A plausible delivery rate hides missing evidence','The service report excludes every shipment without a delivered event and calls the result fleet-wide performance.','shipments shipment_events',
 [c('promises','Original promise population?','shipments'),c('without_delivery','Shipments without a delivered event?','missing_delivery'),c('on_time','On-time first deliveries?','ontime')],
 'Validate denominator coverage independently of the reported rate. Investigate undelivered and missing-event cases before promising a fleet-wide conclusion.',
 'A perfect delivered-only rate can coexist with incomplete delivery evidence.',level=4,diagnose=True)
add('validation',6,'workforce','FTE does not certify headcount','A staffing proposal uses the FTE sum as both capacity and employee headcount.','people employments assignments',
 [c('people','Active employee people on October 3?','headcount'),c('fte','Known employee FTE at that instant?','fte'),c('unknown_source_fte','Unknown FTE source allocation records, including nonemployees?','unknown_fte')],
 'Validate allocation coverage and capacity separately from distinct employee people. Equality in one fixture does not make the measures interchangeable.',
 'Part-time or split assignments can change FTE without the same change in headcount.',level=3,diagnose=True)

add('communication',1,'marketing','Two qualified-lead reports both claim to be right','Sales uses final qualification; Marketing freezes qualification before October 3. Both say their campaign report is correct.','leads lead_states lead_credit',
 [c('current','Final observed qualified lead count?','qualified'),c('historical','Historical qualified lead count?','historical_qualified')],
 'Explain the definition and entity-set difference, avoid declaring a winner from totals alone, and recommend a documented consumer-specific contract.',
 'Equal counts can mask different qualifying identities; a stakeholder message needs the actual clock and attribution assumptions.',level=5,metric=True)
add('communication',2,'saas','Growth appears to offset retention losses','The CEO sees new-logo revenue and asks whether the existing customer book is healthy.','revenue_movements',
 [c('opening','Opening positive-book MRR cents?','opening'),c('new_logo','New-logo MRR cents?','new_revenue'),c('unknown','Opening-book accounts with unresolved closing MRR?','unknown_closing')],
 'Separate acquisition from retention, quantify unresolved evidence, and state what can and cannot be concluded before recommending action.',
 'Total revenue movement can hide churn and contraction among existing accounts.',level=5,metric=True)
add('communication',3,'iot','An executive wants a green uptime badge','The COO wants to publish a fully green reliability badge despite unknown monitored durations.','devices intervals',
 [c('coverage','Known-duration coverage ratio, rounded to 2 decimals?','coverage'),c('unknown','Unknown monitored minutes?','unknown_minutes')],
 'Give the measured result and coverage separately, explain uncertainty in plain language and request an explicit publication decision rather than inventing completeness.',
 'Reporting only the best observed uptime can overstate what the source proves.',level=5,metric=True)
add('communication',4,'workforce','Two teams each claim the same employee','Team leaders want additive departmental headcounts even though a worker has concurrent allocations.','people employments assignments',
 [c('company_people','Distinct active employee people?','headcount'),c('active_allocations','Active employee allocation rows?','active_assignments')],
 'Explain why department presence counts overlap. Offer distinct company headcount alongside explicitly allocated capacity, without forcing an additive people metric.',
 'Summing departmental presence counts can count a shared employee twice.',level=5)
add('communication',5,'payments','Finance challenges a higher payment total','Product summed authorization amounts; Finance summed captures. They ask who made the arithmetic mistake.','attempts captures disputes',
 [c('authorization_total','Known attempt amounts summed in cents?','attempt_amount'),c('settled_total','Actual settled capture cents?','capture_total')],
 'Explain authorization attempts versus settled captures, partial captures, retries and unknown amounts. Reconcile by payment before alleging a calculation defect.',
 'Different lifecycle measures can legitimately disagree even when each sum is arithmetically correct.',level=5,metric=True)
add('communication',6,'ai','A release report uses raw success labels','Leadership wants a task-success claim based only on attempt status=succeeded, while approval and incomplete tasks remain unresolved.','tasks attempts feedback',
 [c('unapproved_success','Succeeded attempts without approval?','false_status_success'),c('eligible','Eligible task population?','eligible_tasks'),c('approved_final','Eligible final-attempt approved successes?','final_success')],
 'Communicate task-level evidence, approval coverage and unresolved maturity; propose a release criterion with a labeled denominator and owner.',
 'Green execution status is not independently verified product task success.',level=6,metric=True,diagnose=True)

RUBRIC=['problem_translation','clarification_quality','grain_and_relationships','metric_definition','temporal_and_integrity','validation_strategy','stakeholder_communication','tradeoff_judgment']
CANDIDATES={
 'REASON-GRAIN-004':'Employee headcount = number of active assignment rows.',
 'REASON-FANOUT-001':'Gross = SUM(order.gross_cents) after joining fulfilled orders to all items.',
 'REASON-FANOUT-002':'Qualified leads = COUNT(credit rows attached to qualified leads).',
 'REASON-FANOUT-003':'Monitored duration = SUM(interval.monitored_minutes) after joining devices to intervals and trips.',
 'REASON-FANOUT-004':'Worked hours = SUM(time_entry.hours) after attaching all effective allocation rows.',
 'REASON-FANOUT-005':'Successful tasks = COUNT(succeeded approved attempt rows after tool-call enrichment).',
 'REASON-FANOUT-006':'Settled value = SUM(capture.cents) after attaching captures to every authorization attempt.',
 'REASON-INTEGRITY-003':'Feedback missing or score NULL means task failed.',
 'REASON-INTEGRITY-005':'Filter invoice events to paid, then select the latest remaining event per invoice.',
 'REASON-VALIDATION-001':'Gross = SUM(DISTINCT order.gross_cents); subtract every refund irrespective of order status.',
 'REASON-VALIDATION-002':'Tool cost agrees with the ledger, so the task success report is certified.',
 'REASON-VALIDATION-003':'Unknown up_minutes = zero. Publish the resulting rate as fully measured fleet uptime.',
 'REASON-VALIDATION-004':'Credit row count is the campaign lead total. No weight or missing-allocation check is needed.',
 'REASON-VALIDATION-005':'Remove shipments without delivered events from the denominator; label the rate fleet-wide performance.',
 'REASON-VALIDATION-006':'SUM(FTE) represents both capacity and distinct employee headcount.',
 'REASON-COMMUNICATION-006':'Task success = succeeded attempt rows / all attempt rows. Approval and pending tasks are excluded from consideration.'}
CANDIDATES.update({
 'REASON-TRANSLATE-001':'Fleet health = healthy heartbeat arrivals / all heartbeat arrivals. Publish this as fleet uptime.',
 'REASON-TRANSLATE-002':'Campaign performance = number of current qualified lead-credit rows. No historical definition is needed.',
 'REASON-TRANSLATE-003':'Recurring revenue equals the amount of every invoice ever observed paid.',
 'REASON-GRAIN-002':'After attaching all user touches, each result row still represents one lead.',
 'REASON-GRAIN-003':'Each distinct delivery_id proves that a new business heartbeat event occurred.',
 'REASON-ENTITIES-001':'Authorization attempt count equals the number of distinct customer payments.',
 'REASON-ENTITIES-002':'A shipment that was delivered at any time has current state delivered.',
 'REASON-ENTITIES-003':'Active users and active accounts are interchangeable product adoption measures.',
 'REASON-METRICS-001':'Monthly active users equals the number of eligible task records.',
 'REASON-METRICS-002':'Customer churn denominator includes new logos. Unknown closing MRR is treated as canceled.',
 'REASON-METRICS-003':'NRR = all closing revenue including new logos / opening MRR; GRR uses the same formula.',
 'REASON-TEMPORAL-001':'The original close report includes every event before close, even when received days later.',
 'REASON-TEMPORAL-002':'Final observed lead status can always reproduce qualification as known before campaign close.',
 'REASON-TEMPORAL-003':'Include both validity ends when selecting the historical version at the midnight boundary.',
 'REASON-INTEGRITY-001':'No heartbeat row, NULL healthy and healthy=false all mean known device downtime.',
 'REASON-INTEGRITY-002':'Unknown amount, known zero and missing capture all represent a fully reconciled zero.',
 'REASON-DIMENSIONS-001':'Select the latest subscription price before producing every historical MRR snapshot.',
 'REASON-DIMENSIONS-002':'Filter time entries to current employees before reporting historical hours.',
 'REASON-DIMENSIONS-003':'Label every past qualification with the current lead segment.',
 'REASON-COMMUNICATION-001':'If both reports have the same qualified count, their definitions are equivalent.',
 'REASON-COMMUNICATION-002':'New-logo growth proves that the existing customer book has healthy retention.',
 'REASON-COMMUNICATION-003':'Publish known-duration uptime as a fully measured SLA without mentioning coverage.'})
PRODUCER={
 'iot':'delivery_id identifies one received heartbeat; event_id identifies a logical heartbeat and can repeat on retry. device_id, interval_id and trip_id identify their respective source entities. Membership version_id identifies an effective ownership interval. Monitored minutes are observed portions of each interval, not necessarily its entire wall-clock duration.',
 'commerce':'customer_id and order_id identify customer and order headers. item_id identifies a line; refund_id identifies a refund. Event rows can repeat business identities; resolve business state before population filters. Header cents and line cents have different grains.',
 'saas':'account_id identifies an account, subscription_id a contract and version_id an effective contract version. event_id identifies an invoice status event; invoice_id identifies the invoice. revenue_movements is an independent authoritative opening/closing book extract keyed by account_id.',
 'payments':'attempt_id identifies an authorization attempt; payment_id groups attempts for one logical payment. capture_id identifies a settled capture; merchant_id identifies the merchant. Equal amounts do not imply the same capture.',
 'logistics':'shipment_id identifies one shipment promise; event_id identifies a business status observation. A later return does not erase a delivery event. Unmatched events are excluded from shipment-promise metrics and investigated separately.',
 'marketing':'lead_id identifies a logical lead; delivery_id a received CRM record; event_id a qualification transition; credit_id an attributed membership. One lead can have several campaign credits. segment_history version_id identifies an effective classification.',
 'workforce':'person_id identifies a person; employment_id a relationship; assignment_id a team allocation; entry_id a work observation. Relationships and allocations use start-inclusive, end-exclusive effective intervals.',
 'ai':'user_id identifies a user, task_id a logical product task, attempt_id a retryable execution, call_id a tool call, feedback_id a review. Task eligibility is supplied explicitly; attempt execution status and approval are separate observations.'}
CHILD_RECALL={
 'translate':[('Should an analytical recommendation identify the business decision?',['yes']),('Should a question expose a material risk to count as essential?',['yes']),('Should acceptance criteria be testable?',['yes'])],
 'grain':[('Does row meaning describe one record or the whole table?',['one record']),('Can one parent match many children?',['yes']),('Should output grain be declared before aggregation?',['yes'])],
 'entities':[('Can a retry share its business identity?',['yes']),('Does an event count always equal an entity count?',['no']),('Should zero-activity eligible entities be considered explicitly?',['yes'])],
 'metrics':[('Should a ratio state its denominator?',['yes']),('Can eligibility filters change a metric?',['yes']),('Should a metric definition label its reporting clock?',['yes'])],
 'fanout':[('Can a join repeat an otherwise correct parent amount?',['yes']),('Under a conserving allocation, what should each complete entity weight group sum to?',['1']),('Can independent child aggregation prevent a cross product?',['yes'])],
 'temporal':[('Which clock places an event in its business period?',['event time']),('Which clock limits what was known at publication?',['receipt time','ingestion time']),('Is the end included in a half-open interval?',['no'])],
 'integrity':[('Is unknown always equivalent to zero?',['no']),('Should retries be deduplicated using guaranteed logical identity?',['yes']),('Should an authoritative source be named for reconciliation?',['yes'])],
 'dimensions':[('Can current ownership misattribute historical activity?',['yes']),('Should an effective classification use the event or snapshot clock?',['yes']),('Can distinct people overlap across segments?',['yes'])],
 'validation':[('Does a conservation check test an invariant?',['yes']),('Must reconciliation compare compatible populations?',['yes']),('Does a plausible rate prove completeness?',['no'])],
 'communication':[('Should material assumptions be visible to the consumer?',['yes']),('Does missing evidence always imply a negative outcome?',['no']),('Should a recommendation name the evidence needed to resolve uncertainty?',['yes'])]}
DECISIONS={
 'translate':['The board will decide whether reliability investment can wait. A headline must distinguish observed service from coverage gaps.',
  'Marketing will allocate its next campaign budget. Sales also needs a reproducible qualification count for follow-up.',
  'Finance needs a recurring-revenue baseline for planning; Collections needs an invoice cash-status view. They can accept separate labeled measures.',
  'Growth will decide whether onboarding is improving customer purchase adoption, not how many repeat orders buyers place.',
  'People Operations will set the hiring baseline. Employee people and capacity must be separately labeled.',
  'Product will decide whether retries recover customer tasks well enough to release the feature; Engineering also monitors execution reliability.'],
 'grain':['Finance needs a reconciliation at one order per result, with line detail available for investigation.',
  'Marketing wants lead-level outreach decisions and touch detail without silently changing the counted population.',
  'Product wants actual heartbeat activity; Ingestion separately measures transport deliveries and retries.',
  'People Operations needs the number of employees represented, with allocation detail for team planning.',
  'Customer Success assigns one account owner to each account-level review; Billing supplies individual subscription contracts.',
  'Product measures whether customer tasks succeed; Engineering measures tool consumption and execution cost.'],
 'entities':['Operations will decide whether payment demand or authorization retry behavior changed.',
  'Operations needs historical delivery reach and a separate current-state exception queue for returned shipments.',
  'Product uses active users to assess adoption; Sales uses active accounts to plan customer outreach.',
  'Fleet Operations will distinguish more adopted devices from heavier usage on existing devices.',
  'People Operations needs a people count that remains meaningful when relationships change.',
  'Merchandising uses orders for demand and distinct buyers for reach. It needs both measures labeled.'],
 'metrics':['Product will track eligible external user adoption for the October extract; repeat task creation is usage depth.',
  'Finance will investigate losses from the opening customer book and separately track unresolved closing observations.',
  'The CFO will assess retention of the opening revenue book, independently of acquisition spending.',
  'Finance will compare fulfilled-order purchase value. Refund-adjusted value is a separate explicitly signed measure.',
  'Operations wants a delivered-service view and a whole-promise exposure view; both may be reported if clearly labeled.',
  'Customer Success will discuss measured reliability and measurement coverage with account owners.'],
 'fanout':['Finance will approve an order revenue report only if item enrichment preserves the authoritative header total.',
  'Marketing needs fractional campaign contribution and distinct qualified lead volume as separate measures.',
  'Engineering needs an availability result that is invariant to the number of trips a device recorded.',
  'Staffing needs actual work performed, plus an explicit policy if work is allocated across teams.',
  'Product needs task outcomes while Finance needs tool costs; cost enrichment must preserve the task population.',
  'Finance will reconcile settled captures to the capture ledger and use authorization attempts only as lifecycle evidence.'],
 'temporal':['Operations needs the report originally knowable at close and a separately labeled later restatement.',
  'Marketing needs qualification at campaign close; Sales needs the latest observed qualification for outreach.',
  'Finance will sign the exact midnight contract snapshot, with one effective version per subscription.',
  'Operations will revise affected delivery periods and explain why the original publication lacked late uploads.',
  'People Operations will use the boundary snapshot for staffing; exits and arrivals remain separately inspectable.',
  'Product will compare the required three-step path with an alternative cart-optional path, keeping the time and eligibility rules explicit.'],
 'integrity':['Support needs separate queues for missing telemetry, unknown observations and observed unhealthy devices.',
  'Payments Operations needs to decide which settlement discrepancies require source investigation.',
  'Product wants a coverage statement before interpreting human feedback as evidence of task quality.',
  'CRM Operations wants reliable lead identity across replayed deliveries without merging distinct leads by email.',
  'Collections needs invoices whose final observed status is paid, rather than invoices that were ever paid.',
  'Operations must investigate unmatched event evidence while keeping the shipment-promise population stable.'],
 'dimensions':['Customer Success will reproduce the contract value at the historical reporting instant.',
  'A manager needs the October 2 work record even for people who have since left.',
  'Marketing needs the customer segment that applied when the qualification occurred.',
  'Billing charges the account responsible at trip start; Support separately uses current ownership.',
  'Product will compare executions by the model version actually used, and separately define any task-level attribution.',
  'Merchant Operations needs one row per eligible merchant, including an explicit treatment of no activity.'],
 'validation':['Finance will sign off only after gross, eligible refunds and net reconcile over the same order set.',
  'Engineering must justify task success separately from the monetary cost reconciliation.',
  'Customer Success needs to know whether the observed data support a fully measured SLA claim.',
  'Marketing will approve attribution only if allocation sums and population coverage both reconcile.',
  'Operations needs to decide whether the service report represents all promised shipments.',
  'Staffing will use distinct people for headcount and explicitly measured capacity for FTE.'],
 'communication':['Sales and Marketing need documented reports for their different operational decisions, with a clear explanation of any disagreement.',
  'The CEO will choose between retention intervention and further acquisition spending using separate evidence.',
  'The COO must approve the publication claim with measured coverage and unresolved uncertainty visible.',
  'Team leaders need a company people total and a transparent explanation of overlapping team presence.',
  'Finance and Product need a lifecycle reconciliation before attributing a discrepancy to an arithmetic defect.',
  'Leadership must define a release criterion based on task-level outcome evidence, approval and pending-task maturity.']}
RUBRIC_GUIDANCE={
 'problem_translation':'Connect the analytical result to a named consumer decision and testable acceptance criteria.',
 'clarification_quality':'Use the actual question ledger to explain material risk; distinguish essential questions, documented assumptions, minor details, overengineering and dangerous assumptions.',
 'grain_and_relationships':'Declare each source and output row meaning, guaranteed identities, relationships and measure additivity.',
 'metric_definition':'Specify compatible population, numerator, denominator and labeled business policy; justify fields marked not applicable.',
 'temporal_and_integrity':'Respect business and availability clocks, boundaries, missing records, nulls, retries and authoritative sources.',
 'validation_strategy':'Propose independent population and component reconciliations, invariants and evidence that could falsify the result.',
 'stakeholder_communication':'Explain the recommendation, quantified evidence and uncertainty in concise consumer language.',
 'tradeoff_judgment':'Defend a proportionate choice, consider a legitimate alternative and name unresolved decision owners.',
 'fault_diagnosis':'Identify the causal defect in the actual candidate, show its consequence and propose a validated repair.'}
METRIC_FIELDS=['definition','entity_grain','numerator','denominator','eligibility','time_window','attribution','missing_duplicates','reconciliation','failure_modes']
RECALL={
 'translate':('Should a stakeholder phrase be treated as a complete metric definition?',['no']),
 'grain':('What does grain describe?',['what one row represents','one row meaning']),
 'entities':('Can a business entity and its execution events have different identities?',['yes']),
 'metrics':('Must a ratio numerator and denominator use compatible eligibility rules?',['yes']),
 'fanout':('Does joining a parent measure to several child rows repeat the parent measure?',['yes']),
 'temporal':('Can event time and receipt time answer different questions?',['yes']),
 'integrity':('Does no record necessarily mean a known zero?',['no']),
 'dimensions':('Can the current attribute differ from the attribute at an event time?',['yes']),
 'validation':('Does one matching total prove the correct entity population?',['no']),
 'communication':('Should a material unverified assumption be disclosed?',['yes'])}

def build():
 out=[]
 for s in SPECS:
  area=s['area'];domain=s['domain'];tag=f'business.{area}.core';children=AREAS[area][2]
  offset=(int(s['id'].split('-')[-1])-1)%len(children)
  child_indexes=[offset,(offset+1)%len(children)]
  tags=[tag]+[f'business.{area}.{children[i]}' for i in child_indexes]
  diagnose=s['id'] in CANDIDATES
  clean=fixture(domain);truth=facts(domain,clean);policy=s['alternative'] or {'specified':'Use the explicitly stated exercise contract; record unresolved interpretation separately.'}
  checks=[]
  for name,prompt,calc in s['checks']:
   val=truth[calc];kind='keys' if isinstance(val,list) else 'number' if val is None or isinstance(val,(int,Decimal)) or isinstance(val,str) and val.lstrip('-').replace('.','',1).isdigit() else 'text'
   checks.append({'field':name,'prompt':prompt,'type':kind,'calculation':calc})
  if s['alternative']:
   mapping={'iot':{'known_observation':'uptime_known','strict_contract':'uptime_strict'},'marketing':{'current':'qualified','historical':'historical_qualified'},'ai':{'final':'success_final','any':'success_any'},'logistics':{'delivered':'on_time_delivered','all_promises':'on_time_all'}}[domain]
   checks.append({'field':'selected_result','prompt':'Under your chosen, labeled definition, what is the resulting ratio (2 decimals), count, or null if uncertifiable?','type':'number','calculation_by_policy':mapping})
  manual=RUBRIC+(['fault_diagnosis'] if diagnose else [])
  clarifications=[
   {'id':'decision','intent':'Which business decision and consumer does the request support?','category':'essential','response':DECISIONS[area][int(s['id'].split('-')[-1])-1]},
   {'id':'definition','intent':'What metric, event, denominator, source identity or attribution definition is intended?','category':'essential','response':'Use a definition tied to the stakeholder decision. Authorized labeled policies: '+json.dumps(policy)},
   {'id':'clock','intent':'Which reporting clock, effective boundary or availability cutoff applies?','category':'essential','response':'Use the explicitly named dates when present. Otherwise assess all rows in the displayed synthetic extract without adding an unstated date filter; this is not a live source. Event and receipt clocks remain separate.'},
   {'id':'identity','intent':'What does each source row mean and which producer identity is guaranteed?','category':'essential','response':PRODUCER[domain]},
   {'id':'rounding','intent':'Can we document display rounding?','category':'documented_assumption','response':'Display ratios to 2 decimal places; retain exact cents and unrounded components for reconciliation.'},
   {'id':'display','intent':'Which cosmetic sort, chart color or report title is required?','category':'minor','response':'No particular cosmetic order or color is needed for this decision.'},
   {'id':'platform','intent':'Do we need a new real-time platform for this static extract?','category':'overengineering','response':'No. This case requires reasoning over a bounded synthetic extract; a new platform is not an acceptance criterion.'},
   {'id':'unsafe','intent':'Can an unresolved observation or business rule be assumed harmless?','category':'dangerous_assumption','response':s['pitfall']+' Treat material unverified claims as pending or blockers.'}]
  hidden=[]
  for variant in VARIANTS:
   data=fixture(domain,variant);fv=facts(domain,data)
   hidden.append({'variant':variant,'fixture_sha256':fingerprint(data),'expected':{p:{c['field']:fv[c.get('calculation') or c['calculation_by_policy'][p]] for c in checks} for p in policy}})
  p={'contract_version':'ae-problem-v1','problem_id':s['id'],'title':s['title'],'neutral_title':s['title'],'domain':domain,'business_context':NAMES[domain]+': '+s['request'],
   'difficulty':{'level':f'L{s["level"]}','dimensions':{'requirement_ambiguity':min(3,s['level']),'business_semantics':min(3,s['level']),'hidden_edge_cases':2,'conflicting_stakeholders':2 if s['level']>=5 else 0},'rationale':'The decision, evidence and business consequences determine difficulty; no SQL is required.'},
   'kind':'reasoning','skills_tested':tags,'mastery_tags':tags,'tables':[t for t in schemas(domain,clean) if t['name'] in s['inputs']],
   'sample_rows':{t:clean[t][:12] for t in s['inputs']},'requirements':['Clarify material uncertainty before adopting a definition.','Make a defensible recommendation supported by the displayed evidence.'],
   'expected_output_grain':'A learner-defined decision contract with explicit entity and reporting grain; objective source identities are checked separately.',
   'hidden_edge_cases':[s['pitfall']],'learner_prompt':{'prediction':'What would you ask the stakeholder first, and why?','requirements':['State the business decision and known versus unknown requirements.'],'proposal':'Explain a short plan before making the analytical recommendation.','answer_fields':['facts','policy','decision','assumptions','metric_contract']},
   'learner_answer':None,'evaluation_rules':{'adapter':'business_reasoning','criteria':manual,'checks':checks,'policies':policy,'metric_fields':METRIC_FIELDS if s['metric'] else ['definition','entity_grain','reconciliation'],
     'prerequisites':[f'business.{a}.core' for a in AREAS[area][1]],'clarifications':clarifications,'resolution':s['reason'],'common_error':s['pitfall'],
     'rubric_guidance':{k:RUBRIC_GUIDANCE[k] for k in manual},'score_anchors':{'0':'Absent, unsupported or materially incorrect.','1':'Partial reasoning with a material unresolved gap.','2':'Defensible and supported by the saved evidence.','3':'Defensible, independently validated and proportionate about uncertainty and alternatives.'},
     'validation_strategy':['Recompute each displayed source fact at its stated identity and clock.',s['reason'],'Challenge this failure mode: '+s['pitfall']]},
   'hidden_tests':hidden,'followups':['What independent evidence would change your recommendation?'],
   'hints':['Name the stakeholder decision before choosing a number.',f'Identify the main {AREAS[area][0].lower()} risk in one source row.',s['pitfall'],s['reason']],
   'solution':s['reason']+' Validate the declared population, grain, clocks and uncertainty before communicating the result.',
   'transfer_from':None,'modes':['LEARN','PRACTICE','INTERVIEW'],
   'artifacts':{'response_type':'reasoning','area':area,'diagnosis_task':diagnose,'metric_case':s['metric'],
     'candidate_reasoning':CANDIDATES.get(s['id']),
     'provenance':'Original AE Lab business reasoning case using synthetic project-owned evidence.'},
   'recall':[{'prompt':RECALL[area][0],'accepted':RECALL[area][1],'concepts':[tag]}]+[{'prompt':CHILD_RECALL[area][i][0],'accepted':CHILD_RECALL[area][i][1],'concepts':[f'business.{area}.{children[i]}']} for i in child_indexes]}
  out.append(p)
 for p in out:
  peers=[q for q in out if q['artifacts']['area']==p['artifacts']['area'] and q['domain']!=p['domain']]
  p['transfer_from']=peers[0]['problem_id']
 return out

if __name__=='__main__':
 path=ROOT/'curriculum/business-bank.json';path.write_text(json.dumps(build(),indent=2)+'\n');print(f'{len(SPECS)} original reasoning cases written')
