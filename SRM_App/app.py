import streamlit as st
import pandas as pd
import altair as alt
import logic

st.set_page_config(page_title="SAP SRM | Advanced Sourcing", page_icon="🏭", layout="wide")

# Styling
st.markdown("""
<style>
    .stApp { background-color: #f5f7f9; }
    .nav-tab { font-weight: bold; }
    .alert-box { padding: 10px; border-radius: 5px; margin-bottom: 5px; font-weight: 500;}
    .alert-red { background-color: #fadbd8; color: #922b21; border: 1px solid #922b21; }
    .alert-green { background-color: #d5f5e3; color: #1e8449; border: 1px solid #1e8449; }
    .metric-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-val { font-size: 1.6rem; font-weight: 800; color: #2c3e50; }
    .metric-lbl { font-size: 0.8rem; text-transform: uppercase; color: #7f8c8d; }
</style>
""", unsafe_allow_html=True)

if 'srm_state' not in st.session_state:
    st.session_state.srm_state = logic.init_game()
    # Default selection removed

state = st.session_state.srm_state

# =============================================================================
# SIDEBAR CONTROLS
# =============================================================================
with st.sidebar:
    st.title("🏭 SAP SRM")
    st.caption("Advanced Procurement Sim")
    st.divider()
    
    menu = st.radio("Module", ["🚀 Procurement Cockpit", "🏭 Sourcing Master", "📅 MRP & Planning"], label_visibility="collapsed")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    c1.metric("Day", f"{state.current_day} / {state.max_days}")
    c2.metric("Cash", f"${state.cash/1000:.1f}k")
    
    if not state.game_over:
        if st.button("➡️ NEXT DAY", type="primary", use_container_width=True):
            logic.process_daily_turn(state)
            st.rerun()
    else:
        st.error("Simulation Ended")
        if st.button("Download Data", type="primary"):
            pass # TODO handled in main

# =============================================================================
# MAIN AREA
# =============================================================================

if menu == "🚀 Procurement Cockpit":
    st.subheader("🚀 Procurement Execution Cockpit")
    
    # 1. KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='metric-card'><div class='metric-val'>{state.inventory}</div><div class='metric-lbl'>Current Stock</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-card'><div class='metric-val'>{len(state.active_pos)}</div><div class='metric-lbl'>Open POs</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-card'><div class='metric-val'>${state.total_rework_cost:,.0f}</div><div class='metric-lbl'>Quality Costs</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-card'><div class='metric-val'>${state.total_stockout_penalty:,.0f}</div><div class='metric-lbl'>Stockout Penalties</div></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # 2. Daily Alerts
    c_alert, c_sched = st.columns([1, 1])
    
    with c_alert:
        st.write("##### 📢 Daily Notifications")
        with st.container(height=300):
            if state.daily_events:
                for ev in reversed(state.daily_events):
                    style = "alert-red" if "STOPPAGE" in ev or "DELAY" in ev or "Defective" in ev else "alert-green"
                    st.markdown(f"<div class='alert-box {style}'>{ev}</div>", unsafe_allow_html=True)
            else:
                st.caption("No recent events.")
                
    with c_sched:
        st.write("##### 📅 Today's Production Target")
        today_demand = state.production_schedule.get(state.current_day, 0)
        
        status_color = "green" if state.inventory >= today_demand else "red"
        st.markdown(f"""
        ### Target: **{today_demand} units**
        ### Available: <span style='color:{status_color}'>{state.inventory} units</span>
        """, unsafe_allow_html=True)
        
        if state.inventory < today_demand:
            st.warning(f"⚠️ RISK: Shortage of {today_demand - state.inventory} units! Line stop imminent.")

    # 3. Inbound Delivery Monitor
    st.write("##### 🚛 Inbound Monitor (Open POs)")
    if state.active_pos:
        po_data = []
        for po in state.active_pos:
            supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
            po_data.append({
                "PO #": po.id,
                "Vendor": supp.name,
                "Qty": po.qty_ordered,
                "Est. Arrival": f"Day {po.expected_arrival_day}",
                "Status": "Processing" if po.status == "Processing" else ("Late" if state.current_day > po.expected_arrival_day else "In Transit")
            })
        st.dataframe(pd.DataFrame(po_data), use_container_width=True)
    else:
        st.info("No active Purchase Orders. Check MRP to place orders.")

