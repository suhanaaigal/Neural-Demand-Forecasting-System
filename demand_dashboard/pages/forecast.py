from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from demand_dashboard.components import metric_row, page_heading
from demand_dashboard.services import (
    ATTENTION_PROFILE,
    adjust_predictions,
    build_payload,
    generate_forecast_pdf,
    inventory_plan,
    load_dimension_values,
    load_products,
    load_sales_daily,
    product_history,
    product_category,
    pricing_scenarios,
    request_forecast,
)


def _record_event(message: str) -> None:
    events = st.session_state.setdefault("planning_activity", [])
    events.insert(0, {"time": date.today().isoformat(), "event": message})
    del events[20:]


def render() -> None:
    page_heading(
        "PLANNING",
        "Demand forecasting",
        "Set operational assumptions, generate the model forecast, and review its planning context.",
    )
    products = load_products()
    product_ids = [int(value) for value in products["product_id"].tolist()]
    if not product_ids:
        st.warning("Register a product before creating a forecast.")
        return

    with st.form("forecast_inputs"):
        with st.container(border=True):
            st.markdown("#### Product and location")
            location_col, product_col, price_col = st.columns(3)
            hubs = load_dimension_values("store_id") or [1]
            with location_col:
                store_id = st.selectbox("Distribution hub", hubs, help="Choose a hub present in the sales ledger.")
            with product_col:
                product_id = st.selectbox(
                    "Product",
                    product_ids,
                    format_func=lambda pid: f"{pid} · {product_category(pid) or 'Uncategorised'}",
                )
            history = product_history(int(product_id))
            with price_col:
                unit_price = st.number_input(
                    "Unit price (₹)",
                    min_value=0.0,
                    value=float(history["unit_price"] or 0.0),
                    step=1.0,
                    format="%.2f",
                    help="Defaults to the product's observed average price in recent sales.",
                )

        with st.container(border=True):
            st.markdown("#### Demand assumptions")
            avg7_col, avg30_col = st.columns(2)
            with avg7_col:
                avg7 = st.number_input(
                    "7-day average (units)",
                    min_value=0.0,
                    value=float(history["rolling_avg_7"] or 0.0),
                    step=1.0,
                    help="Average daily units sold over the last 7 days.",
                )
            with avg30_col:
                avg30 = st.number_input(
                    "30-day average (units)",
                    min_value=0.0,
                    value=float(history["rolling_avg_30"] or 0.0),
                    step=1.0,
                    help="Average daily units sold over the last 30 days.",
                )
            promo_col, day_col = st.columns(2)
            with promo_col:
                promo = st.selectbox("Promotion", ["No promotion", "Promotion active"])
            with day_col:
                day_label = st.selectbox(
                    "Forecast start day",
                    ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    index=date.today().weekday() + 1 if date.today().weekday() < 6 else 0,
                )

        with st.container(border=True):
            st.markdown("#### Inventory context")
            stock_col, lead_col = st.columns(2)
            with stock_col:
                stock = st.number_input("Current stock (units)", min_value=0, value=300, step=1)
            with lead_col:
                lead_time = st.number_input("Supplier lead time (days)", min_value=1, max_value=30, value=3)
            selected_horizons = st.multiselect(
                "Show forecast horizons",
                ["T+1", "T+2", "T+3"],
                default=["T+1", "T+2", "T+3"],
                help="The model returns all three horizons; this controls which results are highlighted.",
            )
            submitted = st.form_submit_button("Generate forecast", type="primary", width="stretch")

    if history["rolling_avg_7"] is None:
        st.info("No sales history is recorded for this product. Enter the price and demand assumptions manually.")

    if submitted:
        day_index = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(day_label)
        payload = build_payload(
            store_id=int(store_id),
            product_id=int(product_id),
            unit_price=unit_price,
            is_promo=int(promo == "Promotion active"),
            rolling_avg_7=avg7,
            rolling_avg_30=avg30,
            day_of_week=day_index,
        )
        try:
            with st.spinner("Contacting the forecasting service…"):
                raw_predictions = request_forecast(payload)
        except RuntimeError as exc:
            st.session_state["forecast_service_online"] = False
            st.error(str(exc))
            st.info("Check that the FastAPI service is running at the configured endpoint.")
            return

        st.session_state["forecast_service_online"] = True
        category = product_category(int(product_id)) or "Unknown / General"
        predictions = adjust_predictions(raw_predictions, category)
        prices, recommended_price, elasticity = pricing_scenarios(unit_price, predictions["t+1"])
        plan = inventory_plan(predictions, avg7, int(stock), int(lead_time))
        result = {
            "store_id": int(store_id),
            "product_id": int(product_id),
            "category": category,
            "unit_price": float(unit_price),
            "promo": int(promo == "Promotion active"),
            "avg7": float(avg7),
            "avg30": float(avg30),
            "day_of_week": day_index,
            "predictions": predictions,
            "inventory": plan,
            "price_scenarios": prices,
            "recommended_price": recommended_price,
            "elasticity": elasticity,
            "selected_horizons": selected_horizons,
            "created_at": date.today().isoformat(),
        }
        st.session_state["last_forecast"] = result
        _record_event(
            f"Forecast generated for product {product_id} at hub {store_id}; suggested order {plan['order_quantity']} units."
        )
        st.session_state["unread_alert_count"] = int(stock <= plan["reorder_point"])

    result = st.session_state.get("last_forecast")
    if result is None:
        st.info("Forecast results will appear here after the first successful run.")
        return

    st.markdown("---")
    st.subheader(f"Forecast · Product {result['product_id']} · Hub {result['store_id']}")
    horizons = result["selected_horizons"] or ["T+1", "T+2", "T+3"]
    keys = [label.lower().replace("t", "t") for label in horizons]
    metric_row(
        [
            (horizon, f"{result['predictions'][key]:,} units", None)
            for horizon, key in zip(horizons, keys)
        ]
    )
    actual = load_sales_daily(result["product_id"], result["store_id"], days=90)
    if actual.empty:
        st.info("No historical transactions match this product and hub. The forecast is based on the assumptions above.")
    else:
        historical = actual.set_index("date")["units_sold"].rename("Observed units")
        forecast_dates = [actual["date"].max() + pd.Timedelta(days=offset) for offset in (1, 2, 3)]
        future = pd.Series(
            list(result["predictions"].values()),
            index=forecast_dates,
            name="Forecast units",
        )
        chart = pd.concat([historical, future])
        st.subheader("Observed demand and forecast")
        st.line_chart(chart, height=270)

    with st.expander("Forecast input profile", expanded=False):
        st.caption(
            "The service returns forecast values, not model attention tensors. "
            "These are the existing configured feature-weight estimates, not per-run model attention."
        )
        weights = pd.DataFrame.from_dict(ATTENTION_PROFILE, orient="index", columns=["Configured weight"])
        weights.index.name = "Input feature"
        st.bar_chart(weights, horizontal=True, height=220)

    st.download_button(
        "Download forecast brief (PDF)",
        data=generate_forecast_pdf(result),
        file_name=f"forecast_product_{result['product_id']}_hub_{result['store_id']}.pdf",
        mime="application/pdf",
    )
