import streamlit as st
import pandas as pd
import numpy as np
import random
from game_engine import (
    GameState, SUPPLIERS, generate_customer_demand, create_customer_order,
    ship_specific_order, place_supplier_order, update_supplier_availability,
    process_supplier_deliveries, process_customer_deliveries, calculate_holding_costs,
    calculate_daily_penalties, get_kpis, save_day_snapshot, generate_market_event,
    update_events
)

# Page Conf
st.set_page_config(
    page_title="ERP Sim",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Styling
st.markdown("""
<style>
    /* Increase top padding to prevent content from being cut off */
    .block-container { padding-top: 4rem; padding-bottom: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .supplier-card { 
        padding: 5px; 
        border: 1px solid #ddd; 
        border-radius: 5px; 
        margin-bottom: 5px; 
        font-size: 0.9rem;
    }
    .compact-table { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# State Init
if 'game_state' not in st.session_state:
    st.session_state.game_state = GameState()
    update_supplier_availability(st.session_state.game_state)
    d = generate_customer_demand(1)
    create_customer_order(st.session_state.game_state, d)
    kpis = get_kpis(st.session_state.game_state)
    save_day_snapshot(st.session_state.game_state, kpis)

state = st.session_state.game_state

# --- Logic Handlers ---

if 'action_ship' in st.session_state:
    oid = st.session_state.action_ship
    if ship_specific_order(state, oid):
        st.toast(f"✅ Order #{oid} Shipped!", icon="🚚")
    else:
        st.toast("❌ Shipping Failed (Check stock)", icon="🚫")
    del st.session_state.action_ship

# --- UI Layout ---

# Top Bar: Info & KPIs
kpis = get_kpis(state)

# Row 1: Header & Controls
h1, h2 = st.columns([0.7, 0.3])
with h1:
    st.markdown(f"### 🏭 **ERP Sim** | Day {state.current_day}/{state.max_days}")
with h2:
    if state.game_over:
        st.error(f"Profit: ${kpis['profit']:,.0f}")
        if st.button("Restart", use_container_width=True):
            del st.session_state.game_state
            st.rerun()
    else:
        if st.button("➡️ NEXT DAY", type="primary", use_container_width=True):
            # 1. Place Orders
            daily_logs = []
            for sid, supplier in SUPPLIERS.items():
                qty_key = f"ord_{sid}"
                qty = st.session_state.get(qty_key, 0)
                if qty > 0:
                    if place_supplier_order(state, sid, qty):
                        msg = f"🛒 Ordered {qty} from {supplier.name}"
                        daily_logs.append(msg)
                        st.toast(msg, icon="✅")
                    else:
                        msg = f"❌ Order failed: {supplier.name} (Check Cash/Min Order)"
                        daily_logs.append(msg)
                        st.toast(msg, icon="🚫")
                st.session_state[qty_key] = 0 # Reset
            
            state.daily_events = daily_logs
            
            # 2. Advance
            state.current_day += 1
            update_supplier_availability(state)
            
            # Events
            state.daily_events.extend(update_events(state))
            new_evt = generate_market_event(state)
            if new_evt: state.daily_events.append(new_evt)
            
            state.daily_events.extend(process_supplier_deliveries(state))
            state.daily_events.extend(process_customer_deliveries(state))
            
            # 3. New Demand (Multiple Orders & Heavy Demand Stress)
            base_demand = generate_customer_demand(state.current_day, state.active_events)
            
            # Stress Event: Heavy Demand (15% chance)
            is_heavy = random.random() < 0.15
            if is_heavy:
                base_demand = int(base_demand * 2.5)
                state.daily_events.append("🚨 HEAVY DEMAND SURGE! Orders spiking!")
            
            num_orders = random.randint(2, 5) if is_heavy else random.randint(1, 3)
            
            for _ in range(num_orders):
                # Ensure minimum order size
                qty = max(5, int(base_demand / num_orders * random.uniform(0.8, 1.2)))
                new_o = create_customer_order(state, qty)
                state.daily_events.append(f"🛍️ New Order: {new_o.customer.name} ({qty} units)")
            
            # 4. Costs & Penalties
            h_cost = calculate_holding_costs(state)
            if h_cost > 0: state.daily_events.append(f"Holding Cost: -${h_cost:.0f}")
            
            # Daily Penalties (>24h late)
            pen_events = calculate_daily_penalties(state)
            state.daily_events.extend(pen_events)
            
            # Snapshot
            save_day_snapshot(state, get_kpis(state))
            
            if state.current_day >= state.max_days: state.game_over = True
            
            st.rerun()

# Row 2: Metrics
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💰 Profit", f"${kpis['profit']:,.0f}")
m2.metric("💵 Cash", f"${kpis['cash']:,.0f}")
inv_delta = f"{kpis['inventory']}/{state.warehouse_capacity}"
m3.metric("📦 Inventory", inv_delta, 
    delta="Over Capacity" if kpis['inventory'] > state.warehouse_capacity else None,
    delta_color="inverse")
m4.metric("⏳ Orders", f"{kpis['orders_pending']}")
m5.metric("🚚 Inbound", f"{kpis['incoming_qty']}")

st.divider()

# Split Layout: Main Tabs (Left) | Info Pane (Right)
# Split Layout: Main Tabs (Left) | Info Pane (Right)
main_tabs, info_pane = st.columns([2.5, 1])

with info_pane:
    # 0. MARKET NEWS
    st.markdown("##### 📰 Market News")
    if state.active_events:
        for event in state.active_events:
            with st.container(border=True):
                st.markdown(f"**{event.name}**")
                st.caption(f"{event.description}")
                st.caption(f"Ends in: {event.duration} days")
    else:
        st.info("No active market events.")
    
    st.divider()

with main_tabs:
    # TABS: Shipping | Procurement | Stats
    tab_ship, tab_proc, tab_stats = st.tabs(["📤 Shipping Station", "🛒 Procurement", "📊 Statistics"])
    
    with tab_ship:
        c1, c2 = st.columns([3, 1])
        c1.subheader("Pending Orders")
        
        # Ship All Button Logic
        pending_orders = [o for o in state.customer_orders if o.status == "pending"]
        
        # Ship All
        if c2.button("🚀 Ship All Available", disabled=len(pending_orders)==0 or state.game_over, type="primary"):
            shipped_count = 0
            # Sort by urgency to prioritize
            pending_orders.sort(key=lambda x: x.due_date)
            for o in pending_orders:
                if state.inventory >= o.quantity:
                    state.inventory -= o.quantity
                    o.quantity_fulfilled = o.quantity
                    o.status = "in_transit"
                    o.day_shipped = state.current_day
                    o.expected_delivery = state.current_day + o.delivery_time
                    shipped_count += 1
            if shipped_count > 0:
                st.toast(f"✅ Batch Shipped {shipped_count} orders!", icon="🚀")
                st.rerun()
            else:
                st.toast("❌ Not enough stock for any order!", icon="🚫")
        
        if pending_orders:
            pending_orders.sort(key=lambda x: x.due_date)
            for o in pending_orders:
                due_in = o.due_date - state.current_day
                urgency_color = "red" if due_in < 1 else "orange" if due_in < 3 else "green"
                
                with st.container(border=True):
                    oc1, oc2, oc3, oc4, oc5 = st.columns([0.5, 2, 1, 1.5, 1])
                    oc1.write(f"#{o.id}")
                    oc2.write(f"**{o.customer.emoji} {o.customer.name}**")
                    oc3.write(f"**{o.quantity}** units")
                    oc4.markdown(f"Due: **Day {o.due_date}** (:<span style='color:{urgency_color}'>{due_in} days</span>)", unsafe_allow_html=True)
                    
                    can_ship = state.inventory >= o.quantity
                    if oc5.button("Ship", key=f"ship_{o.id}", disabled=not can_ship or state.game_over):
                        st.session_state.action_ship = o.id
                        st.rerun()
        else:
            st.success("✅ All orders shipped! Good job.")

    with tab_proc:
        st.subheader("Supplier Market")
        sc1, sc2, sc3, sc4 = st.columns(4)
        suppliers = list(SUPPLIERS.values())
        for i, col in enumerate([sc1, sc2, sc3, sc4]):
            s = suppliers[i]
            avail = state.supplier_availability.get(s.id, {})
            is_av = avail.get('available', True)
            with col:
                with st.container(border=True):
                    # Check for disruption
                    is_disrupted = False
                    delay_txt = ""
                    for e in state.active_events:
                        if e.type == "supply" and (e.target_id == s.id or e.target_id is None):
                            is_disrupted = True
                            delay_txt = f"+{e.magnitude}d delay"
                    
                    st.markdown(f"**{s.emoji} {s.name}**")
                    if is_disrupted:
                        st.markdown(f":red[**⚠️ {delay_txt}**]")
                    st.caption(f"${s.unit_price} | {s.lead_time_min}-{s.lead_time_max}d")
                    if is_av:
                        max_q = avail['max_today']
                        st.number_input("Qty", min_value=0, max_value=max_q, step=10, key=f"ord_{s.id}", label_visibility="collapsed")
                        st.caption(f"Max: {max_q}")
                    else:
                        st.error("Unavailable")
    
    with tab_stats:
        st.subheader("Performance Analytics")
        if len(state.history) > 0:
            hist_df = pd.DataFrame(state.history)
            st.markdown("##### 💵 Financial Trends")
            st.line_chart(hist_df.set_index("day")[["cash", "profit"]], height=250)
            st.markdown("##### 📦 Inventory Levels")
            st.line_chart(hist_df.set_index("day")[["inventory"]], height=250)
        else:
            st.info("Play a few turns to generate data.")

with info_pane:
    # 1. INCOMING SUPPLY
    st.info("📥 **Incoming Supply**")
    inc = [o for o in state.supplier_orders if o.status == "in_transit"]
    if inc:
        inc_df = pd.DataFrame([{
            "Sup": o.supplier_id, "Qty": o.quantity, "Arr": f"Day {o.expected_arrival}"
        } for o in inc])
        st.dataframe(inc_df, hide_index=True, use_container_width=True, height=250)
    else:
        st.caption("No incoming shipments")
        
    st.divider()
    
    # 2. ACTIVITY LOG
    st.warning("📜 **Recent Activity**")
    with st.container(height=400):
        if state.daily_events:
            for e in reversed(state.daily_events):
                st.text(e)
        else:
            st.caption("No events yet.")
