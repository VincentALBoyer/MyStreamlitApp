import streamlit as st
import pandas as pd
import logic

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="SAP SRM | Supplier Management Console",
    page_icon="🏬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Agnostic High-Contrast Styling
st.markdown("""
<style>
    /* === FORCE LIGHT THEME GLOBALLY === */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #f8f9fa !important;
        color: #1a1a1a !important;
    }
    
    p, span, div, label, li, h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
    }
    
    /* Header - Corporate Teal with White Text */
    .srm-header { 
        background-color: #006064 !important; 
        color: #ffffff !important; 
        padding: 1.5rem; 
        border-bottom: 5px solid #00acc1;
        margin-bottom: 25px;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .srm-header h2 { color: #ffffff !important; margin: 0; }
    
    /* Metrics */
    [data-testid="stMetricValue"] { 
        color: #006064 !important; 
        font-weight: 800; 
        font-size: 1.8rem; 
    }
    [data-testid="stMetricLabel"] { 
        color: #555555 !important; 
        font-size: 0.9rem; 
    }
    
    /* Action Buttons */
    .stButton > button { 
        border-radius: 2px; 
        height: 3rem; 
        font-weight: 600;
        color: #ffffff !important;
        background-color: #006064 !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #004d40 !important;
        color: #ffffff !important;
    }
    
    /* Alerts and Overlays */
    [data-testid="stAlert"], [data-testid="stNotification"], [role="listbox"], [role="option"] {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #dee2e6 !important;
    }
    
    /* Table Styling */
    .stDataFrame table, .stDataFrame th, .stDataFrame td {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'srm_state' not in st.session_state:
    st.session_state.srm_state = logic.GameState()
    state = st.session_state.srm_state
    state.suppliers = logic.init_supplier_network()
    
    # Pre-populate some contracts
    for sid in ["VEND-001", "VEND-002", "VEND-005"]:
        vendor = state.suppliers[sid]
        logic.award_contract(state, sid, vendor.category)
        state.cash += 5000 # Neutralize setup cost for start

state = st.session_state.srm_state

# =============================================================================
# CALLBACKS
# =============================================================================
def handle_next_day():
    logic.process_daily_batch(state)

def handle_sourcing(category):
    logic.generate_sourcing_event(state, category)

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### 🏬 SRM CONSOLE")
    st.divider()
    menu = st.radio("Management Modules", [
        "📊 Portfolio Analytics",
        "🎯 Strategic Sourcing",
        "📑 Contract Master",
        "🎖️ Quality Scorecards",
        "🌍 Risk Management"
    ])
    
    st.divider()
    st.subheader("Sim Period")
    st.metric("Period Day", f"{state.current_day} / {state.max_days}")
    st.metric("Procurement Budget", f"${state.cash:,.0f}")
    
    if not state.game_over:
        st.button("➡️ PROCESS DAILY BATCH", type="primary", use_container_width=True, on_click=handle_next_day)
    else:
        st.error("Month End Processed")
        if st.button("🔄 Reset SRM Simulation", use_container_width=True):
            del st.session_state.srm_state
            st.rerun()

# =============================================================================
# DASHBOARD LOGIC
# =============================================================================
kpis = logic.get_kpis(state)

if menu == "📊 Portfolio Analytics":
    st.markdown("<div class='srm-header'><h2>Supplier Portfolio Analytics</h2></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Network Quality", f"{kpis['avg_quality']:.1f}%")
    c2.metric("Reliability Rate", f"{kpis['reliability_rate']:.1f}%")
    c3.metric("Active Contracts", kpis['active_contracts'])
    c4.metric("Risk Incidents", kpis['risk_events'])
    
    st.divider()
    
    col_log, col_suppliers = st.columns([1, 2])
    
    with col_log:
        st.markdown("### 📜 Market Intelligence")
        with st.container(height=350):
            if state.daily_events:
                for e in reversed(state.daily_events):
                    st.write(e)
            else:
                st.caption("Scanning market data...")
                
    with col_suppliers:
        st.markdown("### 🏬 Supplier Network Status")
        sup_data = [{
            "Vendor": s.name,
            "Category": s.category,
            "Quality": f"{s.quality_score}%",
            "Reliability": f"{s.reliability}%",
            "Risk": s.risk_level
        } for s in state.suppliers.values()]
        st.dataframe(pd.DataFrame(sup_data), use_container_width=True, hide_index=True)

elif menu == "🎯 Strategic Sourcing":
    st.markdown("<div class='srm-header'><h2>Strategic Sourcing Center</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### 🏆 Run New RFP (Request for Proposal)")
    cat = st.selectbox("Select Procurement Category", ["Raw Materials", "Logistics", "Components"])
    
    if st.button(f"Generate Bids for {cat}", use_container_width=True):
        handle_sourcing(cat)
        
    if state.available_bids:
        st.divider()
        st.markdown(f"### 📋 Comparison of Bids: {cat}")
        
        for bid in state.available_bids:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                col1.write(f"**{bid.supplier_name}**")
                col2.metric("Setup Cost", f"${bid.proposed_cost:,.0f}")
                col3.metric("Quality Commit", f"{bid.quality_commitment}%")
                col4.metric("Lead Time", f"{bid.guaranteed_lead_time}d")
                
                if st.button(f"Award Contract to {bid.supplier_name}", key=bid.id):
                    if logic.award_contract(state, bid.id, cat):
                        st.success("Contract Awarded! Redirecting to Portfolio...")
                        st.rerun()
                    else:
                        st.error("Insufficient budget for setup.")

elif menu == "📑 Contract Master":
    st.markdown("<div class='srm-header'><h2>Global Contract Master</h2></div>", unsafe_allow_html=True)
    
    if state.contracts:
        for contract in state.contracts:
            vendor = state.suppliers.get(contract.supplier_id)
            if vendor:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**Contract ID #{contract.id}**")
                    c1.write(f"Vendor: {vendor.name} ({contract.category})")
                    c2.write(f"Effective From: Day {contract.start_day}")
                    c2.write(f"Daily Cost Allocation: **${contract.terms_cost * 0.05:,.2f}**")
                    status = "✅ Active" if contract.is_active else "🚫 Terminated"
                    c3.markdown(f"**Status: {status}**")
    else:
        st.info("No active procurement contracts.")

elif menu == "🎖️ Quality Scorecards":
    st.markdown("<div class='srm-header'><h2>Supplier Quality Scorecards</h2></div>", unsafe_allow_html=True)
    
    for s in state.suppliers.values():
        with st.expander(f"Performance Review: {s.name}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Compliance Rate", f"{(s.on_time_deliveries/s.deliveries_completed*100 if s.deliveries_completed > 0 else 100):.1f}%")
            c2.metric("Quality Index", f"{s.quality_score}%")
            c3.metric("Lead Time Variance", "±0.2d")
            
            st.divider()
            st.write(f"**Historical Deliveries**: {s.deliveries_completed}")
            st.write(f"**On-Time Hit Rate**: {s.on_time_deliveries}")
            
            if s.quality_score < 70:
                st.warning("Quality Score below threshold! Issue Improvement Notice.")

elif menu == "🌍 Risk Management":
    st.markdown("<div class='srm-header'><h2>Supply Chain Risk Management</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### 🛡️ Risk Profile")
    
    risk_counts = {"Low": 0, "Med": 0, "High": 0}
    for s in state.suppliers.values():
        risk_counts[s.risk_level] += 1
        
    c1, c2, c3 = st.columns(3)
    c1.metric("Low Risk Vendors", risk_counts["Low"])
    c2.metric("Medium Risk Exposure", risk_counts["Med"])
    c3.metric("High Vulnerability", risk_counts["High"])
    
    st.divider()
    st.markdown("### ⚠️ Critical Alerts")
    critical = [s for s in state.suppliers.values() if s.quality_score < 65 or s.reliability < 70]
    if critical:
        for s in critical:
            st.error(f"VENDOR AT RISK: {s.name} - Reliability critical ({s.reliability}%)")
    else:
        st.success("No critical vendor risks detected.")
