import random
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Material:
    id: str
    name: str
    cost: float
    unit: str

@dataclass
class Product:
    id: str
    name: str
    price: float
    bom: Dict[str, int] # Bill of Materials: {material_id: qty_needed}
    production_hours: int # Capacity needed

@dataclass
class SalesOrder:
    id: str
    day_placed: int
    customer_name: str
    product_id: str
    qty: int
    unit_price: float
    due_day: int
    status: str = "Open" # Open, Shipped, Cancelled
    shipped_day: Optional[int] = None

@dataclass
class WorkOrder:
    id: str
    product_id: str
    qty: int
    day_started: int
    hours_required: int
    hours_completed: int = 0
    status: str = "InProgress" # InProgress, Completed
    completion_day: int = 0

@dataclass
class PurchaseOrder:
    id: str
    material_id: str
    qty: int
    day_placed: int
    lead_time: int
    arrival_day: int
    unit_cost: float
    status: str = "OnOrder" # OnOrder, Received

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    cash: float = 20000.0
    
    # Master Data
    materials: Dict[str, Material] = field(default_factory=dict)
    products: Dict[str, Product] = field(default_factory=dict)
    
    # Inventory
    stock_materials: Dict[str, int] = field(default_factory=dict) # {mat_id: qty}
    stock_finished: Dict[str, int] = field(default_factory=dict) # {prod_id: qty}
    
    # Transactions
    sales_orders: List[SalesOrder] = field(default_factory=list)
    work_orders: List[WorkOrder] = field(default_factory=list)
    purchase_orders: List[PurchaseOrder] = field(default_factory=list)
    
    # Capacity
    daily_capacity_hours: int = 80 # e.g. 10 workers * 8 hours
    
    # Financials
    daily_logs: List[str] = field(default_factory=list) # Audit log
    
    game_over: bool = False

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_game() -> GameState:
    state = GameState()
    
    # 1. Setup Materials (Raw Goods)
    state.materials = {
        "M01": Material("M01", "Steel Pipe", 15.0, "pcs"),
        "M02": Material("M02", "Rubber Tire", 8.0, "pcs"),
        "M03": Material("M03", "Leather Seat", 12.0, "pcs"),
        "M04": Material("M04", "Paint Pack", 5.0, "L"),
    }
    
    # 2. Setup Products (Finished Goods)
    state.products = {
        "P01": Product("P01", "City Bike", 180.0, {"M01": 2, "M02": 2, "M03": 1, "M04": 1}, 4), # 4 hours to make
        "P02": Product("P02", "Pro Racer", 350.0, {"M01": 3, "M02": 2, "M03": 1, "M04": 2}, 6), # 6 hours to make
    }
    
    # 3. Initial Inventory
    state.stock_materials = {
        "M01": 20,
        "M02": 20,
        "M03": 10,
        "M04": 10
    }
    state.stock_finished = {
        "P01": 5,
        "P02": 2
    }
    
    # 4. Generate starting demand
    generate_daily_demand(state)
    
    return state

def generate_daily_demand(state: GameState):
    """Generates random sales orders for the day"""
    # 1-3 Orders per day
    num_orders = random.randint(1, 3)
    
    customers = ["BikeWorld", "CitySports", "EcoRide", "UrbanOutfitters"]
    
    for _ in range(num_orders):
        prod_id = random.choice(list(state.products.keys()))
        qty = random.randint(1, 5)
        
        # Rush order?
        is_rush = random.random() < 0.2
        due_offset = 2 if is_rush else random.randint(3, 7)
        
        so = SalesOrder(
            id=f"SO-{state.current_day}-{random.randint(100,999)}",
            day_placed=state.current_day,
            customer_name=random.choice(customers),
            product_id=prod_id,
            qty=qty,
            unit_price=state.products[prod_id].price,
            due_day=state.current_day + due_offset
        )
        state.sales_orders.append(so)
        state.daily_logs.append(f"🆕 New Order: {so.customer_name} wants {qty}x {state.products[prod_id].name} (Due Day {so.due_day})")

