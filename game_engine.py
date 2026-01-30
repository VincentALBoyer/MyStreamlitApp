import pandas as pd
import numpy as np
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from typing import List, Dict, Optional, Literal

# ═══════════════════════════════════════════════════════════════════════════════
#                           DATA CLASSES & GAME STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketEvent:
    """Represents a global or targeted market event (e.g., strike, demand surge)"""
    name: str
    description: str
    duration: int
    type: Literal["supply", "demand", "general"]
    target_id: Optional[str] = None  # Specific supplier/customer ID or None for global
    magnitude: float = 1.0  # Multiplier or adder depending on context
    active: bool = True

@dataclass
class Supplier:
    """Represents a supplier with pricing and lead time characteristics"""
    id: str
    name: str
    emoji: str
    unit_price: float
    lead_time_min: int
    lead_time_max: int
    min_order: int
    max_order: int  # Maximum order capacity (base)
    reliability: float  # Probability of on-time delivery
    
    reliability: float  # Probability of on-time delivery
    
    def get_lead_time(self, active_events: List[MarketEvent] = []) -> int:
        """Calculate actual lead time with reliability factor and event modifiers"""
        base_time = random.randint(self.lead_time_min, self.lead_time_max)
        
        # Check for active disruption events targeting this supplier
        delay_days = 0
        for event in active_events:
            if event.active and event.type == "supply" and (event.target_id == self.id or event.target_id is None):
                # Magnitude for supply events is typically "added days"
                delay_days += int(event.magnitude)
        
        # Reliability affects if there's a delay (independent of events)
        if random.random() > self.reliability:
            base_time += random.randint(1, 3)
            
        return base_time + delay_days
    
    def get_daily_max_order(self) -> int:
        """Get today's max order capacity (varies daily due to supply constraints)"""
        # Random variation: 40% to 130% of base max capacity
        variation = random.uniform(0.4, 1.3)
        return int(self.max_order * variation)

@dataclass
class CustomerProfile:
    id: str
    name: str
    emoji: str
    urgency_days: int # Expected delivery time (from order creation)

@dataclass
class CustomerOrder:
    """Represents a customer order with delivery tracking"""
    id: int
    day_created: int
    quantity: int
    customer: CustomerProfile
    delivery_time: int = 2  # Days to deliver to customer once shipped (transit time)
    quantity_fulfilled: int = 0
    status: str = "pending"  # pending, in_transit, delivered
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
    """Represents an order placed to a supplier"""
    id: int
    supplier_id: str
    day_ordered: int
    quantity: int
    unit_cost: float
    expected_arrival: int
    status: str = "in_transit"  # in_transit, delivered
    day_delivered: Optional[int] = None

@dataclass
class GameState:
    """Complete game state"""
    current_day: int = 1
    max_days: int = 30
    inventory: int = 100  # Starting inventory
    cash: float = 5000.0  # Starting cash
    
    # Pricing
    # Pricing & Constraints
    selling_price: float = 20.0
    holding_cost_per_unit: float = 0.50
    warehouse_capacity: int = 150
    overflow_cost_per_unit: float = 5.00
    delay_penalty: float = 15.0
    
    # Orders
    customer_orders: List[CustomerOrder] = field(default_factory=list)
    supplier_orders: List[SupplierOrder] = field(default_factory=list)
    
    # Events & Market
    active_events: List[MarketEvent] = field(default_factory=list)
    
    # Counters
    next_customer_order_id: int = 1
    next_supplier_order_id: int = 1
    
    # Statistics
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_holding_cost: float = 0.0
    total_penalties: float = 0.0
    units_sold: int = 0
    orders_fulfilled: int = 0
    orders_delayed: int = 0
    
    # Daily log
    daily_events: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    
    # Daily supplier availability (updated each day)
    supplier_availability: Dict = field(default_factory=dict)
    
    game_over: bool = False

# Initialize suppliers
SUPPLIERS = {
    "dragon": Supplier("dragon", "Dragon Electronics", "🇨🇳", 8.0, 5, 7, 50, 200, 0.85),
    "aztec": Supplier("aztec", "Aztec Components", "🇲🇽", 10.0, 2, 3, 20, 100, 0.95),
    "fasttrack": Supplier("fasttrack", "FastTrack USA", "🇺🇸", 12.0, 1, 2, 10, 60, 0.99),
    "precision": Supplier("precision", "PrecisionTech DE", "🇩🇪", 11.0, 3, 4, 30, 120, 0.97)
}

