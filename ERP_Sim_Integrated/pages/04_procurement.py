# =============================================================================
# Page 04 — Procurement
# ERP-only mode: Manual email-based procurement (simulated inbox + manual PO)
# SRM mode: Supplier Portal with RFQ, quote comparison, contracts, AP invoices
# =============================================================================
import streamlit as st
import pandas as pd
from engine.erp_engine import create_manual_po, run_mrp_suggestion
from engine.srm_engine import send_rfq, award_rfq, create_contract, pay_invoice, get_supplier_scorecard

state = st.session_state.sim_state

st.markdown("""
<div class='page-header'>
    <h2>🛒 Procurement</h2>
    <p>Source raw materials from suppliers — manual or automated depending on active modules</p>
</div>
""", unsafe_allow_html=True)

# ── MRP Recommendation Strip ───────────────────────────────────────────────────
suggestions = run_mrp_suggestion(state)
if suggestions:
    with st.expander(f"🤖 MRP has {len(suggestions)} replenishment recommendations", expanded=True):
        for s in suggestions:
            cls = "alert-red" if s["urgency"] == "High" else "alert-amber"
            st.markdown(
                f"<div class='{cls}'><b>{s['urgency']}</b> — {s['material_name']}: "
                f"Stock={s['current_stock']}, Inbound={s['inbound']}, "
                f"7-day demand={s['projected_demand_7d']} → Order ≥ <b>{s['suggested_qty']}</b></div>",
                unsafe_allow_html=True
            )

st.divider()