elif menu == "📅 MRP & Planning":
    st.subheader("📅 Material Requirements Planning (MRP)")
    
    # 1. The Schedule Chart
    st.write("##### Production Demand Forecast (Next 30 Days)")
    
    sched_df = pd.DataFrame(list(state.production_schedule.items()), columns=["Day", "Demand"])
    # Filter for future only
    sched_df = sched_df[sched_df["Day"] >= state.current_day]
    
    chart = alt.Chart(sched_df).mark_bar().encode(
        x='Day:O',
        y='Demand:Q',
        color=alt.value("#3498db")
    ).properties(height=200)
    st.altair_chart(chart, use_container_width=True)
    
    st.divider()
    
    # 2. Ordering Interface
    st.write("##### 📝 Procurement Desk (Place Orders)")
    
    for supp in state.available_suppliers:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            c1.markdown(f"**{supp.name}**")
            c1.caption(supp.description)
            delta_val = None
            if state.current_day > 1:
                diff = supp.current_price - supp.previous_price
                pct = (diff / supp.previous_price) * 100
                delta_val = f"{pct:+.1f}% vs Yesterday"
            
            c2.metric("Market Price", f"${supp.current_price:.2f}", delta=delta_val, delta_color="inverse")
            c3.metric("Lead Time", f"{supp.quoted_lead_time}d")
            c4.metric("Min Qty", supp.min_order_qty)
            
            # Individual Order Form
            with c5:
                # Unique key for each input to manage state
                qty = st.number_input("Qty", min_value=0, step=50, key=f"qty_{supp.id}", label_visibility="collapsed")
                if st.button("Order", key=f"btn_po_{supp.id}", use_container_width=True):
                    if qty > 0:
                        success, msg = logic.place_order(state, supp.id, qty)
                        if success:
                            st.success(f"Order Sent to {supp.name}")
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter Qty")
        
elif menu == "🏭 Sourcing Master":
    st.subheader("🏭 Supplier Performance Master")
    st.write("Real-time performance tracking. Monitor Actuals vs Promoted Specs.")
    
    for i, s in enumerate(state.available_suppliers):
        stats = logic.get_supplier_stats(state, s.id)
        
        with st.container(border=True):
            c_head, c_kpi = st.columns([1, 3])
            
            with c_head:
                st.markdown(f"### {s.name}")
                st.caption(s.category)
                st.write(f"_{s.description}_")
                
                st.caption(s.category)
                # Description is already shown below or above, removing duplicate here if it exists or consolidating.
                # Actually, looking at the file, line 174 is likely the st.caption(f"_{s.description}_") added recently.
                # The line 172 `st.write(f"_{s.description}_")` is the first one. 
                # I will remove the one at line 174.

            with c_kpi:
                # Comparison Grid
                k1, k2, k3, k4 = st.columns(4)
                
                # PRICE
                # Overall variation vs Start (Quoted)
                diff = s.current_price - s.quoted_price
                pct = (diff / s.quoted_price) * 100
                delta_val = f"{pct:+.1f}% vs Quote"
                
                k1.metric("Current Price", f"${s.current_price:.2f}", delta=delta_val, delta_color="inverse")
                
                # LEAD TIME
                k2.metric("Quoted Lead Time", f"{s.quoted_lead_time}d", help="Promised Delivery Speed")
                
                # DEFECTS (Actual vs Predicted)
                if stats['has_history']:
                    val = f"{stats['defect_rate']:.1f}%"
                    delta = -stats['defect_rate'] # Negative delta is bad (red) - wait, st.metric delta colors: Positive is Up (Green). 
                    # We want Low Defect = Green.
                    # If we use delta_color="inverse", positive delta is Good (Green)? No, inverse means positive is Bad (Red).
                    # Let's just use color formatting or simple metric.
                    k3.metric("Actual Defect Rate", val, delta=None) 
                else:
                    k3.metric("Defect Rate", "N/A", "No History")

                # RELIABILITY
                if stats['has_history']:
                    val = f"{stats['reliability']:.0f}%"
                    # reliability < 90 is bad. 
                    delta = stats['reliability'] - 100 # Gap to perfection
                    k4.metric("On-Time Rate", val, f"{stats['deliveries']} deliveries")
                else:
                    k4.metric("On-Time Rate", "N/A", "No History")
                
                st.divider()
                # Financial Impact
                if stats['has_history']:
                    c_fin, c_min = st.columns(2)
                    c_fin.markdown(f"**Total Rework Cost**: :red[${stats['total_rework']:,.0f}]")
                    c_min.markdown(f"Min Order Qty: **{s.min_order_qty}**")
                else:
                     st.caption("Place orders to generate performance data.")

# Footer Analysis
if state.game_over:
    with st.expander("🏁 End of Game Analysis", expanded=True):
        st.write(f"### Final Cash: ${state.cash:,.0f}")
        csv = logic.get_csv_export(state)
        st.download_button("📥 Download Transaction Log", csv, "srm_mrp_data.csv")
