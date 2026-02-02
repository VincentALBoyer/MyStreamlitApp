import streamlit as st
import pandas as pd
import logic

st.set_page_config(page_title="ERP Sim | Enterprise Management", page_icon="🏭", layout="wide")

# Styling
st.markdown("""
<style>
    .stApp { background-color: #fce4ec; } /* Light pink/red tint for ERP distinction */
    .metric-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-green { background-color: #d5f5e3; color: #1e8449; }
    .badge-yellow { background-color: #fcf3cf; color: #b7950b; }
    .badge-red { background-color: #fadbd8; color: #922b21; }
</style>
""", unsafe_allow_html=True)

if 'erp_state' not in st.session_state:
    st.session_state.erp_state = logic.init_game()

state = st.session_state.erp_state

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.title("🏭 ERP Sim")
    st.caption("Enterprise Resource Planning")
    st.divider()
    
    menu = st.radio("Module", [
        "📊 Dashboard", 
        "📦 Sales & Shipping",
        "🏭 Production", 
        "🛒 Purchasing", 
        "💰 Finance"
    ])
    
    st.divider()
    st.metric("Day", f"{state.current_day} / {state.max_days}")
    st.metric("Bank Balance", f"${state.cash:,.2f}")
    
    if not state.game_over:
        if st.button("➡️ NEXT DAY", type="primary", use_container_width=True):
            logic.process_daily_turn(state)
            st.rerun()
    else:
        st.error("GAME OVER")
        
        # LOG EXPORT
        csv = logic.get_csv_export(state)
        st.download_button("📥 Download Log", csv, "erp_simulation_log.csv", "text/csv", use_container_width=True)
        
        if st.button("🔄 Reset"):
            del st.session_state.erp_state
            st.rerun()

# =============================================================================
# MAIN CONTENT
# =============================================================================

if menu == "📊 Dashboard":
    st.subheader("📊 Executive Dashboard")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    
    open_orders = len([o for o in state.sales_orders if o.status == "Open"])
    wip_orders = len([w for w in state.work_orders if w.status == "InProgress"])
    stock_value = sum(qty * state.materials[mid].cost for mid, qty in state.stock_materials.items())
    
    k1.metric("Open Orders", open_orders)
    k2.metric("WIP Jobs", wip_orders)
    k3.metric("Raw Material Value", f"${stock_value:,.0f}")
    k4.metric("Cash", f"${state.cash:,.0f}")
    
    st.divider()
    
    # Inventory Quick View
    st.write("##### 📦 Current Inventory Levels")
    c_raw, c_fin = st.columns(2)
    
    with c_raw:
        st.caption("🧱 Raw Materials")
        raw_data = [{"Item": state.materials[m].name, "Qty": q} for m, q in state.stock_materials.items()]
        st.dataframe(pd.DataFrame(raw_data), use_container_width=True, hide_index=True)
        
    with c_fin:
        st.caption("🚲 Finished Goods")
        fin_data = [{"Item": state.products[p].name, "Qty": q} for p, q in state.stock_finished.items()]
        st.dataframe(pd.DataFrame(fin_data), use_container_width=True, hide_index=True)

    st.divider()
    
    # Log
    st.write("##### 📝 Daily Activity Log")
    with st.container(height=300):
        if state.daily_logs:
            for log in reversed(state.daily_logs):
                st.write(f"- {log}")
        else:
            st.caption("No recent activity.")

elif menu == "📦 Sales & Shipping":
    st.subheader("📦 Sales Order Management")
    st.caption("Fulfill customer demand. Ship orders to generate revenue.")
    
    # Inventory Check
    st.write("##### Finished Goods Inventory")
    cols = st.columns(len(state.products))
    for i, (pid, qty) in enumerate(state.stock_finished.items()):
        prod = state.products[pid]
        cols[i].metric(prod.name, f"{qty} units", help=f"Price: ${prod.price}")
    
    st.divider()
    
    # Order List
    st.write("##### 📋 Open Orders")
    open_orders = [o for o in state.sales_orders if o.status == "Open"]
    
    if not open_orders:
        st.success("All orders shipped! Good job.")
    else:
        for order in open_orders:
            prod = state.products[order.product_id]
            is_overdue = state.current_day > order.due_day
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
                c1.markdown(f"**{order.customer_name}**")
                c1.caption(f"Order #{order.id}")
                
                c2.write(f"{order.qty}x {prod.name}")
                
                due_color = "red" if is_overdue else "green"
                c3.markdown(f"Due: <span style='color:{due_color}'>Day {order.due_day}</span>", unsafe_allow_html=True)
                
                val = order.qty * order.unit_price
                c4.write(f"${val:,.0f}")
                
                # Check Availability
                in_stock = state.stock_finished.get(order.product_id, 0)
                can_ship = in_stock >= order.qty
                
                if can_ship:
                    if c5.button("🚀 SHIP", key=f"ship_{order.id}", type="primary"):
                        success, msg = logic.ship_order(state, order.id)
                        if success:
                            st.toast(f"Shipped to {order.customer_name}!")
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    c5.button("⏳ Short", disabled=True, key=f"no_ship_{order.id}")