# Initialize Customers
CUSTOMERS = [
    CustomerProfile("techstore", "TechStore Inc.", "🏢", 3),
    CustomerProfile("urgent", "UrgentFlight", "🚀", 1),
    CustomerProfile("local", "LocalShop", "🏪", 5),
    CustomerProfile("mega", "MegaCorp", "🏭", 4)
]

def update_supplier_availability(state: GameState):
    """Update daily supplier availability"""
    state.supplier_availability = {}
    for sid, supplier in SUPPLIERS.items():
        daily_max = supplier.get_daily_max_order()
        is_available = daily_max >= supplier.min_order
        state.supplier_availability[sid] = {
            "max_today": daily_max if is_available else 0,
            "min": supplier.min_order,
            "available": is_available
        }

# ═══════════════════════════════════════════════════════════════════════════════
#                              GAME LOGIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_customer_demand(day: int, active_events: List[MarketEvent] = []) -> int:
    """Generate random customer demand quantity, influenced by events"""
    day_of_week = day % 7
    if day_of_week in [1, 2, 3]:  # Mon-Wed
        base = random.randint(15, 35)
    elif day_of_week in [4, 5]:  # Thu-Fri
        base = random.randint(10, 25)
    else:  # Weekend
        base = random.randint(5, 15)
    
    # Apply Event Modifiers
    multiplier = 1.0
    for event in active_events:
        if event.active and event.type == "demand":
            multiplier *= event.magnitude
            
    base = int(base * multiplier)
    
    if random.random() < 0.10:
        base = int(base * 1.5)
    
    return base

def create_customer_order(state: GameState, quantity: int) -> CustomerOrder:
    """Create a new customer order for a random customer"""
    customer = random.choice(CUSTOMERS)
    # Transit time is fixed for simplicity (2 days), but urgency depends on customer
    transit_time = 2 
    
    order = CustomerOrder(
        id=state.next_customer_order_id,
        day_created=state.current_day,
        quantity=quantity,
        customer=customer,
        delivery_time=transit_time
    )
    state.next_customer_order_id += 1
    state.customer_orders.append(order)
    return order

def ship_specific_order(state: GameState, order_id: int) -> bool:
    """Manually ship a specific order if inventory exists. Full fulfillment only."""
    # Find order
    order = next((o for o in state.customer_orders if o.id == order_id), None)
    
    if not order:
        return False
    
    if order.status != "pending":
        return False
        
    # Check Inventory
    if state.inventory >= order.quantity:
        state.inventory -= order.quantity
        order.quantity_fulfilled = order.quantity
        order.status = "in_transit"
        order.day_shipped = state.current_day
        order.expected_delivery = state.current_day + order.delivery_time
        return True
    
    return False

def process_supplier_deliveries(state: GameState) -> List[str]:
    """Process incoming deliveries"""
    events = []
    for order in state.supplier_orders:
        if order.status == "in_transit" and order.expected_arrival <= state.current_day:
            order.status = "delivered"
            order.day_delivered = state.current_day
            state.inventory += order.quantity
            supplier = SUPPLIERS[order.supplier_id]
            events.append(
                f"📦 Received {order.quantity} units from {supplier.emoji} {supplier.name}"
            )
    return events

def process_customer_deliveries(state: GameState) -> List[str]:
    """Process orders arriving at customers"""
    events = []
    
    for order in state.customer_orders:
        if order.status == "in_transit" and order.expected_delivery <= state.current_day:
            order.status = "delivered"
            order.day_delivered = state.current_day
            state.orders_fulfilled += 1
            
            # Revenue
            revenue = order.quantity * state.selling_price
            state.total_revenue += revenue
            state.cash += revenue
            state.units_sold += order.quantity
            
            events.append(
                f"✅ Order #{order.id} delivered to {order.customer.name}."
            )
    
    return events

def calculate_daily_penalties(state: GameState) -> List[str]:
    """Calculate penalties for orders pending > 24 hours"""
    events = []
    for order in state.customer_orders:
        if order.status == "pending":
            # If order is older than 1 day (created yesterday or before), apply penalty
            # e.g. Created Day 1. End of Day 1 -> Age 0. End of Day 2 -> Age 1.
            # "Within 24 hours" implies if not shipped by the next day's close?
            # Let's say grace period is 1 day.
            if state.current_day > order.day_created + 1:
                penalty = state.delay_penalty
                state.total_penalties += penalty
                state.cash -= penalty
                events.append(f"⚠️ Late Penalty: Order #{order.id} (Day {order.day_created}) -${penalty:.0f}")
    return events

