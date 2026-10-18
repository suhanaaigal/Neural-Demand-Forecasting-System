from __future__ import annotations

import io
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "corporate_sales.db"
FORECAST_ENDPOINT = os.environ.get("DEMAND_FORECAST_URL", "http://127.0.0.1:8000/predict_sequence")
FORECAST_TIMEOUT_SECONDS = float(os.environ.get("DEMAND_FORECAST_TIMEOUT_SECONDS", "20"))
CORE_CATEGORIES = ["Electronics", "Groceries", "Pharmaceuticals", "Home & Kitchen", "Apparel"]
ATTENTION_PROFILE = {
    "Historical price": 0.12,
    "Promotion status": 0.28,
    "7-day average": 0.35,
    "30-day average": 0.18,
    "Day of week": 0.07,
}


@contextmanager
def connect_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_metadata (
                product_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO product_metadata (product_id, category) VALUES (?, ?)",
            [
                (101, "Electronics"),
                (102, "Groceries"),
                (103, "Pharmaceuticals"),
                (104, "Home & Kitchen"),
                (105, "Apparel"),
            ],
        )


def load_registry() -> pd.DataFrame:
    with connect_db() as conn:
        return pd.read_sql_query(
            "SELECT product_id AS [Product ID], category AS Category FROM product_metadata ORDER BY product_id",
            conn,
        )


def load_products() -> pd.DataFrame:
    with connect_db() as conn:
        return pd.read_sql_query(
            """
            SELECT m.product_id, m.category,
                   AVG(t.unit_price) AS avg_price,
                   AVG(t.units_sold) AS avg_demand,
                   MAX(t.date) AS last_sale
            FROM product_metadata m
            LEFT JOIN raw_transactions t ON t.product_id = m.product_id
            GROUP BY m.product_id, m.category
            ORDER BY m.product_id
            """,
            conn,
        )


def load_sales_daily(
    product_id: int | None = None,
    store_id: int | None = None,
    days: int = 30,
) -> pd.DataFrame:
    conditions = ["date >= COALESCE((SELECT date(MAX(date), ?) FROM raw_transactions), ?)"]
    values: list[Any] = [f"-{max(0, days - 1)} days", (date.today() - timedelta(days=days)).isoformat()]
    if product_id is not None:
        conditions.append("product_id = ?")
        values.append(int(product_id))
    if store_id is not None:
        conditions.append("store_id = ?")
        values.append(int(store_id))
    query = f"""
        SELECT date, SUM(units_sold) AS units_sold, SUM(units_sold * unit_price) AS revenue
        FROM raw_transactions
        WHERE {' AND '.join(conditions)}
        GROUP BY date
        ORDER BY date
    """
    with connect_db() as conn:
        return pd.read_sql_query(query, conn, params=values, parse_dates=["date"])


def load_recent_sales(limit: int = 8) -> pd.DataFrame:
    with connect_db() as conn:
        return pd.read_sql_query(
            """
            SELECT t.date AS Date, t.store_id AS Hub, t.product_id AS [Product ID],
                   m.category AS Category, t.units_sold AS Units,
                   ROUND(t.units_sold * t.unit_price, 2) AS Revenue
            FROM raw_transactions t
            LEFT JOIN product_metadata m ON t.product_id = m.product_id
            ORDER BY t.date DESC, t.transaction_id DESC
            LIMIT ?
            """,
            conn,
            params=(int(limit),),
        )


def load_dimension_values(column: str) -> list[int]:
    if column not in {"store_id", "product_id"}:
        raise ValueError("Unsupported sales dimension")
    with connect_db() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM raw_transactions ORDER BY {column}"
        ).fetchall()
    return [int(row[0]) for row in rows]


def product_category(product_id: int) -> str | None:
    with connect_db() as conn:
        row = conn.execute(
            "SELECT category FROM product_metadata WHERE product_id = ?",
            (int(product_id),),
        ).fetchone()
    return str(row[0]) if row else None