# =============================================================================
# MECHANICS: ACTIONS
# =============================================================================

def buy_material(state: GameState, material_id: str, qty: int) -> Tuple[bool, str]:
    """Place a PO for materials"""
    if qty <= 0: return False, "Qty must be > 0"
    
    mat = state.materials.get(material_id)
    cost = mat.cost * qty
    
    if state.cash < cost:
        return False, "Insufficient Cash"
    
    # Deduct cash immediately (Simple model) or AP? 
    # Let's deduct on receipt to be friendlier? No, let's allow "Net 30" (Pay later)?
    # For simplicity, deduct 50% now, 50% later? 
    # Let's keep it simple: Deduct NOW (Cash basis) to force cash management.
    
    state.cash -= cost
    
    lead_time = random.randint(2, 4)
    arrival = state.current_day + lead_time
    
    po = PurchaseOrder(
        id=f"PO-{state.current_day}-{random.randint(1000,9999)}",
        material_id=material_id,
        qty=qty,
        day_placed=state.current_day,
        lead_time=lead_time,
        arrival_day=arrival,
        unit_cost=mat.cost
    )
    state.purchase_orders.append(po)
    state.daily_logs.append(f"💸 Bought {qty}x {mat.name} for ${cost:.0f}. Arrival: Day {arrival}")
    return True, "Order Placed"

def create_work_order(state: GameState, product_id: str, qty: int) -> Tuple[bool, str]:
    """Schedule production"""
    if qty <= 0: return False, "Qty must be > 0"
    
    prod = state.products.get(product_id)
    
    # 1. Check Materials
    for mat_id, needed in prod.bom.items():
        total_needed = needed * qty
        if state.stock_materials.get(mat_id, 0) < total_needed:
            return False, f"Missing Material: {state.materials[mat_id].name} (Need {total_needed})"
            
    # 2. Consume Materials
    for mat_id, needed in prod.bom.items():
        state.stock_materials[mat_id] -= (needed * qty)
        
    # 3. Create WO
    total_hours = prod.production_hours * qty
    
    wo = WorkOrder(
        id=f"WO-{state.current_day}-{random.randint(1000,9999)}",
        product_id=product_id,
        qty=qty,
        day_started=state.current_day,
        hours_required=total_hours
    )
    state.work_orders.append(wo)
    state.daily_logs.append(f"🔧 Started Production: {qty}x {prod.name} (Requires {total_hours} hrs)")
    return True, "Production Started"

def ship_order(state: GameState, so_id: str) -> Tuple[bool, str]:
    """Ship a sales order to customer"""
    so = next((o for o in state.sales_orders if o.id == so_id), None)
    if not so: return False, "Order not found"
    if so.status != "Open": return False, "Order not open"
    
    # Check Finished Stock
    if state.stock_finished.get(so.product_id, 0) < so.qty:
        return False, "Not enough stock"
        
    # Ship it
    state.stock_finished[so.product_id] -= so.qty
    so.status = "Shipped"
    so.shipped_day = state.current_day
    
    # Recognize Revenue
    revenue = so.qty * so.unit_price
    state.cash += revenue
    
    state.daily_logs.append(f"🚚 Shipped {so.customer_name}: +${revenue:.0f}")
    return True, "Shipped!"

# =============================================================================
# MECHANICS: TURN PROCESSING
# =============================================================================

