import random
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Delivery:
    """Represents a completed delivery for analysis"""
    id: str
    day_arrived: int
    supplier_name: str
    qty_received: int
    qty_defective: int
    rework_cost: float
    status: str # On Time, Late
    unit_price: float

@dataclass
class PurchaseOrder:
    """A specific order placed by the student"""
    id: str
    supplier_id: str
    day_placed: int
    qty_ordered: int
    quoted_lead_time: int
    expected_arrival_day: int
    status: str = "Open" # Open, Shipped, Received, Processing
    arrival_day: Optional[int] = None

@dataclass
class Supplier:
    id: str
    name: str 
    category: str
    
    # VISIBLE
    quoted_price: float
    current_price: float 
    previous_price: float # For day-to-day delta
    quoted_lead_time: int
    min_order_qty: int
    
    # HIDDEN
    true_reliability: float 
    true_defect_rate: float 
    true_lead_time_var: int 
    true_price_volatility: float 
    
    description: str

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    cash: float = 50000.0
    
    # Sourcing
    available_suppliers: List[Supplier] = field(default_factory=list)
    active_supplier: Optional[Supplier] = None
    
    # Inventory & MRP
    inventory: int = 500 # Start with some buffer
    production_schedule: Dict[int, int] = field(default_factory=dict) # Day -> Qty Needed
    active_pos: List[PurchaseOrder] = field(default_factory=list)
    
    # Analytics
    delivery_log: List[Delivery] = field(default_factory=list)
    daily_events: List[str] = field(default_factory=list)
    
    # Financials
    total_spend: float = 0.0
    total_rework_cost: float = 0.0
    total_stockout_penalty: float = 0.0
    
    game_over: bool = False

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_game() -> GameState:
    state = GameState()
    
    # 1. Suppliers (Same as before but with Min Order Qty)
    # 1. Suppliers
    state.available_suppliers = [
        Supplier("V-LOW", "CutRate Sensors", "Components", 10.0, 10.0, 10.0, 5, 200, 0.70, 0.15, 4, 0.05, "Aggressive pricing, spotty quality."),
        Supplier("V-FAST", "Express Components", "Components", 25.0, 25.0, 25.0, 1, 10, 0.98, 0.01, 0, 0.05, "Overnight delivery premium. Reliable."),
        Supplier("V-MID", "Standard Supply", "Components", 14.0, 14.0, 14.0, 5, 100, 0.90, 0.03, 2, 0.10, "Balanced choice for standard needs."),
        Supplier("V-VOL", "Global Trading", "Components", 11.0, 11.0, 11.0, 8, 500, 0.85, 0.05, 5, 0.40, "High volume importer. Volatile.")
    ]
    
    # 2. Generate Production Schedule (The Demand)
    # Variable demand pattern to force planning
    for day in range(1, 32):
        # Base demand 100, spikes every 5 days
        demand = 100
        if day % 5 == 0:
            demand = 300 # Surge
        if day > 20: 
            demand += 50 # Late sim ramp up
        
        # Add some noise
        demand += random.randint(-10, 20)
        state.production_schedule[day] = demand
        
    return state

def commit_draft_orders(state: GameState):
    """Transition Draft POs to Open, deducting cash."""
    drafts = [po for po in state.active_pos if po.status == "Draft"]
    confirmed_count = 0
    
    for po in drafts:
        supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
        cost = po.qty_ordered * supp.current_price
        
        # Final Budget Check (Removed - Unlimited)
        # if state.cash >= cost:
        if True:
            state.cash -= cost # We still track cash flow (it will go negative, or we just ignore)
            state.total_spend += cost
            po.status = "Open"
            state.daily_events.append(f"📝 PO Confirmed: {po.qty_ordered} from {supp.name}")
            confirmed_count += 1
        # else:
        #    ...
            
    return confirmed_count

# =============================================================================
# GAME ACTIONS
# =============================================================================

