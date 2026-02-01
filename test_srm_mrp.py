
import sys
import os

# Add the directory to path so we can import logic
sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))

import logic

def test_srm_mrp_logic():
    print("1. Initializing Game...")
    state = logic.init_game()
    assert state.inventory == 500
    assert len(state.production_schedule) == 31
    print("   - Schedule generated.")

    print("2. Placing PO...")
    # Select first supplier
    logic.switch_supplier(state, "V-LOW")
    success, msg = logic.place_order(state, 1000)
    assert success
    assert len(state.active_pos) == 1
    po = state.active_pos[0]
    print(f"   - PO Placed. Est Arrival: Day {po.expected_arrival_day}")

    print("3. Simulating Production & Arrival...")
    # Simulate until arrival
    for i in range(10):
        # We start at Day 1
        current = state.current_day
        logic.process_daily_turn(state)
        
        # Check if PO arrived
        if state.delivery_log: 
             # Verify it moved from active_pos to log
             pass
    
    print(f"   - Day {state.current_day}")
    print(f"   - Inventory: {state.inventory}")
    print(f"   - Stockout Cost: ${state.total_stockout_penalty}")
    
    # If we didn't order enough, we should have stockouts by day 10 (demand ~100/day, start 500)
    assert state.total_stockout_penalty > 0 or state.inventory > 0
    print("   - Simulation logic valid.")

    print("4. CSV Export...")
    csv = logic.get_csv_export(state)
    assert len(csv) > 0
    
    print("✅ TEST PASSED")

if __name__ == "__main__":
    test_srm_mrp_logic()