# =============================================================================
# ===  ERP-ONLY MANUAL PROCUREMENT MODE  =====================================
# =============================================================================
if not state.srm_enabled:
    st.markdown("""
    <div class='alert-amber'>
    <b>📭 Manual Procurement Mode (ERP Only)</b><br>
    SRM is disabled. To order materials, you must:<br>
    1. Go to <b>Inbox</b> to read supplier quotes (arrive next day)<br>
    2. Come back here and manually enter the price and lead time from the email<br>
    3. Create a Purchase Order manually
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    # Inline unread email count hint
    unread_rfq = [m for m in state.inbox if not m.is_read and m.category == "rfq_response"]
    if unread_rfq:
        st.info(f"📬 You have {len(unread_rfq)} unread supplier quote emails in your Inbox.")

    st.markdown("<div class='section-title'>📝 Manual Purchase Order Entry</div>", unsafe_allow_html=True)
    st.caption("Enter the price and lead time from the supplier email you received.")

    with st.form("manual_po_form"):
        c1, c2 = st.columns(2)
        with c1:
            mat_choice = st.selectbox("Material", list(state.materials.keys()),
                                       format_func=lambda x: state.materials[x].name)
            supplier_choice = st.selectbox(
                "Supplier",
                [sid for sid, sup in state.suppliers.items()
                 if mat_choice in sup.materials and not sup.is_blocked],
                format_func=lambda x: f"{state.suppliers[x].name} ({state.suppliers[x].country})",
            ) if any(mat_choice in sup.materials and not sup.is_blocked
                     for sup in state.suppliers.values()) else None

        with c2:
            quoted_price = st.number_input("Quoted Price (from email) $",
                                             min_value=1.0, value=float(state.materials[mat_choice].cost),
                                             step=0.5, format="%.2f")
            quoted_lead = st.number_input("Lead Time (days, from email)",
                                           min_value=1, max_value=30, value=3)
            qty = st.number_input("Quantity", min_value=10, max_value=1000, value=50, step=10)

        mat = state.materials[mat_choice]
        market_ref = state.suppliers[supplier_choice].current_price.get(mat_choice, mat.cost) if supplier_choice else mat.cost
        st.caption(f"📊 Reference market price: **${market_ref:.2f}/{mat.unit}** | "
                   f"Total cost: **${quoted_price * qty:,.0f}** | Cash: **${state.cash:,.0f}**")

        submitted = st.form_submit_button("📋 Create Purchase Order", type="primary", use_container_width=True)
        if submitted:
            if not supplier_choice:
                st.error("No eligible supplier found for this material.")
            else:
                ok, msg = create_manual_po(state, supplier_choice, mat_choice, qty, quoted_price, quoted_lead)
                if ok:
                    st.success(f"✅ PO created: {msg}. Expected arrival: Day {state.current_day + quoted_lead}")
                    st.rerun()
                else:
                    st.error(msg)

    # Open POs
    st.markdown("<div class='section-title'>📦 Open Purchase Orders</div>", unsafe_allow_html=True)
    open_pos = [po for po in state.purchase_orders if po.status == "OnOrder"]
    if open_pos:
        rows = []
        for po in sorted(open_pos, key=lambda x: x.expected_arrival_day):
            sup = state.suppliers.get(po.supplier_id)
            mat = state.materials.get(po.material_id)
            days_left = po.expected_arrival_day - state.current_day
            rows.append({
                "PO #": po.id, "Supplier": sup.name if sup else "?",
                "Material": mat.name if mat else "?", "Qty": po.qty,
                "Unit Cost": f"${po.unit_cost:.2f}", "Total": f"${po.qty * po.unit_cost:,.0f}",
                "Expected Arrival": f"Day {po.expected_arrival_day}",
                "Days Left": days_left,
                "Status": "🔴 Late" if days_left < 0 else ("🟡 Soon" if days_left <= 1 else "🟢 OK"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No open purchase orders. Go to Inbox to get supplier quotes and create POs.")


# =============================================================================
# ===  SRM MODULE — SUPPLIER PORTAL  =========================================
# =============================================================================
else:
    st.markdown("<div class='alert-blue'><b>🔗 SRM Module Active</b> — Real-time supplier portal with automated RFQ, quote comparison, contract management & AP tracking.</div>",
                unsafe_allow_html=True)
    st.markdown("")

    tab_rfq, tab_contracts, tab_invoices, tab_scorecards = st.tabs([
        "📋 RFQ & Ordering", "📝 Contracts", "🧾 AP Invoices", "🏅 Supplier Scorecards"
    ])

    # ── RFQ Tab ────────────────────────────────────────────────────────────────
    with tab_rfq:
        st.markdown("<div class='section-title'>Send RFQ (Request for Quotation)</div>", unsafe_allow_html=True)

        col_rfq, col_open = st.columns([1, 1])
        with col_rfq:
            with st.form("rfq_form"):
                mat_rfq = st.selectbox("Material Needed", list(state.materials.keys()),
                                        format_func=lambda x: state.materials[x].name)
                qty_rfq = st.number_input("Quantity Required", min_value=10, max_value=2000, value=100, step=10)
                st.caption(f"✅ SRM will query all eligible suppliers instantly. "
                           f"Market ref: ${state.materials[mat_rfq].cost:.2f}/{state.materials[mat_rfq].unit}")
                send_btn = st.form_submit_button("📤 Send RFQ to All Suppliers", type="primary", use_container_width=True)
                if send_btn:
                    ok, msg, rfq = send_rfq(state, mat_rfq, qty_rfq)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(msg)

        with col_open:
            # Show latest open RFQ
            open_rfqs = [r for r in state.rfqs if r.status == "QuotesReceived"]
            if open_rfqs:
                st.markdown(f"**{len(open_rfqs)} Open RFQ(s)** — Awards pending")
                latest = open_rfqs[-1]
                mat = state.materials.get(latest.material_id)
                st.markdown(f"**{latest.id}**: {latest.qty_requested}x {mat.name if mat else '?'}")
            else:
                st.info("No open RFQs. Send one to see quotes.")

        # ── Quote Comparison ────────────────────────────────────────────────
        open_rfqs = [r for r in state.rfqs if r.status == "QuotesReceived"]
        for rfq in open_rfqs:
            mat = state.materials.get(rfq.material_id)
            st.markdown(f"<div class='section-title'>🏆 Quote Comparison — {rfq.id} | {rfq.qty_requested}x {mat.name if mat else '?'}</div>",
                        unsafe_allow_html=True)

            if not rfq.responses:
                st.warning("No responses received.")
                continue

            quote_rows = []
            for i, r in enumerate(rfq.responses):
                contract_tag = "✅ Contracted" if r.get("is_contracted") else "—"
                rank = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}")
                quote_rows.append({
                    "Rank": rank, "Supplier": r["supplier_name"],
                    "Unit Price": f"${r['price']:.2f}", "Total Cost": f"${r['total_cost']:,.0f}",
                    "Lead Time": f"{r['lead_time']}d",
                    "Quality Rate": f"{r['quality_rate']*100:.0f}%",
                    "On-Time Rate": f"{r['reliability']*100:.0f}%",
                    "Rel. Score": f"{r['relationship_score']:.0f}/100",
                    "Composite Score": f"{r['composite_score']:.1f}",
                    "Contract": contract_tag,
                })
            st.dataframe(pd.DataFrame(quote_rows), use_container_width=True, hide_index=True)

            # Award buttons
            st.markdown("**Award to:**")
            award_cols = st.columns(len(rfq.responses))
            for i, r in enumerate(rfq.responses):
                with award_cols[i]:
                    if st.button(f"Award to {r['supplier_name'].split()[0]}",
                                 key=f"award_{rfq.id}_{r['supplier_id']}", type="primary"):
                        ok, msg = award_rfq(state, rfq.id, r["supplier_id"])
                        if ok:
                            st.success(f"✅ PO {msg} created!")
                            st.rerun()
                        else:
                            st.error(msg)

        # Active POs
        st.markdown("<div class='section-title'>📦 Inbound Monitor</div>", unsafe_allow_html=True)
        open_pos = [po for po in state.purchase_orders if po.status == "OnOrder"]
        if open_pos:
            pos_rows = []
            for po in sorted(open_pos, key=lambda x: x.expected_arrival_day):
                sup = state.suppliers.get(po.supplier_id)
                mat = state.materials.get(po.material_id)
                days_left = po.expected_arrival_day - state.current_day
                pos_rows.append({
                    "PO #": po.id, "Source": po.po_source.upper(),
                    "Supplier": sup.name if sup else "?", "Material": mat.name if mat else "?",
                    "Qty": po.qty, "Unit Cost": f"${po.unit_cost:.2f}",
                    "Total": f"${po.qty * po.unit_cost:,.0f}",
                    "Arrival": f"Day {po.expected_arrival_day}",
                    "Days Left": days_left,
                    "Status": "🔴 Late" if days_left < 0 else ("🟡 Today" if days_left == 0 else "🟢 Transit"),
                })
            st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No open purchase orders.")

    # ── Contracts Tab ─────────────────────────────────────────────────────────
    with tab_contracts:
        st.markdown("<div class='section-title'>📝 Create / Manage Contracts</div>", unsafe_allow_html=True)
        st.info("Lock in a preferred supplier price for a material. Contracted prices appear highlighted in RFQ comparisons.")

        with st.form("contract_form"):
            c1, c2 = st.columns(2)
            with c1:
                contract_mat = st.selectbox("Material", list(state.materials.keys()),
                                             format_func=lambda x: state.materials[x].name)
                valid_suppliers = [sid for sid, sup in state.suppliers.items()
                                   if contract_mat in sup.materials and not sup.is_blocked]
                contract_sup = st.selectbox(
                    "Supplier", valid_suppliers,
                    format_func=lambda x: state.suppliers[x].name
                ) if valid_suppliers else None
            with c2:
                market_p = state.suppliers[contract_sup].current_price.get(contract_mat, 0) if contract_sup else 0
                neg_price = st.number_input("Negotiated Price $", min_value=0.1,
                                             value=round(market_p * 0.96, 2), step=0.1, format="%.2f")
                volume = st.number_input("Volume Commitment (units)", min_value=50, value=200, step=50)
                st.caption(f"Market price: ${market_p:.2f} | Your price: ${neg_price:.2f} "
                           f"| Saving: ${(market_p - neg_price) * volume:,.0f} over commitment")

            if st.form_submit_button("📝 Establish Contract", type="primary", use_container_width=True):
                if not contract_sup:
                    st.error("No eligible supplier.")
                else:
                    ok, msg = create_contract(state, contract_sup, contract_mat, neg_price, volume)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()

        # Show active contracts
        contracts = [(sid, sup) for sid, sup in state.suppliers.items() if sup.contract_price]
        if contracts:
            st.markdown("**Active Contracts:**")
            for sid, sup in contracts:
                for mid, price in sup.contract_price.items():
                    mat = state.materials.get(mid)
                    market = sup.current_price.get(mid, mat.cost if mat else 0)
                    savings = market - price
                    st.markdown(
                        f"<div class='alert-green'>📝 <b>{sup.name}</b> → {mat.name if mat else mid}: "
                        f"${price:.2f} (market ${market:.2f}, saving ${savings:.2f}/unit)</div>",
                        unsafe_allow_html=True
                    )

    # ── AP Invoices Tab ───────────────────────────────────────────────────────
    with tab_invoices:
        st.markdown("<div class='section-title'>🧾 Accounts Payable — Supplier Invoices</div>", unsafe_allow_html=True)

        unpaid = [i for i in state.supplier_invoices if i.status in ("Unpaid", "Overdue")]
        paid_recent = [i for i in state.supplier_invoices if i.status == "Paid"][-10:]

        if not unpaid:
            st.success("✅ No unpaid invoices! Great payables management.")
        else:
            for inv in sorted(unpaid, key=lambda x: x.due_day):
                sup = state.suppliers.get(inv.supplier_id)
                days_left = inv.due_day - state.current_day
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 1.2, 1.2, 1.2, 1.5])
                    c1.markdown(f"**{sup.name if sup else '?'}**")
                    c1.caption(f"{inv.id} | PO: {inv.po_id}")
                    c2.metric("Amount", f"${inv.amount:,.0f}")

                    if days_left < 0:
                        c3.markdown(f"<div class='alert-red'>Overdue {-days_left}d</div>", unsafe_allow_html=True)
                    elif days_left <= 5:
                        c3.markdown(f"<div class='alert-amber'>Due in {days_left}d</div>", unsafe_allow_html=True)
                    else:
                        c3.markdown(f"<div class='alert-green'>Due Day {inv.due_day}</div>", unsafe_allow_html=True)

                    early_ok = state.current_day <= inv.day_issued + 10
                    c4.metric("Early Disc.", f"${inv.early_payment_discount:.0f}" if early_ok else "N/A")

                    with c5:
                        if c5.button("💸 Pay Standard", key=f"pay_std_{inv.id}", type="secondary"):
                            ok, msg = pay_invoice(state, inv.id, early=False)
                            if ok:
                                st.toast(f"Paid {inv.id}")
                                st.rerun()
                            else:
                                st.error(msg)
                        if early_ok and c5.button(f"⚡ Pay Early (−${inv.early_payment_discount:.0f})",
                                                   key=f"pay_early_{inv.id}", type="primary"):
                            ok, msg = pay_invoice(state, inv.id, early=True)
                            if ok:
                                st.toast(f"Early payment! Discount applied.")
                                st.rerun()
                            else:
                                st.error(msg)

        if paid_recent:
            st.markdown("**Recently Paid Invoices:**")
            paid_rows = [{"ID": i.id, "Supplier": state.suppliers[i.supplier_id].name if i.supplier_id in state.suppliers else "?",
                          "Amount": f"${i.amount:,.0f}", "Paid Day": i.paid_day} for i in paid_recent]
            st.dataframe(pd.DataFrame(paid_rows), use_container_width=True, hide_index=True)

    # ── Supplier Scorecard Tab ─────────────────────────────────────────────────
    with tab_scorecards:
        st.markdown("<div class='section-title'>🏅 Supplier Performance Scorecards</div>", unsafe_allow_html=True)
        for sid, sup in state.suppliers.items():
            sc = get_supplier_scorecard(state, sid)
            with st.container(border=True):
                ch, ck = st.columns([1, 3])
                with ch:
                    st.markdown(f"**{sup.name}**")
                    st.caption(f"{sup.category} | {sup.country}")
                    if sup.is_blocked:
                        st.error("🚫 BLOCKED")
                    elif sup.relationship_score >= 80:
                        st.success(f"⭐ {sup.relationship_score:.0f}/100")
                    elif sup.relationship_score >= 50:
                        st.warning(f"🟡 {sup.relationship_score:.0f}/100")
                    else:
                        st.error(f"🔴 {sup.relationship_score:.0f}/100")
                    if sup.contract_price:
                        st.markdown("<span class='badge-srm'>CONTRACTED</span>", unsafe_allow_html=True)

                with ck:
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Deliveries", sc.get("deliveries", 0))
                    k2.metric("On-Time Rate", f"{sc.get('on_time_rate', 0):.0f}%")
                    k3.metric("Defect PPM", sc.get("defect_ppm", 0))
                    k4.metric("Total Spend", f"${sc.get('total_spend', 0):,.0f}")
