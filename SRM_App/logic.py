import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Supplier:
    id: str
    name: str
    category: str  # Raw Materials, Logistics, Components
    quality_score: int  # 0-100
    cost_index: float  # Multiplier (e.g., 1.0 is standard)
    reliability: int  # 0-100 % chance of hitting lead time
    lead_time: int
    capacity: int
    risk_level: str  # Low, Med, High
    status: str = "Active"  # Active, Under Review, Blacklisted
    
    # Performance History
    deliveries_completed: int = 0
    on_time_deliveries: int = 0
    quality_failures: int = 0

@dataclass
class SourcingBid:
    id: str
    supplier_name: str
    proposed_cost: float
    guaranteed_lead_time: int
    quality_commitment: int
    reliability_commitment: int

@dataclass
class Contract:
    id: int
    supplier_id: str
    category: str
    start_day: int
    duration: int
    terms_cost: float
    is_active: bool = True

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    cash: float = 50000.0
    
    # Supplier Master
    suppliers: Dict[str, Supplier] = field(default_factory=dict)
    
    # Active Sourcing
    contracts: List[Contract] = field(default_factory=list)
    available_bids: List[SourcingBid] = field(default_factory=list)
    next_contract_id: int = 1
    
    # Performance Data
    total_savings: float = 0
    risk_events_hit: int = 0
    
    # History
    daily_events: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=dict)
    
    game_over: bool = False

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_supplier_network() -> Dict[str, Supplier]:
    return {
        "VEND-001": Supplier("VEND-001", "Global Circuits", "Components", 92, 1.2, 95, 4, 1000, "Low"),
        "VEND-002": Supplier("VEND-002", "SwiftLogix", "Logistics", 75, 0.8, 80, 2, 5000, "Med"),
        "VEND-003": Supplier("VEND-003", "CheapParts Co", "Components", 60, 0.6, 65, 7, 2000, "High"),
        "VEND-004": Supplier("VEND-004", "Prime Materials", "Raw Materials", 98, 1.5, 99, 5, 500, "Low"),
        "VEND-005": Supplier("VEND-005", "Standard Sourcing", "Raw Materials", 82, 1.0, 90, 4, 1500, "Low"),
        "VEND-006": Supplier("VEND-006", "Atlas Freight", "Logistics", 88, 1.1, 85, 3, 3000, "Med")
    }

# =============================================================================
# GAME ACTIONS
# =============================================================================

def generate_sourcing_event(state: GameState, category: str):
    """Generate 3 competing bids for a category"""
    state.available_bids = []
    
    # Templates for bids
    if category == "Raw Materials":
        base_cost = 5000
    elif category == "Logistics":
        base_cost = 3000
    else:  # Components
        base_cost = 8000
        
    for i in range(3):
        # Trade-off logic: High quality = High cost
        quality = random.randint(60, 98)
        cost_mod = (quality / 80) * random.uniform(0.9, 1.1)
        lead_time = max(1, 10 - (quality // 10))
        reliability = random.randint(70, 99)
        
        bid = SourcingBid(
            id=f"BID-{category[:2]}-{i+1}",
            supplier_name=f"Proposed Vendor {i+1}",
            proposed_cost=base_cost * cost_mod,
            guaranteed_lead_time=lead_time,
            quality_commitment=quality,
            reliability_commitment=reliability
        )
        state.available_bids.append(bid)

def award_contract(state: GameState, bid_id: str, category: str):
    """Award a contract to a bidder"""
    bid = next((b for b in state.available_bids if b.id == bid_id), None)
    if not bid:
        return False
        
    contract = Contract(
        id=state.next_contract_id,
        supplier_id=bid.id, # In this sim, we create a new vendor entry from the bid
        category=category,
        start_day=state.current_day,
        duration=10,
        terms_cost=bid.proposed_cost
    )
    
    # Create the supplier entry for tracking
    new_vendor = Supplier(
        id=bid.id,
        name=bid.supplier_name,
        category=category,
        quality_score=bid.quality_commitment,
        cost_index=1.0,
        reliability=bid.reliability_commitment,
        lead_time=bid.guaranteed_lead_time,
        capacity=2000,
        risk_level="Med"
    )
    
    state.suppliers[bid.id] = new_vendor
    state.contracts.append(contract)
    state.next_contract_id += 1
    state.cash -= bid.proposed_cost # Initial setup cost
    state.available_bids = [] # Clear sourcing event
    return True

def process_daily_batch(state: GameState):
    """Process supplier disruptions and scorecard updates"""
    state.daily_events = []
    
    # 1. Contract Performance Checks
    for contract in state.contracts:
        if not contract.is_active: continue
        
        vendor = state.suppliers.get(contract.supplier_id)
        if not vendor: continue
        
        # Daily Operational Cost
        cost = contract.terms_cost * 0.05 # 5% of contract value per day
        state.cash -= cost
        
        # Reliability Check (Random disruption)
        if random.randint(0, 100) > vendor.reliability:
            state.daily_events.append(f"⚠️ DISRUPTION: {vendor.name} delayed shipment (Reliability failure)")
            state.risk_events_hit += 1
            vendor.quality_score = max(0, vendor.quality_score - 2)
        else:
            vendor.on_time_deliveries += 1
            
        vendor.deliveries_completed += 1
    
    # 2. Random Market Events
    if random.random() < 0.15: # 15% chance of market event
        events = [
            ("Raw Material shortage", "Raw Materials", -5),
            ("Fuel price surge", "Logistics", -10),
            ("Port congestion", "Logistics", -3),
            ("New quality standard", "Components", -5)
        ]
        ev_name, cat, impact = random.choice(events)
        state.daily_events.append(f"🌍 MARKET EVENT: {ev_name}! {cat} vendors quality impacted.")
        for s in state.suppliers.values():
            if s.category == cat:
                s.quality_score = max(0, s.quality_score + impact)

    # 3. Financial Update
    state.current_day += 1
    if state.current_day > state.max_days or state.cash < 0:
        state.game_over = True

def get_kpis(state: GameState) -> Dict:
    """Calculate SRM KPIs"""
    avg_quality = sum(s.quality_score for s in state.suppliers.values()) / len(state.suppliers) if state.suppliers else 0
    active_contracts = len([c for c in state.contracts if c.is_active])
    reliability_rate = sum(s.on_time_deliveries for s in state.suppliers.values()) / \
                       sum(s.deliveries_completed for s in state.suppliers.values()) * 100 \
                       if sum(s.deliveries_completed for s in state.suppliers.values()) > 0 else 0
                       
    return {
        "day": state.current_day,
        "cash": state.cash,
        "avg_quality": avg_quality,
        "active_contracts": active_contracts,
        "reliability_rate": reliability_rate,
        "risk_events": state.risk_events_hit
    }
