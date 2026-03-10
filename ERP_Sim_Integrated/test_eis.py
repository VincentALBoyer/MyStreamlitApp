import sys
sys.path.insert(0, '.')

print('=== EIS Simulator — Engine Tests ===')

print('Testing config...')
import config
print('  OK: config.py')

print('Testing engine/state...')
from engine.state import SimState, Material, Product
print('  OK: engine/state.py')

print('Testing engine/srm_engine...')
from engine.srm_engine import init_suppliers
print('  OK: engine/srm_engine.py')

print('Testing engine/crm_engine...')
from engine.crm_engine import init_customers, generate_new_leads
print('  OK: engine/crm_engine.py')

print('Testing engine/erp_engine...')
from engine.erp_engine import init_simulation, advance_day, get_kpis, export_activity_log, export_kpi_summary
print('  OK: engine/erp_engine.py')

print('')
print('=== Running Full Simulation Test ===')
state = init_simulation()
print(f'  Day 1: Cash=${state.cash:.0f}, Materials={len(state.materials)}, Suppliers={len(state.suppliers)}')
print(f'  Inbox messages: {len(state.inbox)}, Sales orders: {len(state.sales_orders)}')

from engine.srm_engine import update_supplier_prices
update_supplier_prices(state)
advance_day(state)
print(f'  After Day 1 advance: Day={state.current_day}, Events={len(state.daily_events)}')

kpis = get_kpis(state)
print(f'  KPIs: Cash=${kpis["cash"]:.0f}, Open Orders={kpis["open_orders"]}, OTIF={kpis["otif_pct"]}%')

print('')
print('=== Testing ERP Actions ===')
from engine.erp_engine import create_work_order, ship_sales_order, create_manual_po, run_mrp_suggestion

# Create production run
ok, msg = create_work_order(state, 'P01', 5)
print(f'  Create WO (5x City Cruiser): {ok} — {msg}')

# Manual PO
ok, msg = create_manual_po(state, 'S01', 'M01', 30, 18.0, 3)
print(f'  Manual PO (30x Steel Frame): {ok} — {msg}')

# MRP suggestions
suggestions = run_mrp_suggestion(state)
print(f'  MRP suggestions: {len(suggestions)} items')

print('')
print('=== Testing SRM ===')
state.srm_enabled = True
from engine.srm_engine import send_rfq, award_rfq, create_contract, get_supplier_scorecard
ok, msg, rfq = send_rfq(state, 'M01', 100)
print(f'  RFQ sent: {ok}, msg={msg}, responses={len(rfq.responses) if rfq else 0}')

if rfq and rfq.responses:
    best_sup = rfq.responses[0]['supplier_id']
    ok, msg2 = award_rfq(state, rfq.id, best_sup)
    print(f'  Award RFQ to {rfq.responses[0]["supplier_name"]}: {ok} — {msg2}')

sc = get_supplier_scorecard(state, 'S01')
print(f'  Supplier scorecard S01: deliveries={sc["deliveries"]}, rel_score={sc["relationship_score"]}')

print('')
print('=== Testing CRM ===')
state.crm_enabled = True
init_customers(state)
print(f'  Customers loaded: {len(state.customers)}')

from engine.crm_engine import run_marketing_campaign, advance_lead_stage, create_service_ticket, resolve_ticket
ok, msg, leads = run_marketing_campaign(state, 'digital_ads')
print(f'  Digital ads campaign: {ok}, {msg}')

if state.leads:
    lead_id = state.leads[0].id
    ok, msg = advance_lead_stage(state, lead_id, 'Qualified')
    print(f'  Advance lead to Qualified: {ok} — {msg}')

print('')
print('=== Testing Exports ===')
log_csv = export_activity_log(state)
kpi_csv = export_kpi_summary(state)
print(f'  Activity log CSV: {len(log_csv)} bytes')
print(f'  KPI summary CSV: {len(kpi_csv)} bytes')

print('')
print('=== ALL TESTS PASSED ===')
