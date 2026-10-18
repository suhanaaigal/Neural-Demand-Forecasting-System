from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from demand_dashboard.components import go_to, metric_row, page_heading
from demand_dashboard.services import (
    FORECAST_ENDPOINT,
    load_products,
    load_recent_sales,
    load_registry,
    load_sales_daily,
)


def render() -> None:
    page_heading(
        "EXECUTIVE WORKSPACE",
        "Overview",
        "A live view of registered products, observed sales, and the latest planning run.",
    )
    products = load_products()
    registry = load_registry()
    latest = st.session_state.get("last_forecast")
    daily = load_sales_daily(days=30)
    sales_total = int(daily["units_sold"].sum()) if not daily.empty else 0
    alerts = int(
        bool(latest and latest["inventory"]["stock"] <= latest["inventory"]["reorder_point"])
    )
    projected = (
        f"{sum(latest['predictions'].values()):,} units"
        if latest
        else "—"
    )
    metric_row(
        [
            ("Registered SKUs", f"{len(registry):,}", "Product/category records in the SKU registry"),
            ("Observed sales · 30 days", f"{sales_total:,} units", "From the latest 30 days present in the sales ledger"),
            ("Latest 3-day forecast", projected, "Available after generating a forecast in this session"),
            ("Planning alerts", str(alerts) if latest else "—", "Based on the most recent forecast and its stock assumption"),
            (
                "Suggested replenishment",
                f"{latest['inventory']['order_quantity']:,} units" if latest else "—",
                "Recommendation only; no purchase order is created",
            ),
            ("Inventory value / open POs", "Not tracked", "No inventory valuation or purchase-order records exist in the database"),
        ]
    )

    st.markdown("")
    left, right = st.columns([1.55, 1])
    with left:
        with st.container(border=True):
            if latest:
                st.subheader(f"Observed demand · Product {latest['product_id']} · Hub {latest['store_id']}")
                trend = load_sales_daily(
                    product_id=latest["product_id"],
                    store_id=latest["store_id"],
                    days=30,
                )
            else:
                st.subheader("Observed demand · All products")
                trend = daily
            st.caption("Daily observed units from the sales ledger. Forecast horizons are shown separately.")
            if trend.empty:
                st.info("No matching sales history is available in the database.")
            else:
                chart = trend.set_index("date")["units_sold"].rename("Observed units")
                chart.index.name = "Date"
                st.line_chart(chart, height=250, width="stretch")
            if latest:
                forecast_chart = pd.DataFrame.from_dict(
                    latest["predictions"],
                    orient="index",
                    columns=["Forecast units"],
                )
                st.subheader("Latest forecast horizons")
                st.bar_chart(forecast_chart, height=180, width="stretch")

    with right:
        with st.container(border=True):
            st.subheader("Planning alerts")
            if latest is None:
                st.info("Generate a forecast to see SKU-specific replenishment alerts.")
                go_to("Open demand forecasting", "Demand forecasting", key="overview_forecast")
            elif alerts:
                st.warning(
                    f"Product {latest['product_id']} at hub {latest['store_id']} is below its "
                    f"reorder point by {latest['inventory']['order_quantity']:,} units."
                )
                go_to("Review replenishment", "Inventory & replenishment", key="overview_inventory")
            else:
                st.success("The latest planning run is above its calculated reorder point.")
            st.markdown("---")
            st.caption("Procurement requests are recommendations only; purchase orders are not connected.")

    action_a, action_b, action_c = st.columns(3)
    with action_a:
        go_to("＋  Generate forecast", "Demand forecasting", key="overview_go_forecast", primary=True)
    with action_b:
        go_to("▦  Review inventory", "Inventory & replenishment", key="overview_go_inventory")
    with action_c:
        go_to("⇩  Create a report", "Reports & bulk operations", key="overview_go_reports")

    activity, status = st.columns([1.5, 1])
    with activity:
        with st.container(border=True):
            st.subheader("Recent sales activity")
            recent = load_recent_sales()
            if recent.empty:
                st.info("No transaction records are available.")
            else:
                st.dataframe(recent, hide_index=True, width="stretch")
        with st.container(border=True):
            st.subheader("Recent procurement activity")
            st.info("Purchase orders are not stored in the current database.")
            if latest:
                st.caption(
                    f"Latest recommendation: {latest['inventory']['order_quantity']:,} units "
                    f"for product {latest['product_id']}. This is not an issued order."
                )
    with status:
        with st.container(border=True):
            st.subheader("System status")
            try:
                response = requests.get(
                    FORECAST_ENDPOINT.rsplit("/", 1)[0] + "/openapi.json",
                    timeout=2,
                )
                if response.ok:
                    st.success("Forecasting API is reachable.")
                    st.session_state["forecast_service_online"] = True
                else:
                    st.warning(f"Forecasting API responded with HTTP {response.status_code}.")
                    st.session_state["forecast_service_online"] = False
            except requests.RequestException:
                st.error("Forecasting API is not reachable. Start the backend to generate forecasts.")
                st.session_state["forecast_service_online"] = False
            st.caption(f"{len(products):,} products in registry join · sales ledger available")
            st.caption("Procurement and inventory valuation: not connected")
