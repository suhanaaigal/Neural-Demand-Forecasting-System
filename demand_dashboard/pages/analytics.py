from __future__ import annotations

import pandas as pd
import streamlit as st

from demand_dashboard.components import metric_row, page_heading
from demand_dashboard.services import (
    ATTENTION_PROFILE,
    load_products,
    load_sales_daily,
    pricing_scenarios,
)


def render() -> None:
    page_heading(
        "ANALYSIS",
        "Pricing & analytics",
        "Compare the existing price scenarios and inspect observed product demand and forecast context.",
    )
    forecast = st.session_state.get("last_forecast")
    products = load_products()
    if products.empty:
        st.info("Register products and record sales to use pricing analytics.")
        return

    product_ids = products["product_id"].astype(int).tolist()
    default_product = forecast["product_id"] if forecast and forecast["product_id"] in product_ids else product_ids[0]
    selected_product = st.selectbox(
        "Product",
        product_ids,
        index=product_ids.index(default_product),
        format_func=lambda pid: f"{pid} · {products.loc[products['product_id'] == pid, 'category'].iloc[0]}",
    )
    product_row = products.loc[products["product_id"] == selected_product].iloc[0]
    default_price = (
        float(forecast["unit_price"])
        if forecast and forecast["product_id"] == selected_product
        else float(product_row["avg_price"]) if pd.notna(product_row["avg_price"]) else 0.0
    )
    default_demand = (
        int(forecast["predictions"]["t+1"])
        if forecast and forecast["product_id"] == selected_product
        else max(5, round(float(product_row["avg_demand"]))) if pd.notna(product_row["avg_demand"]) else 5
    )
    price_col, demand_col = st.columns(2)
    with price_col:
        price = st.number_input("Current price (₹)", min_value=0.0, value=default_price, step=1.0, format="%.2f")
    with demand_col:
        demand = st.number_input("T+1 baseline demand (units)", min_value=0, value=default_demand, step=1)

    scenarios, recommended, elasticity = pricing_scenarios(price, int(demand))
    baseline_revenue = price * demand
    best_revenue = float(scenarios["Estimated revenue (₹)"].max())
    metric_row(
        [
            ("Current price", f"₹{price:,.2f}", None),
            ("Suggested scenario price", f"₹{recommended:,.2f}", "Best revenue in the five current price scenarios"),
            ("Demand elasticity", f"{elasticity:.2f}", "Existing pricing-sandbox assumption"),
            ("Estimated scenario revenue", f"₹{best_revenue:,.2f}", f"Baseline scenario revenue: ₹{baseline_revenue:,.2f}"),
        ]
    )
    st.subheader("Price scenario comparison")
    st.bar_chart(scenarios.set_index("Price change")[["Estimated revenue (₹)"]], height=260)
    st.dataframe(scenarios, hide_index=True, width="stretch")

    st.subheader("Observed demand trend")
    history = load_sales_daily(int(selected_product), days=180)
    if history.empty:
        st.info("There is no transaction history for this product.")
    else:
        st.line_chart(history.set_index("date")["units_sold"].rename("Units sold"), height=260)

    with st.expander("Configured forecast input profile"):
        st.caption(
            "This is the application's existing configured feature-weight profile, not measured per-request "
            "Transformer attention. The forecast API does not return explainability tensors."
        )
        st.bar_chart(
            pd.DataFrame.from_dict(ATTENTION_PROFILE, orient="index", columns=["Configured weight"]),
            horizontal=True,
            height=220,
        )
