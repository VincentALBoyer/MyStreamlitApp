
import sys
import os
import pandas as pd
import random

# Add path to import logic
sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))
import logic

def run_simulation(run_id, strategy="random"):
    print(f"--- Starting Run {run_id} ({strategy}) ---")
    state = logic.init_game()
    
    # Simple bot loop
    for day in range(1, 31):
        # 1. Place Orders logic
        # Strategy: Keep inventory above 200
        current_inv = state.inventory
        
        # Check projected stock (simple)
        # We don't have perfect visibility in bot, but we access state directly
        if current_inv < 200:
            # Pick a random supplier
            supp = random.choice(state.available_suppliers)
            qty = max(supp.min_order_qty, 300)
            
            # Place order (Open directly as if committed)
            logic.place_order(state, supp.id, qty, status="Open")
        
        # 2. Process Turn
        logic.process_daily_turn(state)
        
        if state.game_over:
            break
            
    print(f"Run {run_id} Complete. Cash: {state.cash}, Stockouts: {state.total_stockout_penalty}")
    
    # Capture Log
    # We want to see the raw dictionary data before it becomes CSV string, 
    # but the function returns CSV string. We can parse it back or just inspect logic.
    # Let's inspect the logic.delivery_log directly for what IS available vs what is EXPORTED.
    
    export_df = pd.DataFrame([
        {
            "Day": d.day_arrived,
            "Supplier": d.supplier_name,
            "Qty_Good": d.qty_received,
            "Qty_Defect": d.qty_defective,
            "Rework_Cost": d.rework_cost,
            "Status": d.status,
            # Attributes present in Object but maybe missing in CSV?
            "Unit_Price_Obj": d.unit_price 
        }
        for d in state.delivery_log
    ])
    
    # Also get the actual CSV string to see what columns are currently valid
    csv_string = logic.get_csv_export(state)
    
    return export_df, csv_string

def main():
    # Run 3 times
    all_runs = []
    for i in range(3):
        df, csv = run_simulation(i+1)
        df['Run_ID'] = i+1
        all_runs.append(df)
        
    final_df = pd.concat(all_runs)
    
    print("\n=== AGGREGATED DATA ANALYSIS ===")
    print(final_df.head())
    print("-" * 30)
    print("Columns in Data Object:", final_df.columns.tolist())
    
    # Check what's actually in the CSV export function
    # We can infer from the csv_string header
    from io import StringIO
    _, csv_string = run_simulation(99) # quick run
    csv_headers = pd.read_csv(StringIO(csv_string)).columns.tolist()
    print("Columns in CURRENT CSV EXPORT:", csv_headers)
    
    # KPI Check
    print("\n=== KPI FEASIBILITY CHECK ===")
    has_price = "Unit_Price" in csv_headers or "Unit Price" in csv_headers
    has_placed_day = "Day Placed" in csv_headers or "Lead Time" in csv_headers
    
    print(f"1. Financial KPI (True Cost): {'POSSIBLE' if has_price else 'MISSING PRICE'}")
    print(f"   (Needs: Unit Price + Rework Cost)")
    
    print(f"2. Quality KPI (Defect Rate): {'POSSIBLE'}")
    print(f"   (Needs: Qty Good + Qty Defect)")
    
    print(f"3. Delivery KPI (Lead Time Var): {'PARTIAL' if 'Status' in csv_headers else 'MISSING'}")
    print(f"   (Current 'Status' column shows 'Late', but calculating specific days late requires 'Day Placed')")

if __name__ == "__main__":
    main()