def switch_supplier(state: GameState, supplier_id: str):
    """Switch active supplier. In a complex sim, this might cost money/time."""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if supp:
        # If switching, maybe a small admin fee?
        if state.active_supplier and state.active_supplier.id != supplier_id:
             state.daily_events.append(f"🔄 Switched partner to {supp.name}")
        state.active_supplier = supp

def place_order(state: GameState, supplier_id: str, qty: int, status: str = "Open"):
    """Manual PO placement. If status='Draft', no cash deduction yet."""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if not supp:
        return False, "Invalid Supplier"
    
    if qty < supp.min_order_qty:
        return False, f"Below Min Order Qty ({supp.min_order_qty})"
    
    # Cost Check
    cost = qty * supp.current_price
    # Removed Budget Check as per user request (Unlimited Budget, Minimize Cost)
    # if state.cash < cost:
    #    return False, "Insufficient Budget"
    
    # Setup PO
    arrival_day = state.current_day + supp.quoted_lead_time
    
    po = PurchaseOrder(
        id=f"PO-{state.current_day}-{random.randint(100,999)}",
        supplier_id=supp.id,
        day_placed=state.current_day,
        qty_ordered=qty,
        quoted_lead_time=supp.quoted_lead_time,
        expected_arrival_day=arrival_day,
        status=status
    )
    
    if status == "Open":
        # Commit Immediately
        state.cash -= cost
        state.total_spend += cost
        state.daily_events.append(f"📝 PO Placed: {qty} units from {supp.name} (Est. Day {arrival_day})")
    elif status == "Draft":
        # Do not deduct cash yet. Do not log public event.
        pass
        
    state.active_pos.append(po)
    return True, "Order Placed"

def process_daily_turn(state: GameState):
    state.daily_events = []
    
    # 0. MARKET FLUCTUATIONS (Update Spot Prices)
    for s in state.available_suppliers:
        # Save previous
        s.previous_price = s.current_price
        
        # Volatility check
        if s.true_price_volatility > 0:
            change = random.uniform(-s.true_price_volatility, s.true_price_volatility)
            s.current_price = s.quoted_price * (1.0 + change)
            # Ensure no huge drops below cost (optional, but keep simple)
            s.current_price = max(s.quoted_price * 0.5, s.current_price)
            
            # Big Spike Event
            if random.random() < 0.05: # 5% chance of surge
                s.current_price *= 1.5
                state.daily_events.append(f"📈 PRICE SURGE: {s.name} spot price jump to ${s.current_price:.2f}")
    
    # 1. RECEIVING LOGIC (Check for arrivals)
    # We iterate a copy to modify the list safely if we were removing (though we keep POs for history? No, move to delivery log)
    arrived_pos = []
    
    # 1. PREDICTIVE ALERTS (Day Before)
    for po in state.active_pos:
        if po.status != "Open": continue
        if state.current_day == po.expected_arrival_day - 1:
             is_late = random.random() > next((s.true_reliability for s in state.available_suppliers if s.id == po.supplier_id), 0.9)
             if is_late:
                 supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
                 days_late = random.randint(1, supp.true_lead_time_var)
                 po.expected_arrival_day += days_late
                 state.daily_events.append(f"⚠️ NOTICE: PO {po.id} delayed by carrier. New Arrival: Day {po.expected_arrival_day}")

    # 2. PRODUCTION RUN (Consumption - Using Start-of-Day Stock)
    demand = state.production_schedule.get(state.current_day, 0)
    
    if state.inventory >= demand:
        state.inventory -= demand
    else:
        # STOCKOUT
        shortfall = demand - state.inventory
        penalty = shortfall * 20.0 
        state.total_stockout_penalty += penalty
        state.inventory = 0
        state.cash -= penalty
        state.daily_events.append(f"🛑 LINE STOPPAGE! Missing {shortfall} units. Penalty: ${penalty:,.0f}")

    # 3. END-OF-DAY LOGISTICS (Arrivals & Stocking)
    
    # Step A: Upgrade "Processing" to "Received" (Stock becomes available)
    # This happens for goods that arrived YESTERDAY (Day X-1), so they are ready for Day X.
    for po in state.active_pos:
        if po.status == "Processing":
            # Add to Inventory
            supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
            
            # Defects logic
            defect_rate = supp.true_defect_rate
            if random.random() < 0.2: defect_rate *= 2.0 
            qty_bad = int(po.qty_ordered * defect_rate)
            qty_good = po.qty_ordered - qty_bad
            
            rework = qty_bad * 50.0
            state.total_rework_cost += rework
            state.cash -= rework
            state.inventory += qty_good
            
            # KPI Log
            promised_day = po.day_placed + po.quoted_lead_time
            status_kpi = "On Time"
            if state.current_day > promised_day:
                 status_kpi = f"Late ({state.current_day - promised_day}d)"
            
            po.status = "Received"
            # We don't need to keep it in active_pos for UI if we don't want to.
            # User will see Inventory jump.
            # Maybe keep event?
            
            deliv = Delivery(
                id=f"DEL-{po.id}",
                day_arrived=state.current_day,
                supplier_name=supp.name,
                qty_received=qty_good,
                qty_defective=qty_bad,
                rework_cost=rework,
                status=status_kpi,
                unit_price=po.qty_ordered * supp.quoted_price / po.qty_ordered if po.qty_ordered else 0 
            )
            state.delivery_log.append(deliv)
            
            msg = f"✅ STOCK AVAILABLE: {qty_good} units from {supp.name}."
            if qty_bad > 0: msg += f" ({qty_bad} Defective!)"
            state.daily_events.append(msg)
    
    # Step B: Check for NEW Arrivals (Open -> Processing)
    # We check if they arrive *Tomorrow*? No, we want them to appear as "Processing" on Tomorrow's screen.
    # So we check if current_day + 1 >= expected.
    for po in state.active_pos:
        if po.status == "Open":
            if state.current_day + 1 >= po.expected_arrival_day:
                po.status = "Processing"
                state.daily_events.append(f"🚛 ARRIVAL: PO {po.id} at dock. Processing (Available +24h).")

    # Clean up PO list (Remove completely processed ones)
    state.active_pos = [po for po in state.active_pos if po.status != "Received"]
        
    # 3. ADVANCE
    state.current_day += 1
    if state.current_day > state.max_days:
        state.game_over = True

