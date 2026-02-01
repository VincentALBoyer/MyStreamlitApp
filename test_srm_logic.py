
import sys
import os

# Add the directory to path so we can import logic
sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))

import logic

def test_srm_logic():
    print("1. Initializing Game...")
    state = logic.init_game()
    assert len(state.available_suppliers) == 4
    print("   - Game initialized with 4 suppliers.")

    print("2. Selecting Supplier...")
    target = state.available_suppliers[0].id
    logic.select_supplier(state, target)
    assert state.active_supplier is not None
    assert state.active_supplier.id == target
    print(f"   - Selected {state.active_supplier.name}")

    print("3. Simulating 30 Days...")
    for i in range(30):
        logic.process_daily_turn(state)
    
    print(f"   - Simulation complete. Day: {state.current_day}")
    print(f"   - Deliveries logged: {len(state.delivery_log)}")
    print(f"   - Total Spend: ${state.total_spend:.2f}")
    print(f"   - Total Rework: ${state.total_rework_cost:.2f}")

    print("4. Generating CSV...")
    csv_content = logic.get_csv_export(state)
    assert len(csv_content) > 0
    print("   - CSV generated successfully.")
    
    print("✅ TEST PASSED")

if __name__ == "__main__":
    test_srm_logic()