def process_daily_turn(state: GameState):
    """Advance the day"""
    state.daily_logs.clear()
    
    # 1. New Demand
    generate_daily_demand(state)
    
    # 2. Receive Materials
    arrived_pos = []
    for po in state.purchase_orders:
        if po.status == "OnOrder" and state.current_day >= po.arrival_day:
            po.status = "Received"
            state.stock_materials[po.material_id] = state.stock_materials.get(po.material_id, 0) + po.qty
            arrived_pos.append(po)
            # state.daily_logs.append(f"🚛 Received {po.qty}x {state.materials[po.material_id].name}")
            
    if arrived_pos:
        state.daily_logs.append(f"🚛 {len(arrived_pos)} Inbound Deliveries Processed")

    # 3. Advance Production (Capacity constraint)
    # We allocate today's 80 hours to open Work Orders
    available_hours = state.daily_capacity_hours
    
    active_wos = [wo for wo in state.work_orders if wo.status == "InProgress"]
    # Simple FIFO allocation
    for wo in active_wos:
        if available_hours <= 0: break
        
        remaining_work = wo.hours_required - wo.hours_completed
        work_to_do = min(available_hours, remaining_work)
        
        wo.hours_completed += work_to_do
        available_hours -= work_to_do
        
        # Check completion
        if wo.hours_completed >= wo.hours_required:
            wo.status = "Completed"
            wo.completion_day = state.current_day
            state.stock_finished[wo.product_id] = state.stock_finished.get(wo.product_id, 0) + wo.qty
            state.daily_logs.append(f"✅ Production Finished: {wo.qty}x {state.products[wo.product_id].name}")

    # 4. Advance Date
    state.current_day += 1
    if state.current_day > state.max_days:
        state.game_over = True

def get_csv_export(state: GameState) -> str:
    """Export all transaction data as a chronological blockchain-style ledger"""
    data = []
    
    # helper to add row
    def add_row(day, type_, ref_id, details, cash_impact=0.0):
        data.append({
            "Day": day,
            "Event_Type": type_,
            "Ref_ID": ref_id,
            "Details": details,
            "Cash_Impact": cash_impact
        })
    
    # 1. Sales Orders (Placed & Shipped)
    for so in state.sales_orders:
        prod_name = state.products[so.product_id].name
        # Event: Order Received
        add_row(so.day_placed, "New Sales Order", so.id, 
               f"Customer {so.customer_name} ordered {so.qty}x {prod_name}")
        
        # Event: Shipped
        if so.status == "Shipped" and so.shipped_day:
            val = so.qty * so.unit_price
            add_row(so.shipped_day, "Order Shipped", so.id, 
                   f"Shipped to {so.customer_name}", val)

    # 2. Production (Started & Finished)
    for wo in state.work_orders:
        prod_name = state.products[wo.product_id].name
        # Event: Start
        add_row(wo.day_started, "Production Started", wo.id,
               f"Started batch of {wo.qty}x {prod_name}")
        
        # Event: Finish
        if wo.status == "Completed" and wo.completion_day:
             add_row(wo.completion_day, "Production Finished", wo.id,
                    f"Completed {wo.qty}x {prod_name}")

    # 3. Purchasing (Placed & Received)
    for po in state.purchase_orders:
        mat_name = state.materials[po.material_id].name
        cost = po.qty * po.unit_cost
        
        # Event: Placed
        add_row(po.day_placed, "PO Placed", po.id,
               f"Ordered {po.qty}x {mat_name}", -cost) # Cash out
        
        # Event: Received
        if po.status == "Received" and po.arrival_day <= state.current_day: # Arrivals are pre-set
             add_row(po.arrival_day, "PO Received", po.id,
                    f"Received {po.qty}x {mat_name}")

    # Sort by Day, then by Type (inputs before outputs)
    data.sort(key=lambda x: (x["Day"], x["Event_Type"]))
    
    # Add cumulative balance? Optional, but blockchain-y.
    balance = 20000.0 # Starting
    for row in data:
        balance += row["Cash_Impact"]
        row["Running_Balance"] = balance
        
    df = pd.DataFrame(data)
    # Reorder columns
    cols = ["Day", "Event_Type", "Ref_ID", "Details", "Cash_Impact", "Running_Balance"]
    return df[cols].to_csv(index=False)
