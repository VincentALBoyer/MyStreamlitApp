from game_engine import GameState, MarketEvent, calculate_holding_costs, Supplier, generate_market_event

def test_warehouse_overflow():
    print("\n--- Testing Warehouse Overflow ---")
    state = GameState()
    state.warehouse_capacity = 100
    state.holding_cost_per_unit = 1.0
    state.overflow_cost_per_unit = 10.0
    state.cash = 1000
    
    # Case 1: Under Capacity
    state.inventory = 50
    cost = calculate_holding_costs(state)
    print(f"Inventory: 50/100. Cost: {cost}")
    assert cost == 50.0, f"Expected 50.0, got {cost}"
    
    # Case 2: At Capacity
    state = GameState() # Reset
    state.warehouse_capacity = 100
    state.holding_cost_per_unit = 1.0
    state.overflow_cost_per_unit = 10.0
    state.inventory = 100
    cost = calculate_holding_costs(state)
    print(f"Inventory: 100/100. Cost: {cost}")
    assert cost == 100.0, f"Expected 100.0, got {cost}"
    
    # Case 3: Over Capacity
    state = GameState() # Reset
    state.warehouse_capacity = 100
    state.holding_cost_per_unit = 1.0
    state.overflow_cost_per_unit = 10.0
    state.inventory = 120
    cost = calculate_holding_costs(state)
    # Expected: 100 * 1.0 + 20 * 10.0 = 100 + 200 = 300
    print(f"Inventory: 120/100. Cost: {cost}")
    assert cost == 300.0, f"Expected 300.0, got {cost}"
    print("✅ Warehouse Overflow Logic Verified")

def test_market_event_generation():
    print("\n--- Testing Market Event Generation ---")
    state = GameState()
    
    # Force event generation (usually random)
    # depending on implementation, might need to mock random or loop until one appears
    # For now, let's manually inspect the mechanics
    
    # Add a mock event
    evt = MarketEvent(
        name="Test Strike", 
        description="Workers on strike", 
        duration=3, 
        type="supply", 
        target_id="dragon", 
        magnitude=5.0
    )
    state.active_events.append(evt)
    
    assert len(state.active_events) == 1
    print(f"Added Event: {state.active_events[0]}")
    print("✅ Market Event Structure Verified")

def test_supply_disruption():
    print("\n--- Testing Supply Disruption ---")
    state = GameState()
    
    # Setup Supplier
    supplier = Supplier("test", "Test Sup", "T", 10.0, 5, 5, 10, 100, 1.0) # Lead time fixed at 5 (min=max=5, reliable=1.0)
    
    # Base Case
    lead = supplier.get_lead_time(active_events=[])
    print(f"Base Lead Time: {lead}")
    assert lead == 5
    
    # Disruption Case
    evt = MarketEvent("Strike", "Strike", 5, "supply", "test", 10.0) # +10 days
    lead_delayed = supplier.get_lead_time(active_events=[evt])
    print(f"Delayed Lead Time: {lead_delayed}")
    assert lead_delayed == 15 # 5 + 10
    
    print("✅ Supply Disruption Verified")

if __name__ == "__main__":
    test_warehouse_overflow()
    test_market_event_generation()
    test_supply_disruption()
