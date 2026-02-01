import pandas as pd
import numpy as np
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ═══════════════════════════════════════════════════════════════════════════════
#                           DATA CLASSES & GAME STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Supplier:
    id: str
    name: str
    emoji: str
    unit_price: float
    lead_time_min: int
    lead_time_max: int
    min_order: int
    max_order: int
    reliability: float
    
    def get_lead_time(self) -> int:
        base_time = random.randint(self.lead_time_min, self.lead_time_max)
        if random.random() > self.reliability:
            base_time += random.randint(1, 3)
        return base_time
    
    def get_daily_max_order(self) -> int:
        variation = random.uniform(0.4, 1.3)
        return int(self.max_order * variation)

@dataclass
class CustomerProfile:
    id: str
    name: str
    emoji: str
    urgency_days: int

@dataclass
class CustomerOrder:
    id: int
    day_created: int
    quantity: int
    customer: CustomerProfile
    delivery_time: int = 2
    quantity_fulfilled: int = 0
    status: str = "pending"
    day_shipped: Optional[int] = None
    expected_delivery: Optional[int] = None
    day_delivered: Optional[int] = None
    
    @property
    def remaining(self) -> int:
        return self.quantity - self.quantity_fulfilled
        
    @property
    def due_date(self) -> int:
        return self.day_created + self.customer.urgency_days

@dataclass
class SupplierOrder:
    id: int
    supplier_id: str
    day_ordered: int
    quantity: int
    unit_cost: float
    expected_arrival: int
    status: str = "in_transit"
    day_delivered: Optional[int] = None

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    inventory: int = 100
    cash: float = 5000.0
    selling_price: float = 20.0
    holding_cost_per_unit: float = 0.50
    delay_penalty: float = 15.0
    customer_orders: List[CustomerOrder] = field(default_factory=list)
    supplier_orders: List[SupplierOrder] = field(default_factory=list)
    next_customer_order_id: int = 1
    next_supplier_order_id: int = 1
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_holding_cost: float = 0.0
    total_penalties: float = 0.0
    units_sold: int = 0
    orders_fulfilled: int = 0
    orders_delayed: int = 0
    daily_events: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    supplier_availability: Dict = field(default_factory=dict)
    game_over: bool = False

# Constants
SUPPLIERS = {
    "dragon": Supplier("dragon", "Dragon Electronics", "🇨🇳", 8.0, 5, 7, 50, 200, 0.85),
    "aztec": Supplier("aztec", "Aztec Components", "🇲🇽", 10.0, 2, 3, 20, 100, 0.95),
    "fasttrack": Supplier("fasttrack", "FastTrack USA", "🇺🇸", 12.0, 1, 2, 10, 60, 0.99),
    "precision": Supplier("precision", "PrecisionTech DE", "🇩🇪", 11.0, 3, 4, 30, 120, 0.97)
}

CUSTOMERS = [
    CustomerProfile("techstore", "TechStore Inc.", "🏢", 3),
    CustomerProfile("urgent", "UrgentFlight", "🚀", 1),
    CustomerProfile("local", "LocalShop", "🏪", 5),
    CustomerProfile("mega", "MegaCorp", "🏭", 4)
]

# Logic Functions
def update_supplier_availability(state: GameState):
    state.supplier_availability = {}
    for sid, supplier in SUPPLIERS.items():
        daily_max = supplier.get_daily_max_order()
        is_available = daily_max >= supplier.min_order
        state.supplier_availability[sid] = {
            "max_today": daily_max if is_available else 0,
            "min": supplier.min_order,
            "available": is_available
        }

def generate_customer_demand(day: int) -> int:
    day_of_week = day % 7
    if day_of_week in [1, 2, 3]:  base = random.randint(15, 35)
    elif day_of_week in [4, 5]: base = random.randint(10, 25)
    else: base = random.randint(5, 15)
    if random.random() < 0.10: base = int(base * 1.5)
    return base

