from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import date

from demand_dashboard.components import page_heading
from demand_dashboard.services import (
    adjust_predictions,
    build_payload,
    generate_bulk_pdf,
    generate_forecast_pdf,
    inventory_plan,
    product_category,
    product_history,
    request_forecast,
    validate_manifest,
)


def _simulate(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        product_id = int(row["product_id"])
        store_id = int(row["store_id"])
        history = product_history(product_id)
        history_available = history["rolling_avg_7"] is not None
        required_history = ("unit_price", "rolling_avg_7", "rolling_avg_30")
        if not history_available and any(
            pd.isna(row.get(column)) for column in required_history
        ):
            raise RuntimeError(
                f"Product {product_id} has no recorded sales. Supply unit_price, rolling_avg_7, and rolling_avg_30 in the manifest."
            )
        unit_price = float(row.get("unit_price")) if pd.notna(row.get("unit_price")) else history["unit_price"]
        promo_value = int(row.get("is_promo")) if pd.notna(row.get("is_promo")) else 0
        average7 = float(row.get("rolling_avg_7")) if pd.notna(row.get("rolling_avg_7")) else history["rolling_avg_7"]
        average30 = float(row.get("rolling_avg_30")) if pd.notna(row.get("rolling_avg_30")) else history["rolling_avg_30"]
        day = int(row.get("day_of_week")) if pd.notna(row.get("day_of_week")) else 1
        payload = build_payload(
            store_id=store_id,
            product_id=product_id,
            unit_price=unit_price,
            is_promo=promo_value,
            rolling_avg_7=average7,
            rolling_avg_30=average30,
            day_of_week=day,
        )
        raw = request_forecast(payload)
        category = product_category(product_id) or "Unknown / General"
        predictions = adjust_predictions(raw, category)
        plan = inventory_plan(predictions, average7, int(row["current_stock"]), 3)
        rows.append(
            {
                "Store ID": store_id,
                "Product ID": product_id,
                "Category": category,
                "Current stock": int(row["current_stock"]),
                "Forecast T+1": predictions["t+1"],
                "Forecast T+2": predictions["t+2"],
                "Forecast T+3": predictions["t+3"],
                "Reorder point": plan["reorder_point"],
                "Suggested order": plan["order_quantity"],
                "Status": "Review replenishment" if plan["order_quantity"] else "Above reorder point",
            }
        )
    return pd.DataFrame(rows)


def render() -> None:
    page_heading(
        "REPORTING",
        "Reports & bulk operations",
        "Download a planning brief, validate an inventory manifest, and run the existing forecast service over a batch.",
    )
    report_tab, bulk_tab, activity_tab = st.tabs(["Forecast report", "Bulk planning", "System activity"])
    forecast = st.session_state.get("last_forecast")

    with report_tab:
        if forecast is None:
            st.info("Generate a forecast before creating a product-specific PDF brief.")
        else:
            st.markdown(
                f"Latest plan: product **{forecast['product_id']}**, hub **{forecast['store_id']}**, "
                f"forecast generated **{forecast['created_at']}**."
            )
            st.download_button(
                "Download executive forecast PDF",
                data=generate_forecast_pdf(forecast),
                file_name=f"forecast_product_{forecast['product_id']}_hub_{forecast['store_id']}.pdf",
                mime="application/pdf",
            )
            st.caption("The brief reports this session's forecast and stock assumptions.")

    with bulk_tab:
        st.markdown("#### Upload inventory manifest")
        st.caption(
            "Required CSV columns: store_id, product_id, current_stock. Optional overrides: unit_price, "
            "is_promo, rolling_avg_7, rolling_avg_30, day_of_week. Missing overrides use observed product sales."
        )
        uploaded = st.file_uploader("Choose a CSV manifest", type=["csv"], key="bulk_manifest")
        if uploaded is None:
            st.info("Upload a CSV to review and validate its contents.")
        else:
            try:
                manifest = pd.read_csv(uploaded)
            except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
                st.error(f"Could not read this CSV: {exc}")
            else:
                validation = validate_manifest(manifest)
                if validation:
                    st.error("The manifest needs correction before it can be processed.")
                    for message in validation:
                        st.write(f"- {message}")
                    st.dataframe(manifest.head(10), hide_index=True, width="stretch")
                else:
                    st.success(f"Manifest validated · {len(manifest):,} rows ready.")
                    st.dataframe(manifest.head(10), hide_index=True, width="stretch")
                    if st.button("Run batch forecast", type="primary", key="run_bulk"):
                        try:
                            with st.spinner(f"Running forecasts for {len(manifest):,} rows…"):
                                results = _simulate(manifest)
                        except RuntimeError as exc:
                            st.session_state["forecast_service_online"] = False
                            st.error(f"Batch stopped: {exc}")
                        else:
                            st.session_state["forecast_service_online"] = True
                            st.session_state["bulk_results"] = results
                            st.session_state["unread_alert_count"] = int(
                                (results["Status"] == "Review replenishment").sum()
                            )
                            events = st.session_state.setdefault("planning_activity", [])
                            events.insert(0, {"time": date.today().isoformat(), "event": f"Batch forecast completed for {len(results)} manifest rows."})
                            st.success(f"Batch complete · {len(results):,} products processed.")

        results = st.session_state.get("bulk_results")
        if results is not None:
            st.markdown("#### Latest simulation results")
            st.dataframe(results, hide_index=True, width="stretch")
            csv_data = results.to_csv(index=False).encode("utf-8")
            csv_col, pdf_col = st.columns(2)
            with csv_col:
                st.download_button(
                    "Download results CSV",
                    data=csv_data,
                    file_name="bulk_forecast_results.csv",
                    mime="text/csv",
                )
            with pdf_col:
                st.download_button(
                    "Download results PDF",
                    data=generate_bulk_pdf(results),
                    file_name="bulk_forecast_results.pdf",
                    mime="application/pdf",
                )

    with activity_tab:
        st.markdown("#### Session planning activity")
        activity = st.session_state.get("planning_activity", [])
        if not activity:
            st.info("Forecast and batch events will appear here during this session.")
        else:
            st.dataframe(pd.DataFrame(activity), hide_index=True, width="stretch")
        st.caption("These are local session events. No external webhook or purchase-order system is connected.")
