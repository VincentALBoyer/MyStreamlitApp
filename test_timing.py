
import sys
import os
import random

sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))
import logic

def test_arrival_timing():
    state = logic.init_game()
    print("1. Placing Order on Day 1 (Express, 1 Day Lead)...")
    supp = next(s for s in state.available_suppliers if s.id == "V-FAST")
    logic.place_order(state, supp.id, 100)
    
    po = state.active_pos[0]
    print(f"   - PO {po.id} Placed. Expected Arrival: Day {po.expected_arrival_day}")
    # Day 1 + 1 = Day 2 Expected.
    
    print("\n2. Processing Day 1 -> Day 2...")
    logic.process_daily_turn(state)
    # Now Day 2.
    print(f"   - Current Day: {state.current_day}")
    print(f"   - PO Status: {po.status}")
    print(f"   - Inventory: {state.inventory}")
    
    # Logic: 
    # Day 1 -> Day 2 turn.
    # Current Day was 1. Expected 2. 1 >= 2 False.
    # Increment -> 2.
    # Result: Day 2 UI. PO Status "Open" (In Transit). Inventory 500 (Base).
    # Wait, my logic check is `current_day >= expected`.
    # Turn 1: current=1. expected=2. False.
    # Turn 2: current=2. expected=2. True.
    # Arrives END of Day 2?
    
    # If Express (1 day). Place Day 1. Arrive Day 2.
    # User sees it arrive on Day 2 screen?
    # If I place order Day 1. Day 1 Sim runs.
    # Day 2 Screen appears.
    # If it arrived Day 2 (PM) in sim? No, sim advances day.
    
    # If I want it to arrive Day 2.
    # process_daily_turn(Day 1) -> Advances to Day 2.
    # Does it check arrival for Day 2? No, `current_day` is 1 during the check.
    # So it arrives Day 2 Sim (End of Day 2).
    # Visible Day 3.
    
    # This is standard Lead Time logic (Order Day 1, Lead 1 -> Arrive Day 2 End -> Available Day 3).
    # User wanted "Arrive Day 9, Available Day 10". 
    # If Lead Time is 1. Order Day 1. Expected Day 2.
    # Day 1 Sim -> Day 2.
    # Day 2 Sim -> Arrives -> Added to Stock -> Day 3.
    
    # This seems correct for "Available Day 3".
    # Express Components: Lead 1.
    # If I want it Available Day 2? Then Lead Time should be 0.
    
    pass

if __name__ == "__main__":
    test_arrival_timing()
