
import sys
import os
import random

sys.path.append(os.path.join(os.getcwd(), 'SRM_App'))
import logic

def test_price_variation():
    print("1. Initializing Game...")
    state = logic.init_game()
    
    # Check initial state
    s_vol = next(s for s in state.available_suppliers if s.id == "V-VOL")
    print(f"   - {s_vol.name} Initial Price: ${s_vol.current_price:.2f} (Quote: ${s_vol.quoted_price})")
    assert s_vol.current_price == s_vol.quoted_price
    
    print("2. Simulating 10 Days of Fluctuation...")
    prices = []
    for i in range(10):
        logic.process_daily_turn(state)
        prices.append(s_vol.current_price)
        print(f"   - Day {state.current_day}: ${s_vol.current_price:.2f}")
        
    # Verify variance
    variance = max(prices) - min(prices)
    print(f"   - Max Price: ${max(prices):.2f}")
    print(f"   - Min Price: ${min(prices):.2f}")
    print(f"   - Spread: ${variance:.2f}")
    
    assert variance > 0 or s_vol.true_price_volatility == 0
    if variance > 0:
        print("✅ Price Fluctuation Confirmed")
    else:
        print("⚠️ Warning: No fluctuation detected (bad luck?)")

    print("✅ TEST PASSED")

if __name__ == "__main__":
    test_price_variation()
