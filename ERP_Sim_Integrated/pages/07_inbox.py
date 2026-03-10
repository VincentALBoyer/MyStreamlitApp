# =============================================================================
# Page 07 — Inbox (Simulated Communications)
# Most meaningful in ERP-only (manual) mode.
# In SRM/CRM mode, shows system notifications instead.
# =============================================================================
import streamlit as st
import pandas as pd

state = st.session_state.sim_state

st.markdown("""
<div class='page-header'>
    <h2>📬 Communications Inbox</h2>
    <p>Simulated emails from suppliers and customers — check daily for quotes and orders</p>
</div>
""", unsafe_allow_html=True)

# Mode context banner
if state.srm_enabled and state.crm_enabled:
    st.markdown("""
    <div class='alert-green'>
    <b>✅ Both SRM and CRM are active.</b> Your inbox is now replaced by real-time portals.
    Supplier quotes appear instantly in Procurement → RFQ. Customer pipelines are managed in Sales.
    This inbox shows system alerts only.
    </div>
    """, unsafe_allow_html=True)
elif state.srm_enabled:
    st.markdown("""
    <div class='alert-blue'>
    <b>🔗 SRM Active:</b> Supplier quotes now arrive immediately in the Procurement portal.
    Customer order emails still appear below (CRM not enabled yet).
    </div>
    """, unsafe_allow_html=True)
elif state.crm_enabled:
    st.markdown("""
    <div class='alert-blue'>
    <b>📊 CRM Active:</b> Customer orders are managed in the Sales pipeline.
    Supplier quote requests still require manual email handling (SRM not enabled yet).
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class='alert-amber'>
    <b>📭 Manual Mode (ERP Only):</b> All supplier and customer communications arrive here.
    <br>• Read supplier emails to get prices → go to <b>Procurement</b> to create POs manually.
    <br>• Read customer order emails → go to <b>Sales</b> to process orders.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
cat_filter = st.tabs(["📥 All Messages", "📋 Supplier Quotes", "🛒 Customer Orders", "⚠️ Alerts"])

def render_messages(messages):
    if not messages:
        st.info("No messages in this category.")
        return

    for msg in sorted(messages, key=lambda x: (x.is_read, -x.day_received)):
        read_cls = "inbox-read" if msg.is_read else "inbox-unread"
        unread_badge = "" if msg.is_read else "<span style='background:#EFF6FF;color:#1D4ED8;padding:2px 8px;border-radius:20px;font-size:0.72rem;font-weight:700;'>NEW</span>"

        with st.container():
            st.markdown(
                f"<div class='inbox-card {read_cls}'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='font-weight:600;font-size:0.9rem;'>{msg.sender}</span>"
                f"<span style='display:flex;gap:8px;align-items:center;'>{unread_badge}"
                f"<span style='color:#94A3B8;font-size:0.78rem;'>Day {msg.day_received}</span></span>"
                f"</div>"
                f"<div style='font-size:0.95rem;margin:4px 0;'><b>{msg.subject}</b></div>"
                f"<div style='font-size:0.84rem;color:#475569;white-space:pre-line;'>{msg.body[:400]}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            if not msg.is_read:
                if st.button("📖 Mark as Read", key=f"read_{msg.id}"):
                    msg.is_read = True
                    st.rerun()

            # Category-specific quick-action hints
            if msg.category == "rfq_response" and not state.srm_enabled:
                st.caption("👉 Go to **Procurement** to create a manual PO using this price.")
            elif msg.category == "customer_order" and not state.crm_enabled:
                st.caption("👉 Go to **Sales** to process this customer order.")


with cat_filter[0]:
    render_messages(state.inbox)

with cat_filter[1]:
    rfq_msgs = [m for m in state.inbox if m.category == "rfq_response"]
    render_messages(rfq_msgs)

with cat_filter[2]:
    order_msgs = [m for m in state.inbox if m.category == "customer_order"]
    render_messages(order_msgs)

with cat_filter[3]:
    alert_msgs = [m for m in state.inbox if m.category == "alert"]
    if not alert_msgs:
        # Generate from daily events as alerts
        if state.daily_events:
            critical = [ev for ev in state.daily_events if "⚠️" in ev or "❌" in ev or "🚫" in ev]
            if critical:
                for ev in critical:
                    st.markdown(f"<div class='alert-red'>{ev}</div>", unsafe_allow_html=True)
            else:
                st.success("✅ No alerts today!")
        else:
            st.info("No alerts.")
    else:
        render_messages(alert_msgs)

# Unread count footer
unread = len([m for m in state.inbox if not m.is_read])
if unread > 0:
    if st.button(f"✅ Mark All as Read ({unread} unread)", use_container_width=True):
        for m in state.inbox:
            m.is_read = True
        st.rerun()
