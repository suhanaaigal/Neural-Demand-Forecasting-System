from __future__ import annotations

import pandas as pd
import streamlit as st

from demand_dashboard.components import page_heading
from demand_dashboard.services import classify_category, load_products, load_registry


CLASS_GUIDE = pd.DataFrame(
    [
        ("A", "Higher revenue-impact class", "Prioritise service levels and frequent review"),
        ("B", "Intermediate revenue-impact class", "Balance availability and working capital"),
        ("C", "Lower revenue-impact class", "Use simple controls and consolidated orders"),
        ("X", "Stable category-rule class", "Routine replenishment review"),
        ("Y", "Variable category-rule class", "Maintain suitable safety stock"),
        ("Z", "Erratic category-rule class", "Review before replenishment"),
    ],
    columns=["Class", "Definition", "Planning interpretation"],
)


def render() -> None:
    page_heading(
        "PORTFOLIO",
        "ABC / XYZ portfolio",
        "Explore the existing category-based portfolio classification and its recommended inventory strategies.",
    )
    products = load_products()
    if products.empty:
        st.info("Add products to the SKU registry to populate the portfolio.")
        return

    products["Product ID"] = products["product_id"].astype(int)
    classified = products.apply(
        lambda row: classify_category(row["Product ID"], str(row["category"])),
        axis=1,
        result_type="expand",
    )
    classified.columns = ["ABC class", "XYZ class", "Recommended strategy"]
    table = pd.concat(
        [
            products[["Product ID", "category"]].rename(columns={"category": "Category"}),
            classified,
        ],
        axis=1,
    )
    counts = table.groupby(["ABC class", "XYZ class"]).size()
    matrix = pd.DataFrame(
        {
            xyz: [int(counts.get((abc, xyz), 0)) for abc in ("A", "B", "C")]
            for xyz in ("X", "Y", "Z")
        },
        index=["A", "B", "C"],
    )
    matrix.index.name = "ABC class"
    st.subheader("Portfolio matrix · registered SKU counts")
    st.caption("Classes retain the application's existing category-based assignment rules.")
    st.dataframe(matrix, width="stretch")
    st.markdown("#### Classification definitions")
    st.dataframe(CLASS_GUIDE, hide_index=True, width="stretch")

    abc_col, xyz_col, category_col = st.columns(3)
    with abc_col:
        abc_filter = st.selectbox("ABC class", ["All"] + sorted(table["ABC class"].unique()))
    with xyz_col:
        xyz_filter = st.selectbox("XYZ class", ["All"] + sorted(table["XYZ class"].unique()))
    with category_col:
        category_filter = st.selectbox(
            "Category",
            ["All"] + sorted(table["Category"].dropna().unique().tolist()),
        )
    displayed = table
    if abc_filter != "All":
        displayed = displayed[displayed["ABC class"] == abc_filter]
    if xyz_filter != "All":
        displayed = displayed[displayed["XYZ class"] == xyz_filter]
    if category_filter != "All":
        displayed = displayed[displayed["Category"] == category_filter]
    st.markdown("#### Classified products")
    st.dataframe(displayed, hide_index=True, width="stretch")

    abc_counts = table["ABC class"].value_counts()
    xyz_counts = table["XYZ class"].value_counts()
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("ABC-A products", int(abc_counts.get("A", 0)))
    kpi_cols[1].metric("XYZ-Z products", int(xyz_counts.get("Z", 0)))
    kpi_cols[2].metric("Registered SKUs", len(load_registry()))
    st.caption(
        "ABC/XYZ assignments are category rules in the current application; the database does not contain "
        "configured revenue thresholds or variability-classification parameters."
    )