def product_history(product_id: int, days: int = 30) -> dict[str, float | None]:
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT AVG(unit_price), AVG(is_promo), AVG(units_sold)
            FROM raw_transactions
            WHERE product_id = ?
              AND date >= COALESCE((SELECT date(MAX(date), ?) FROM raw_transactions), ?)
            """,
            (int(product_id), f"-{max(0, days - 1)} days", (date.today() - timedelta(days=days)).isoformat()),
        ).fetchone()
    if not row or row[2] is None:
        return {"unit_price": None, "is_promo": None, "rolling_avg_7": None, "rolling_avg_30": None}
    price = float(row[0] or 0.0)
    average = float(row[2] or 0.0)
    return {
        "unit_price": price,
        "is_promo": float(row[1] or 0.0),
        "rolling_avg_7": average,
        "rolling_avg_30": average,
    }


def classify_category(product_id: int, category: str) -> tuple[str, str, str]:
    if category in {"Electronics", "Pharmaceuticals"}:
        return "A", "X", "Tight control and frequent review"
    if category == "Groceries":
        return "A", "Y", "Maintain a higher safety-stock buffer"
    if category == "Apparel":
        return "B", "Z", "Use promotion-aware replenishment"
    if category == "Home & Kitchen":
        return "C", "Y", "Consolidate orders where practical"
    abc = "B" if int(product_id) % 2 == 0 else "C"
    return abc, "Z", "Review demand before replenishing"


def request_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(FORECAST_ENDPOINT, json=payload, timeout=FORECAST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Forecast service is unavailable: {exc}") from exc

    try:
        result = response.json()
        predictions = result["predictions"]
        forecasts = {horizon: int(predictions[horizon]) for horizon in ("t+1", "t+2", "t+3")}
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Forecast service returned an invalid response.") from exc

    return forecasts


def adjust_predictions(raw: dict[str, int], category: str) -> dict[str, int]:
    multipliers = {
        "Apparel": (1.5, 1.4, 1.3),
        "Groceries": (2.1, 2.0, 1.9),
    }.get(category, (1.0, 1.0, 1.0))
    return {
        horizon: int(raw[horizon] * multiplier)
        for horizon, multiplier in zip(("t+1", "t+2", "t+3"), multipliers)
    }


def pricing_scenarios(base_price: float, day_one_demand: int) -> tuple[pd.DataFrame, float, float]:
    elasticity = -1.45
    rows = []
    for change in (-20, -10, 0, 10, 20):
        price = base_price * (1 + change / 100)
        demand = max(5, int(day_one_demand * (1 + change / 100 * elasticity)))
        rows.append((f"{change:+}%", round(price, 2), demand, round(price * demand, 2)))
    frame = pd.DataFrame(
        rows,
        columns=["Price change", "Scenario price (₹)", "Projected T+1 demand", "Estimated revenue (₹)"],
    )
    best_price = float(frame.loc[frame["Estimated revenue (₹)"].idxmax(), "Scenario price (₹)"])
    return frame, best_price, elasticity


def inventory_plan(predictions: dict[str, int], average_week: float, stock: int, lead_time: int) -> dict[str, int | float]:
    average_forecast = sum(predictions.values()) / 3
    reorder_point = int(average_forecast * lead_time + int(average_week * 1.5))
    order_quantity = max(0, reorder_point - stock)
    return {
        "reorder_point": reorder_point,
        "order_quantity": order_quantity,
        "stock": stock,
        "lead_time": lead_time,
        "stockout_risk": max(0, reorder_point - stock) * 12.0,
        "holding_cost": max(0, stock - reorder_point) * 1.5,
    }


def generate_forecast_pdf(forecast: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=20, textColor=colors.HexColor("#17365f"), spaceAfter=14)
    body = ParagraphStyle("ReportBody", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8)
    story = [
        Paragraph("Demand Intelligence — Forecast & Replenishment Brief", title),
        Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y %H:%M')}", body),
        Paragraph(
            f"Product {forecast['product_id']} · {escape(str(forecast['category']))} · Hub {forecast['store_id']}",
            body,
        ),
        Spacer(1, 12),
    ]
    plan = forecast["inventory"]
    data = [
        ["Measure", "Value"],
        ["Unit price", f"INR {forecast['unit_price']:,.2f}"],
        ["Forecast demand (T+1 / T+2 / T+3)", " / ".join(str(forecast["predictions"][h]) for h in ("t+1", "t+2", "t+3"))],
        ["Current stock supplied for this plan", f"{plan['stock']} units"],
        ["Supplier lead time", f"{plan['lead_time']} days"],
        ["Reorder point", f"{plan['reorder_point']} units"],
        ["Suggested order quantity", f"{plan['order_quantity']} units"],
        ["Recommended price scenario", f"INR {forecast['recommended_price']:,.2f}"],
        ["Stockout exposure estimate", f"INR {plan['stockout_risk']:,.2f}"],
        ["Excess-stock carrying estimate", f"INR {plan['holding_cost']:,.2f}"],
    ]
    table = Table(data, colWidths=[265, 235])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365f")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8e0ec")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Inventory valuation and purchase-order execution are not connected to this application.", body))
    doc.build(story)
    return buffer.getvalue()


def generate_bulk_pdf(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=24, leftMargin=24, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Demand Intelligence — Bulk Planning Results", styles["Title"]),
        Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y %H:%M')}", styles["Normal"]),
        Spacer(1, 12),
    ]
    data = [list(frame.columns)] + frame.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f8")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8e0ec")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def validate_manifest(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    required = {"store_id", "product_id", "current_stock"}
    missing = sorted(required - set(frame.columns))
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}."]
    if frame.empty:
        return ["The uploaded manifest has no rows."]

    numeric_columns = required | {
        "unit_price",
        "is_promo",
        "rolling_avg_7",
        "rolling_avg_30",
        "day_of_week",
    }
    for column in numeric_columns & set(frame.columns):
        values = pd.to_numeric(frame[column], errors="coerce")
        required_column = column in required
        missing_values = values.isna() if required_column else (frame[column].notna() & values.isna())
        bad_rows = values[missing_values].index.tolist()
        if bad_rows:
            errors.append(f"{column}: missing or non-numeric values on CSV row(s) {', '.join(str(i + 2) for i in bad_rows[:8])}.")
            continue
        checked_values = values.dropna()
        if not np.isfinite(checked_values.to_numpy(dtype=float)).all():
            errors.append(f"{column}: values must be finite.")
        if column in {"store_id", "product_id", "current_stock", "is_promo", "day_of_week"}:
            if not np.equal(checked_values, np.floor(checked_values)).all():
                errors.append(f"{column}: values must be whole numbers.")
        if column in {"store_id", "product_id"} and (checked_values < 1).any():
            errors.append(f"{column}: values must be at least 1.")
        if column in {"current_stock", "unit_price", "rolling_avg_7", "rolling_avg_30"} and (checked_values < 0).any():
            errors.append(f"{column}: values cannot be negative.")
        if column == "is_promo" and not checked_values.isin([0, 1]).all():
            errors.append("is_promo: use 0 or 1.")
        if column == "day_of_week" and not checked_values.between(0, 6).all():
            errors.append("day_of_week: use a value from 0 (Sunday) to 6 (Saturday).")
    return errors


def build_payload(
    *,
    store_id: int,
    product_id: int,
    unit_price: float,
    is_promo: int,
    rolling_avg_7: float,
    rolling_avg_30: float,
    day_of_week: int,
) -> dict[str, Any]:
    return {
        "store_id": int(store_id),
        "product_id": int(product_id),
        "unit_price_history": [float(unit_price)] * 7,
        "is_promo_history": [0, 0, 0, 0, 0, int(is_promo), int(is_promo)],
        "rolling_avg_7_history": [float(rolling_avg_7)] * 7,
        "rolling_avg_30_history": [float(rolling_avg_30)] * 7,
        "day_of_week_history": [int(day_of_week)] * 7,
    }
