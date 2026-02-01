
import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))
import logic

def test_csv_export():
    print("1. Initializing Game...")
    state = logic.init_game()
    
    # Place an order to ensure deliveries happen
    print("2. Placing Order...")
    supp = state.available_suppliers[0]
    logic.place_order(state, supp.id, 100) # Lead time e.g. 5 days
    
    # Fast forward
    print("3. Simulating 10 days...")
    for _ in range(10):
        logic.process_daily_turn(state)
        
    print(f"   Current Day: {state.current_day}")
    print(f"   Delivery Log Count: {len(state.delivery_log)}")
    
    if len(state.delivery_log) > 0:
        print("   [OK] Log has entries.")
    else:
        print("   [FAIL] Log is empty!")

    print("4. Generating CSV...")
    csv = logic.get_csv_export(state)
    print("CSV Content Preview:")
    print("-" * 20)
    print(csv)
    print("-" * 20)
    
    if len(csv.strip()) == 0:
        print("   [FAIL] CSV string is empty.")
    elif "\n" not in csv and "," not in csv:
        print("   [FAIL] CSV seems malformed.")
    else:
        print("   [OK] CSV generated.")

if __name__ == "__main__":
    test_csv_export()