# =============================================================================
# EXPORT
# =============================================================================
def get_csv_export(state: GameState) -> str:
    cols = ["Day", "Supplier", "Qty_Good", "Qty_Defect", "Rework_Cost", "Status"]
    data = []
    for d in state.delivery_log:
        data.append({
            "Day": d.day_arrived,
            "Supplier": d.supplier_name,
            "Qty_Good": d.qty_received,
            "Qty_Defect": d.qty_defective,
            "Rework_Cost": d.rework_cost,
            "Status": d.status
        })
    return pd.DataFrame(data, columns=cols).to_csv(index=False)

def get_supplier_stats(state: GameState, supplier_id: str) -> Dict:
    """Calculate real-time performance stats for a supplier"""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if not supp: return {}
    
    # Filter deliveries
    deliveries = [d for d in state.delivery_log if d.supplier_name == supp.name]
    total_deliv = len(deliveries)
    
    if total_deliv == 0:
        return {
            "deliveries": 0,
            "defect_rate": 0.0,
            "reliability": 100.0, # Benefit of the doubt
            "total_rework": 0.0,
            "has_history": False
        }
        
    total_items = sum(d.qty_received + d.qty_defective for d in deliveries)
    total_defects = sum(d.qty_defective for d in deliveries)
    
    defect_rate = (total_defects / total_items * 100) if total_items > 0 else 0.0
    
    on_time = sum(1 for d in deliveries if d.status == "On Time")
    reliability = (on_time / total_deliv * 100)
    
    return {
        "deliveries": total_deliv,
        "defect_rate": defect_rate,
        "reliability": reliability,
        "total_rework": sum(d.rework_cost for d in deliveries),
        "has_history": True
    }
