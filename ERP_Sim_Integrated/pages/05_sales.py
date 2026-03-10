# =============================================================================
# Page 05 — Sales
# ERP-only: manual order inbox + ship button
# CRM enabled: full pipeline kanban, campaigns, customer 360, service tickets
# =============================================================================
import streamlit as st
import pandas as pd
from engine.erp_engine import ship_sales_order
from engine.crm_engine import (advance_lead_stage, run_marketing_campaign,
                                 create_service_ticket, resolve_ticket,
                                 compute_customer_health, get_crm_kpis, STAGE_ORDER)

state = st.session_state.sim_state

st.markdown("""
<div class='page-header'>
    <h2>📈 Sales</h2>
    <p>Manage customer orders — manual entry or full CRM pipeline</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# ===  ERP-ONLY MANUAL SALES MODE  ===========================================
# =============================================================================
if not state.crm_enabled:
    st.markdown("""
    <div class='alert-amber'>
    <b>📭 Manual Sales Mode (ERP Only)</b><br>
    CRM is disabled. Customer orders arrive via email/phone (shown below and in Inbox).
    You must review each open order and ship manually when stock is available.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    # ── Finished Goods Availability ───────────────────────────────────────────
    st.markdown("<div class='section-title'>🚲 Finished Goods Availability</div>", unsafe_allow_html=True)
    cols = st.columns(len(state.products))
    for i, (pid, prod) in enumerate(state.products.items()):
        qty = state.stock_finished.get(pid, 0)
        demand = sum(so.qty for so in state.sales_orders if so.product_id == pid and so.status == "Open")
        cols[i].metric(prod.name, f"{qty} units",
                       delta=f"Need {demand}" if demand > qty else f"+{qty - demand} surplus",
                       delta_color="inverse" if demand > qty else "normal")

    st.divider()

    # ── Open Orders ────────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>📋 Customer Orders — Pending Shipment</div>", unsafe_allow_html=True)
    open_orders = [so for so in state.sales_orders if so.status == "Open"]
    open_orders_sorted = sorted(open_orders, key=lambda x: x.due_day)

    if not open_orders_sorted:
        st.success("✅ All orders processed! Good job.")
    else:
        for so in open_orders_sorted:
            prod = state.products[so.product_id]
            is_rush = so.due_day - so.day_placed <= 2
            is_late = state.current_day > so.due_day
            in_stock = state.stock_finished.get(so.product_id, 0)
            can_ship = in_stock >= so.qty

            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1, 1, 1, 1])

                c1.markdown(f"{'🔴 RUSH — ' if is_rush else ''}**{so.customer_name}**")
                c1.caption(f"Order {so.id} | Day {so.day_placed}")

                c2.write(f"{so.qty}× {prod.name}")
                c2.caption(f"${so.qty * so.unit_price:,.0f}")

                due_html = f"<span style='color:{'red' if is_late else 'green'};font-weight:700'>Due D{so.due_day}</span>"
                c3.markdown(f"**Due:** {due_html}", unsafe_allow_html=True)
                if is_late:
                    c3.caption(f"⚠️ {state.current_day - so.due_day}d late")

                c4.metric("In Stock", in_stock)

                if can_ship:
                    if c6.button("🚀 SHIP", key=f"ship_{so.id}", type="primary"):
                        ok, msg = ship_sales_order(state, so.id)
                        if ok:
                            st.toast(f"✅ Shipped to {so.customer_name}!")
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    c6.button(f"⏳ Short {so.qty - in_stock}", disabled=True, key=f"wait_{so.id}")

    # ── Shipped orders summary ────────────────────────────────────────────────
    st.divider()
    shipped = [so for so in state.sales_orders if so.status == "Shipped"]
    cancelled = [so for so in state.sales_orders if so.status == "Cancelled"]
    cols_s = st.columns(3)
    cols_s[0].metric("Shipped Today", len([s for s in shipped if s.shipped_day == state.current_day - 1]))
    cols_s[1].metric("Total Shipped", len(shipped))
    cols_s[2].metric("Lost / Cancelled", len(cancelled))