elif menu == "🏭 Production":
    st.subheader("🏭 Factory Floor")
    st.caption(f"Capacity: {state.daily_capacity_hours} hrs/day")
    
    # 1. Create Work Order
    st.write("##### 🔨 Schedule Production")
    with st.form("new_wo"):
        c1, c2, c3 = st.columns(3)
        prod_choice = c1.selectbox("Product", list(state.products.keys()), format_func=lambda x: state.products[x].name)
        qty = c2.number_input("Quantity", min_value=1, value=5)
        
        # Show Requirements
        prod = state.products[prod_choice]
        req_str = ", ".join([f"{q*qty}x {state.materials[m].name}" for m, q in prod.bom.items()])
        c3.caption(f"Requires: {req_str}")
        c3.caption(f"Time: {prod.production_hours * qty} hours")
        
        submitted = st.form_submit_button("Start Production")
        if submitted:
            success, msg = logic.create_work_order(state, prod_choice, qty)
            if success:
                st.success(f"Work Order Created! {msg}")
                st.rerun()
            else:
                st.error(msg)
    
    st.divider()
    
    # 2. Work In Progress
    st.write("##### ⚙️ Work In Progress")
    wip = [w for w in state.work_orders if w.status == "InProgress"]
    
    if not wip:
        st.info("Floor is quiet.")
    else:
        # Calculate total load
        total_backlog = sum(w.hours_required - w.hours_completed for w in wip)
        st.progress(min(1.0, total_backlog / (state.daily_capacity_hours * 5)), text=f"Backlog Load: {total_backlog} hours")
        
        for wo in wip:
            prod = state.products[wo.product_id]
            pct = wo.hours_completed / wo.hours_required
            st.write(f"**{prod.name}** ({wo.qty} units)")
            st.progress(pct, text=f"{int(pct*100)}% ({wo.hours_completed}/{wo.hours_required} hrs)")

elif menu == "🛒 Purchasing":
    st.subheader("🛒 Procurement (MRP)")
    st.caption("Buy raw materials to ensure production continuity.")
    
    # 1. Inventory View
    st.write("##### 🧱 Raw Material Inventory")
    inv_cols = st.columns(len(state.materials))
    for i, (mid, mat) in enumerate(state.materials.items()):
        qty = state.stock_materials.get(mid, 0)
        with inv_cols[i]:
            st.metric(mat.name, f"{qty} {mat.unit}", f"${mat.cost}/u")
            
            # Quick Buy
            with st.popover(f"Buy {mat.name}"):
                buy_qty = st.number_input("Qty", min_value=10, step=10, key=f"buy_{mid}")
                if st.button("Order", key=f"btn_buy_{mid}"):
                    success, msg = logic.buy_material(state, mid, buy_qty)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()
    
    # 2. Inbound Orders
    st.write("##### 🚛 Inbound Deliveries")
    inbound = [p for p in state.purchase_orders if p.status == "OnOrder"]
    if inbound:
        data = [{
            "Material": state.materials[p.material_id].name,
            "Qty": p.qty,
            "Arrival": f"Day {p.arrival_day}",
            "Cost": f"${p.qty * p.unit_cost:.0f}"
        } for p in inbound]
        st.table(data)
    else:
        st.caption("No incoming shipments.")

elif menu == "💰 Finance":
    st.subheader("💰 Financial Statement")
    
    # Simple P&L
    
    # Calculate Revenue
    revenue = sum(o.qty * o.unit_price for o in state.sales_orders if o.status == "Shipped")
    
    # Calculate COGS (Standard Cost)
    # Estimate based on shipped items
    cogs = 0
    shipped = [o for o in state.sales_orders if o.status == "Shipped"]
    for o in shipped:
        prod = state.products[o.product_id]
        # Sum material costs
        mat_cost = sum(state.materials[m].cost * q for m, q in prod.bom.items())
        cogs += mat_cost * o.qty
        
    gross_margin = revenue - cogs
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", f"${revenue:,.0f}")
    c2.metric("COGS (Est)", f"${cogs:,.0f}")
    
    delta_color = "normal" if gross_margin >= 0 else "inverse"
    c3.metric("Gross Profit", f"${gross_margin:,.0f}", delta_color=delta_color)

