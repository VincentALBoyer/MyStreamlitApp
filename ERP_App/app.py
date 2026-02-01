import streamlit as st
import pandas as pd
import random
import logic

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION (PROFESSIONAL & HIGH CONTRAST)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SAP S/4HANA Simulation | ERP Console",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Agnostic High-Contrast Styling (Works in Light & Dark Modes)
st.markdown("""
<style>
    /* === FORCE LIGHT THEME GLOBALLY === */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #f8f9fa !important;
        color: #1a1a1a !important;
    }
    
    /* Force all text elements to dark */
    p, span, div, label, li, h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
    }
    
    /* Header - Deep Navy with White Text */
    .sap-header { 
        background-color: #1c2d3d !important; 
        color: #ffffff !important; 
        padding: 1.5rem; 
        border-bottom: 5px solid #0070f2;
        margin-bottom: 25px;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sap-header h2 { color: #ffffff !important; margin: 0; }
    
    /* Metrics - Force Dark Text */
    [data-testid="stMetricValue"] { 
        color: #1c2d3d !important; 
        font-weight: 800; 
        font-size: 1.8rem; 
    }
    [data-testid="stMetricLabel"] { 
        color: #555555 !important; 
        font-size: 0.9rem; 
    }
    
    /* Containers & Cards - White Background */
    [data-testid="stVerticalBlock"] > div {
        background-color: #ffffff !important;
    }
    .element-container, [data-testid="stMarkdownContainer"] {
        color: #1a1a1a !important;
    }
    
    /* Tables - White Background, Dark Text */
    .stDataFrame, [data-testid="stTable"], table {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        border-radius: 4px;
    }
    .stDataFrame table, .stDataFrame th, .stDataFrame td,
    [data-testid="stTable"] table, [data-testid="stTable"] th, [data-testid="stTable"] td,
    table, th, td {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border-color: #dee2e6 !important;
    }
    
    /* Sidebar - White Background */
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #dee2e6;
    }
    [data-testid="stSidebar"] * { 
        color: #1c2d3d !important; 
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #1c2d3d !important;
    }

    /* Action Buttons - Professional Blue with White Text */
    .stButton > button { 
        border-radius: 2px; 
        height: 3rem; 
        font-weight: 600;
        color: #ffffff !important;
        background-color: #0070f2 !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #0056b3 !important;
        color: #ffffff !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #0070f2 !important;
        color: #ffffff !important;
    }
    .stButton > button:disabled {
        background-color: #e9ecef !important;
        color: #6c757d !important;
    }
    
    /* Input Fields - White Background */
    input, textarea, select, [data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #dee2e6 !important;
    }
    
    /* Number Input */
    [data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
    
    /* Info/Success/Error Boxes */
    [data-testid="stAlert"] {
        background-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if 'game_state' not in st.session_state:
    st.session_state.game_state = logic.GameState()
    state = st.session_state.game_state
    # Init demand
    logic.update_supplier_availability(state)
    d = logic.generate_customer_demand(1)
    logic.create_customer_order(state, d)
    kpis = logic.get_kpis(state)
    logic.save_day_snapshot(state, kpis)

state = st.session_state.game_state

# -----------------------------------------------------------------------------
# CALBACKS & ACTION HANDLERS
# -----------------------------------------------------------------------------
def handle_ship(order_id):
    if logic.ship_specific_order(state, order_id):
        st.toast(f"✅ Order #{order_id} Shipped!", icon="🚚")
    else:
        st.error("Insufficient stock to ship order.")

def handle_ship_all():
    pending = [o for o in state.customer_orders if o.status == "pending"]
    pending.sort(key=lambda x: x.due_date)
    count = 0
    for o in pending:
        if logic.ship_specific_order(state, o.id):
            count += 1
    if count > 0:
        st.toast(f"✅ Batch Shipped {count} orders!", icon="🚀")
    else:
        st.error("Cannot ship any orders. Bulk up inventory.")

def handle_next_day():
    state.daily_events = []
    
    # Advance Logic
    state.current_day += 1
    logic.update_supplier_availability(state)
    state.daily_events.extend(logic.process_supplier_deliveries(state))
    state.daily_events.extend(logic.process_customer_deliveries(state))
    
    # 3. New Demand
    base = logic.generate_customer_demand(state.current_day)
    # Surge logic replication
    if random.random() < 0.15:
        base = int(base * 2.5)
        state.daily_events.append("🚨 MARKET ALERT: Unexpected demand surge detected!")
    
    num_o = random.randint(1, 4)
    for _ in range(num_o):
        qty = max(5, int(base / num_o * random.uniform(0.8, 1.2)))
        logic.create_customer_order(state, qty)
    
    # 4. End-of-Day costs
    logic.calculate_holding_costs(state)
    state.daily_events.extend(logic.calculate_daily_penalties(state))
    
    # Snapshot
    logic.save_day_snapshot(state, logic.get_kpis(state))
    
    if state.current_day >= state.max_days:
        state.game_over = True

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏢 S/4HANA INTERFACE")
    st.divider()
    menu = st.radio("Business Modules", [
        "📊 Executive Cockpit",
        "📦 Warehouse & Shipping",
        "🛒 Procurement Center",
        "📑 Audit Logs"
    ])
    
    st.divider()
    st.subheader("Fiscal Period")
    st.metric("Day", f"{state.current_day} / {state.max_days}")
    st.metric("Liquid Cash", f"${state.cash:,.0f}")
    
    if not state.game_over:
        st.button("➡️ RUN DAILY BATCH", type="primary", use_container_width=True, on_click=handle_next_day)
    else:
        st.error("Month Complete (30 Days)")
        if st.button("🔄 Reset Simulation", use_container_width=True):
            del st.session_state.game_state
            st.rerun()

# -----------------------------------------------------------------------------
# MAIN DASHBOARD
# -----------------------------------------------------------------------------
kpis = logic.get_kpis(state)

if menu == "📊 Executive Cockpit":
    st.markdown("<div class='sap-header'><h2>Management Dashboard</h2></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Financial Profit", f"${kpis['profit']:,.0f}")
    c2.metric("Inventory Volume", kpis['inventory'])
    c3.metric("Service Level (Fill)", f"{kpis['fill_rate']:.1f}%")
    c4.metric("Unshipped Depth", kpis['orders_pending'])
    
    st.divider()
    
    col_plot, col_log = st.columns([2, 1])
    with col_plot:
        st.markdown("### 📈 Performance Trends")
        if state.history:
            df_hist = pd.DataFrame(state.history)
            st.line_chart(df_hist.set_index("day")[["profit", "cash"]], height=300)
    with col_log:
        st.markdown("### 📜 System Notifications")
        with st.container(height=300):
            if state.daily_events:
                for e in reversed(state.daily_events):
                    st.write(e)
            else:
                st.caption("Awaiting first system batch...")

elif menu == "📦 Warehouse & Shipping":
    st.markdown("<div class='sap-header'><h2>Outbound Logistics: Shipping Station</h2></div>", unsafe_allow_html=True)
    
    col_info, col_batch = st.columns([3, 1])
    with col_info:
        st.markdown(f"Available Stock: **{state.inventory} units**")
    with col_batch:
        st.button("🚀 Bulk Ship Available", on_click=handle_ship_all, use_container_width=True, type="primary")

    st.divider()
    
    pending = [o for o in state.customer_orders if o.status == "pending"]
    if not pending:
        st.success("Logistics Clear: No pending orders.")
    else:
        pending.sort(key=lambda x: x.due_date)
        for o in pending:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1.5, 1])
                c1.write(f"**{o.customer.emoji} {o.customer.name}** (#{o.id})")
                c2.write(f"Qty: **{o.quantity}**")
                
                due_in = o.due_date - state.current_day
                color = "#d32f2f" if due_in < 1 else "#ed6c02" if due_in < 3 else "#2e7d32"
                c3.markdown(f"Due: Day {o.due_date} (<span style='color:{color}'>{due_in}d</span>)", unsafe_allow_html=True)
                
                can_ship = state.inventory >= o.quantity
                if c4.button("Post Shipment", key=f"s_{o.id}", disabled=not can_ship, use_container_width=True):
                    handle_ship(o.id)
                    st.rerun()

elif menu == "🛒 Procurement Center":
    st.markdown("<div class='sap-header'><h2>Inbound Logistics: Supplier Market</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### Approved Supplier Network")
    st.info("Orders placed here enter 'In-Transit' immediately.")
    
    sc1, sc2 = st.columns(2)
    suppliers = list(logic.SUPPLIERS.items())
    
    for i, (sid, s) in enumerate(suppliers):
        col = sc1 if i % 2 == 0 else sc2
        with col:
            with st.container(border=True):
                avail = state.supplier_availability.get(sid, {})
                st.markdown(f"#### {s.emoji} {s.name}")
                
                # Show Specs explicitly
                c1, c2 = st.columns(2)
                c1.metric("Min Order", s.min_order)
                c2.metric("Max Capacity", avail.get('max_today', 0))
                
                c3, c4 = st.columns(2)
                c3.metric("Unit Price", f"${s.unit_price}")
                c4.metric("Lead Time", f"{s.lead_time_min}-{s.lead_time_max}d")
                
                if avail.get('available'):
                    order_qty = st.number_input(f"Order Quantity ({sid})", 
                                              min_value=0, max_value=avail['max_today'], 
                                              step=10, key=f"input_{sid}", label_visibility="collapsed")
                    
                    if st.button(f"🛒 Place Order with {s.id}", key=f"btn_{sid}", use_container_width=True):
                        if order_qty >= s.min_order:
                            if logic.place_supplier_order(state, sid, order_qty):
                                st.success(f"Order for {order_qty} units transmitted to {s.name}.")
                                st.rerun()
                            else:
                                st.error("Financial Constraint: Insufficient cash.")
                        else:
                            st.warning(f"Quantity below Minimum Order ({s.min_order}).")
                else:
                    st.error("Supplier Unavailable (Capacity Constraint met).")

    st.divider()
    st.markdown("### 🚛 In-Transit Supply (Active Orders)")
    inc = [o for o in state.supplier_orders if o.status == "in_transit"]
    if inc:
        # Sort by arrival day
        inc_data = [{
            "PO #": o.id, 
            "Vendor": logic.SUPPLIERS[o.supplier_id].name, 
            "Quantity": o.quantity, 
            "Est. Arrival": f"Day {o.expected_arrival}",
            "Status": "On Ship" if (o.expected_arrival - state.current_day) > 2 else "In Port"
        } for o in sorted(inc, key=lambda x: x.expected_arrival)]
        st.table(pd.DataFrame(inc_data))
    else:
        st.caption("No pending supplier deliveries.")

elif menu == "📑 Audit Logs":
    st.markdown("<div class='sap-header'><h2>Regulatory Audit & Data Export</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### Master Data Exports")
    c1, c2 = st.columns(2)
    with c1:
        csv_o = pd.DataFrame([vars(o) for o in state.customer_orders]).to_csv(index=False)
        st.download_button("📥 Export Customer Orders", csv_o, "Audit_Orders.csv")
    with c2:
        csv_s = pd.DataFrame([vars(o) for o in state.supplier_orders]).to_csv(index=False)
        st.download_button("📥 Export Supplier POs", csv_s, "Audit_Suppliers.csv")
    
    st.divider()
    st.markdown("### Historical Performance")
    if state.history:
        st.dataframe(pd.DataFrame(state.history), use_container_width=True, hide_index=True)