def create_customer_order(state: GameState, quantity: int) -> CustomerOrder:
    customer = random.choice(CUSTOMERS)
    order = CustomerOrder(
        id=state.next_customer_order_id,
        day_created=state.current_day,
        quantity=quantity,
        customer=customer,
        delivery_time=2
    )
    state.next_customer_order_id += 1
    state.customer_orders.append(order)
    return order

def ship_specific_order(state: GameState, order_id: int) -> bool:
    order = next((o for o in state.customer_orders if o.id == order_id), None)
    if not order or order.status != "pending": return False
    if state.inventory >= order.quantity:
        state.inventory -= order.quantity
        order.quantity_fulfilled = order.quantity
        order.status = "in_transit"
        order.day_shipped = state.current_day
        order.expected_delivery = state.current_day + order.delivery_time
        return True
    return False

def process_supplier_deliveries(state: GameState) -> List[str]:
    events = []
    for order in state.supplier_orders:
        if order.status == "in_transit" and order.expected_arrival <= state.current_day:
            order.status = "delivered"
            order.day_delivered = state.current_day
            state.inventory += order.quantity
            supplier = SUPPLIERS[order.supplier_id]
            events.append(f"📦 Received {order.quantity} units from {supplier.emoji} {supplier.name}")
    return events

def process_customer_deliveries(state: GameState) -> List[str]:
    events = []
    for order in state.customer_orders:
        if order.status == "in_transit" and order.expected_delivery <= state.current_day:
            order.status = "delivered"
            order.day_delivered = state.current_day
            state.orders_fulfilled += 1
            rev = order.quantity * state.selling_price
            state.total_revenue += rev
            state.cash += rev
            state.units_sold += order.quantity
            events.append(f"✅ Order #{order.id} delivered to {order.customer.name}")
    return events

def calculate_daily_penalties(state: GameState) -> List[str]:
    events = []
    for order in state.customer_orders:
        if order.status == "pending" and state.current_day > order.day_created + 1:
            state.total_penalties += state.delay_penalty
            state.cash -= state.delay_penalty
            events.append(f"⚠️ Late Penalty: Order #{order.id} -${state.delay_penalty:.0f}")
    return events

def calculate_holding_costs(state: GameState) -> float:
    cost = state.inventory * state.holding_cost_per_unit
    state.total_holding_cost += cost
    state.cash -= cost
    return cost

def place_supplier_order(state: GameState, supplier_id: str, quantity: int) -> Optional[SupplierOrder]:
    if quantity <= 0: return None
    supplier = SUPPLIERS[supplier_id]
    if quantity < supplier.min_order: return None
    cost = quantity * supplier.unit_price
    if state.cash < cost: return None
    state.cash -= cost
    state.total_cost += cost
    arrival = state.current_day + supplier.get_lead_time()
    order = SupplierOrder(
        id=state.next_supplier_order_id,
        supplier_id=supplier_id,
        day_ordered=state.current_day,
        quantity=quantity,
        unit_cost=supplier.unit_price,
        expected_arrival=arrival
    )
    state.next_supplier_order_id += 1
    state.supplier_orders.append(order)
    return order

def get_kpis(state: GameState) -> Dict:
    pending = [o for o in state.customer_orders if o.status == "pending"]
    delivered = [o for o in state.customer_orders if o.status == "delivered"]
    in_transit = [o for o in state.customer_orders if o.status == "in_transit"]
    profit = state.total_revenue - state.total_cost - state.total_holding_cost - state.total_penalties
    fill_rate = (len(delivered)+len(in_transit))/len(state.customer_orders)*100 if state.customer_orders else 100
    return {
        "inventory": state.inventory,
        "cash": state.cash,
        "profit": profit,
        "revenue": state.total_revenue,
        "costs": state.total_cost,
        "holding_costs": state.total_holding_cost,
        "penalties": state.total_penalties,
        "fill_rate": fill_rate,
        "orders_pending": len(pending),
        "incoming_qty": sum(o.quantity for o in state.supplier_orders if o.status == "in_transit")
    }

def save_day_snapshot(state: GameState, kpis: Dict):
    state.history.append({"day": state.current_day, **kpis})
