from __future__ import annotations

import streamlit as st

from demand_dashboard.components import go_to, metric_row, page_heading


def render() -> None:
    page_heading(
        "OPERATIONS",
        "Inventory & replenishment",
        "Review lead-time coverage and suggested replenishment using the latest forecast run.",
    )
    forecast = st.session_state.get("last_forecast")
    if forecast is None:
        with st.container(border=True):
            st.info("There is no forecast in this session yet. Generate one to calculate the reorder point and order quantity.")
            go_to("Open demand forecasting", "Demand forecasting", key="inventory_open_forecast", primary=True)
        st.caption("Stock assumptions and recommendations are session-based; inventory and purchase orders are not stored in the database.")
        return

    plan = forecast["inventory"]
    below_reorder = plan["stock"] <= plan["reorder_point"]
    st.markdown(
        f"**Product {forecast['product_id']}** · {forecast['category']} · "
        f"Hub {forecast['store_id']} · Updated {forecast['created_at']}"
    )
    metric_row(
        [
            ("Current stock", f"{plan['stock']:,} units", None),
            ("Reorder point", f"{plan['reorder_point']:,} units", "Lead-time demand plus the existing safety-stock calculation"),
            ("Suggested order quantity", f"{plan['order_quantity']:,} units", "Recommendation only; no purchase order is created"),
            ("Supplier lead time", f"{plan['lead_time']} days", None),
        ]
    )
    st.markdown("")
    if below_reorder:
        st.error(
            f"Replenishment recommended: stock is {plan['order_quantity']:,} units below the calculated reorder point."
        )
        st.warning("This is a planning alert only. The application does not send a webhook or submit a purchase order.")
    else:
        st.success("Stock is currently above the calculated reorder point.")

    coverage = min(100, round(plan["stock"] / plan["reorder_point"] * 100)) if plan["reorder_point"] else 100
    st.subheader("Stock level")
    st.progress(coverage, text=f"{coverage}% of reorder-point coverage")
    details, alerts = st.columns(2)
    with details:
        with st.container(border=True):
            st.subheader("Planning inputs")
            st.write(f"Forecast: {sum(forecast['predictions'].values()):,} units across three days")
            st.write(f"7-day average demand: {forecast['avg7']:,.1f} units")
            st.write(f"Stockout exposure estimate: ₹{plan['stockout_risk']:,.2f}")
            st.write(f"Excess-stock carrying estimate: ₹{plan['holding_cost']:,.2f}")
    with alerts:
        with st.container(border=True):
            st.subheader("Recommended action")
            if below_reorder:
                st.write(f"Plan an order for approximately **{plan['order_quantity']:,} units**.")
                st.caption("Confirm supplier availability and stock counts before acting.")
            else:
                st.write("No replenishment quantity is suggested by the current inputs.")
                st.caption("Review the plan again when demand or lead-time assumptions change.")

    with st.expander("System notices"):
        activity = st.session_state.get("planning_activity", [])
        if not activity:
            st.caption("No planning events have been recorded in this session.")
        else:
            for event in activity[:10]:
                st.write(f"{event['time']} · {event['event']}")
        st.caption("External notification delivery and procurement execution are not configured.")