def calculate_holding_costs(state: GameState) -> float:
    """Calculate inventory holding costs with warehouse limits"""
    # Standard capacity cost
    normal_units = min(state.inventory, state.warehouse_capacity)
    overflow_units = max(0, state.inventory - state.warehouse_capacity)
    
    cost_normal = normal_units * state.holding_cost_per_unit
    cost_overflow = overflow_units * state.overflow_cost_per_unit
    
    total_cost = cost_normal + cost_overflow
    
    state.total_holding_cost += total_cost
    state.cash -= total_cost
    return total_cost

def place_supplier_order(state: GameState, supplier_id: str, quantity: int) -> Optional[SupplierOrder]:
    if quantity <= 0: return None
    supplier = SUPPLIERS[supplier_id]
    if quantity < supplier.min_order: return None
    total_cost = quantity * supplier.unit_price
    if state.cash < total_cost: return None
    
    state.cash -= total_cost
    state.total_cost += total_cost
    
    # Pass active events to get impacted lead time
    arrival_day = state.current_day + supplier.get_lead_time(state.active_events)
    
    order = SupplierOrder(
        id=state.next_supplier_order_id,
        supplier_id=supplier_id,
        day_ordered=state.current_day,
        quantity=quantity,
        unit_cost=supplier.unit_price,
        expected_arrival=arrival_day
    )
    state.next_supplier_order_id += 1
    state.supplier_orders.append(order)
    return order

def get_kpis(state: GameState) -> Dict:
    pending = [o for o in state.customer_orders if o.status == "pending"]
    partial = [] # Deprecated concept in new full-ship logic, but keeping for compatibility if needed
    in_transit = [o for o in state.customer_orders if o.status == "in_transit"]
    delivered = [o for o in state.customer_orders if o.status == "delivered"]
    
    if delivered:
        avg_fulfillment = sum(o.day_delivered - o.day_created for o in delivered) / len(delivered)
    else:
        avg_fulfillment = 0
    
    incoming_qty = sum(o.quantity for o in state.supplier_orders if o.status == "in_transit")
    pending_demand = sum(o.remaining for o in pending)
    
    profit = state.total_revenue - state.total_cost - state.total_holding_cost - state.total_penalties
    
    completed_ops = len(delivered) + len(in_transit)
    total_ops = len(state.customer_orders)
    fill_rate = (completed_ops / total_ops * 100) if total_ops > 0 else 100
    
    return {
        "inventory": state.inventory,
        "cash": state.cash,
        "profit": profit,
        "revenue": state.total_revenue,
        "costs": state.total_cost,
        "holding_costs": state.total_holding_cost,
        "penalties": state.total_penalties,
        "units_sold": state.units_sold,
        "orders_pending": len(pending),
        "incoming_qty": incoming_qty,
        "avg_fulfillment_days": avg_fulfillment,
        "orders_delayed": state.orders_delayed,
        "fill_rate": fill_rate,
        "pending_demand": pending_demand
    }

def generate_market_event(state: GameState) -> Optional[str]:
    """Randomly generate a new market event"""
    # 10% chance of a new event each day if fewer than 2 active
    if len(state.active_events) >= 2 or random.random() > 0.10:
        return None
        
    event_types = [
        ("demand", "📈 Tech Boom! High Demand", "Analysts predict a surge in electronics demand.", 3, 1.5, None),
        ("demand", "📉 Market Slump", "Consumer confidence is low.", 3, 0.7, None),
        ("supply", "⚓ Port Strike", "Customs delays at major ports.", 5, 5.0, None), # +5 days
        ("supply", "⚡ Factory Fire", "Semiconductor factory issues.", 7, 7.0, "dragon"), # Specific to Dragon
        ("supply", "🌪️ Storm Warning", "Shipping routes disrupted.", 3, 3.0, "aztec")
    ]
    
    etype, name, desc, duration, mag, target = random.choice(event_types)
    
    new_event = MarketEvent(name, desc, duration, etype, target, mag)
    state.active_events.append(new_event)
    return f"📰 NEWS FLASH: {name} - {desc}"

def update_events(state: GameState) -> List[str]:
    """Decrease duration of active events and remove expired ones"""
    logs = []
    active = []
    for event in state.active_events:
        event.duration -= 1
        if event.duration > 0:
            active.append(event)
        else:
            logs.append(f"✅ Event Ended: {event.name}")
    state.active_events = active
    return logs

def save_day_snapshot(state: GameState, kpis: Dict):
    state.history.append({"day": state.current_day, **kpis})