# =============================================================================
# ===  CRM MODULE — FULL PIPELINE  ===========================================
# =============================================================================
else:
    crm_kpis = get_crm_kpis(state)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Pipeline Value", crm_kpis["Pipeline Value"])
    k2.metric("Win Rate", crm_kpis["Win Rate %"])
    k3.metric("Active Customers", crm_kpis["Active Customers"])
    k4.metric("Avg CSAT", crm_kpis["Average CSAT"])
    k5.metric("Open Tickets", crm_kpis["Open Tickets"])

    tab_pipeline, tab_orders, tab_campaigns, tab_customers, tab_service = st.tabs([
        "🎯 Pipeline", "📦 Sales Orders", "📢 Campaigns", "👥 Customers", "🎫 Service"
    ])

    # ── Pipeline Kanban ───────────────────────────────────────────────────────
    with tab_pipeline:
        st.markdown("<div class='section-title'>Sales Pipeline — Opportunity Management</div>",
                    unsafe_allow_html=True)
        st.info("Move leads through stages. Won deals auto-create ERP Sales Orders.")

        active_leads = [l for l in state.leads if l.stage not in ("Won", "Lost")]
        if not active_leads:
            st.warning("No active leads. Launch a campaign to generate leads!")
        else:
            # Show by stage
            pipeline_stages = ["New", "Qualified", "Proposal", "Negotiation"]
            stage_cols = st.columns(len(pipeline_stages))
            stage_colors = {"New": "#94A3B8", "Qualified": "#3B82F6",
                            "Proposal": "#F59E0B", "Negotiation": "#EF4444"}

            for i, stage in enumerate(pipeline_stages):
                stage_leads = [l for l in active_leads if l.stage == stage]
                with stage_cols[i]:
                    color = stage_colors[stage]
                    total_val = sum(l.estimated_value for l in stage_leads)
                    st.markdown(
                        f"<div style='background:{color}20; border-top:3px solid {color}; "
                        f"padding:8px; border-radius:6px; margin-bottom:8px;'>"
                        f"<b style='color:{color}'>{stage}</b> ({len(stage_leads)})"
                        f"<br><span style='font-size:0.8rem; color:#64748B'>${total_val:,.0f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    for lead in stage_leads:
                        with st.container(border=True):
                            st.markdown(f"**{lead.company}**")
                            st.caption(f"{lead.tier} | ${lead.estimated_value:,.0f}")
                            st.caption(f"🎯 {lead.win_probability}% | Day {lead.days_in_stage} in stage")

                            next_stages = [s for s in STAGE_ORDER
                                           if STAGE_ORDER.index(s) > STAGE_ORDER.index(stage)]
                            if next_stages:
                                move_to = st.selectbox("Move to", next_stages,
                                                        key=f"move_{lead.id}",
                                                        label_visibility="collapsed")
                                c_b1, c_b2 = st.columns(2)
                                if c_b1.button("✅ Advance", key=f"adv_{lead.id}", type="primary"):
                                    ok, msg = advance_lead_stage(state, lead.id, move_to)
                                    if ok:
                                        st.toast(msg)
                                        st.rerun()
                                if c_b2.button("❌ Lost", key=f"lost_{lead.id}"):
                                    advance_lead_stage(state, lead.id, "Lost")
                                    st.rerun()

        # Won/Lost Summary
        st.divider()
        won = [l for l in state.leads if l.stage == "Won"]
        lost = [l for l in state.leads if l.stage == "Lost"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🏆 Won Deals:**")
            if won:
                won_df = pd.DataFrame([{
                    "Company": l.company, "Tier": l.tier, "Value": f"${l.estimated_value:,.0f}"
                } for l in won[-10:]])
                st.dataframe(won_df, hide_index=True, use_container_width=True)
        with c2:
            st.markdown("**📉 Lost Deals:**")
            if lost:
                lost_df = pd.DataFrame([{
                    "Company": l.company, "Tier": l.tier, "Value": f"${l.estimated_value:,.0f}"
                } for l in lost[-10:]])
                st.dataframe(lost_df, hide_index=True, use_container_width=True)

    # ── Sales Orders ──────────────────────────────────────────────────────────
    with tab_orders:
        st.markdown("<div class='section-title'>ERP Sales Orders</div>", unsafe_allow_html=True)
        open_orders = sorted([so for so in state.sales_orders if so.status == "Open"],
                             key=lambda x: x.due_day)
        for pid, prod in state.products.items():
            qty = state.stock_finished.get(pid, 0)
            st.metric(prod.name, f"{qty} in stock")

        if not open_orders:
            st.success("✅ All orders shipped.")
        else:
            for so in open_orders:
                prod = state.products[so.product_id]
                in_stock = state.stock_finished.get(so.product_id, 0)
                can_ship = in_stock >= so.qty
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2.5, 1.5, 1, 1])
                    c1.markdown(f"**{so.customer_name}** — {so.qty}× {prod.name}")
                    c1.caption(f"{so.id} | Due D{so.due_day} | Source: {so.source}")
                    c2.write(f"${so.qty * so.unit_price:,.0f}")
                    c3.metric("Stock", in_stock)
                    if can_ship:
                        if c4.button("🚀 SHIP", key=f"crmship_{so.id}", type="primary"):
                            ok, msg = ship_sales_order(state, so.id)
                            st.toast("Shipped!" if ok else msg)
                            st.rerun()
                    else:
                        c4.button("⏳ Wait", disabled=True, key=f"crmwt_{so.id}")

    # ── Campaigns ─────────────────────────────────────────────────────────────
    with tab_campaigns:
        st.markdown("<div class='section-title'>📢 Marketing Campaigns</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for col, (ctype, cfg) in zip([c1, c2, c3], {
            "digital_ads": ("💻 Digital Ads", "$500", "1–2 leads", "30–55% win prob"),
            "outbound_calls": ("📞 Outbound Calls", "$1,200", "2–4 leads", "45–65% win prob"),
            "trade_show": ("⭐ Trade Show", "$3,500", "3–5 premium leads", "60–80% win prob"),
        }.items()):
            label, cost, leads, prob = cfg
            with col:
                with st.container(border=True):
                    st.markdown(f"#### {label}")
                    st.metric("Cost", cost)
                    st.caption(f"**{leads}** | {prob}")
                    if st.button(f"🚀 Launch {label.split()[-1]}", key=f"campaign_{ctype}",
                                 use_container_width=True, type="primary"):
                        ok, msg, new_leads = run_marketing_campaign(state, ctype)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        st.metric("Marketing Spend to Date", crm_kpis["Marketing Spend"])
        st.metric("Cost per Win (CAC)", crm_kpis["CAC (Cost per Lead Won)"])

    # ── Customers ─────────────────────────────────────────────────────────────
    with tab_customers:
        st.markdown("<div class='section-title'>👥 Customer 360° View</div>", unsafe_allow_html=True)
        if not state.customers:
            st.info("No customers yet. Win opportunities to create customers.")
        else:
            for cid, cust in state.customers.items():
                health = compute_customer_health(cust)
                icon = "🟢" if health == "Healthy" else ("🟠" if health == "At Risk" else "🔴")
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 1.2, 1.2, 1.2, 1.5])
                    c1.markdown(f"**{cust.name}**")
                    c1.caption(f"{cust.tier} | {cust.city}")
                    c2.metric("CSAT", f"{cust.csat}%")
                    c3.metric("Total Revenue", f"${cust.total_revenue:,.0f}")
                    c4.metric("LTV", f"${cust.lifetime_value:,.0f}")
                    c5.markdown(f"{icon} **{health}**")
                    if cust.open_tickets > 0:
                        c5.caption(f"⚠️ {cust.open_tickets} open ticket(s)")

    # ── Service Desk ──────────────────────────────────────────────────────────
    with tab_service:
        st.markdown("<div class='section-title'>🎫 Service Desk</div>", unsafe_allow_html=True)

        # New ticket form
        with st.expander("➕ Create New Ticket"):
            c1, c2 = st.columns(2)
            if state.customers:
                t_cust = c1.selectbox("Customer", list(state.customers.keys()),
                                       format_func=lambda x: state.customers[x].name)
                t_sev = c1.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
                t_issue = c2.text_input("Issue Description", "Delivery delay reported")
                if c2.button("Create Ticket", type="primary"):
                    ok, msg = create_service_ticket(state, t_cust, t_issue, t_sev)
                    st.toast(f"Ticket {msg} created") if ok else st.error(msg)
                    st.rerun()
            else:
                st.info("No customers yet.")

        # Open Tickets
        open_tickets = [t for t in state.service_tickets if t.status in ("Open", "In Progress")]
        if not open_tickets:
            st.success("✅ No open tickets — great service!")
        else:
            st.warning(f"⚠️ {len(open_tickets)} ticket(s) require attention")
            for t in open_tickets:
                sev_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}[t.severity]
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
                    c1.markdown(f"**{t.customer_name}**")
                    c1.caption(f"{t.id} — {t.issue}")
                    c2.write(f"{sev_color} {t.severity}")
                    c3.write(f"Day {t.day_opened}")
                    b1, b2 = c4.columns(2)
                    if b1.button("✅ Std ($300)", key=f"std_{t.id}"):
                        ok, msg = resolve_ticket(state, t.id, priority=False)
                        st.toast(msg if ok else msg)
                        st.rerun()
                    if b2.button("⚡ Priority ($800)", key=f"pri_{t.id}", type="primary"):
                        ok, msg = resolve_ticket(state, t.id, priority=True)
                        st.toast(msg if ok else msg)
                        st.rerun()
