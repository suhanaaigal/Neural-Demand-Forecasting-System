from __future__ import annotations

import streamlit as st

from demand_dashboard.components import page_heading
from demand_dashboard.services import CORE_CATEGORIES, connect_db, load_registry


def _save_product(product_id: int, category: str) -> None:
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO product_metadata (product_id, category) VALUES (?, ?)
            ON CONFLICT(product_id) DO UPDATE SET category = excluded.category
            """,
            (int(product_id), category.strip()),
        )


def render() -> None:
    page_heading(
        "MASTER DATA",
        "SKU registry",
        "Search, filter, review, and maintain the product-to-category mapping used by forecasting and portfolio views.",
    )
    registry = load_registry()
    st.metric("Registered products", f"{len(registry):,}")
    search_col, category_col = st.columns([1.5, 1])
    with search_col:
        search = st.text_input("Search product or category", placeholder="Enter an ID or category name")
    with category_col:
        categories = ["All categories"] + sorted(registry["Category"].dropna().unique().tolist())
        selected_category = st.selectbox("Filter by category", categories)

    visible = registry.copy()
    if search.strip():
        matching = (
            visible["Product ID"].astype(str).str.contains(search.strip(), case=False, regex=False)
            | visible["Category"].astype(str).str.contains(search.strip(), case=False, regex=False)
        )
        visible = visible.loc[matching]
    if selected_category != "All categories":
        visible = visible.loc[visible["Category"] == selected_category]

    st.dataframe(visible, hide_index=True, width="stretch")
    if visible.empty:
        st.info("No products match these filters.")

    view_tab, edit_tab, delete_tab = st.tabs(["View product", "Add / edit", "Delete"])
    with view_tab:
        if registry.empty:
            st.info("No products are registered.")
        else:
            product_id = st.selectbox("Select a product", registry["Product ID"].astype(int).tolist(), key="view_product_id")
            row = registry.loc[registry["Product ID"] == product_id].iloc[0]
            first, second = st.columns(2)
            first.metric("Product ID", str(product_id))
            second.metric("Category", str(row["Category"]))
            st.caption("Registry changes are synchronized to the shared SQLite product_metadata table.")

    with edit_tab:
        mode = st.radio("Operation", ["Add product", "Edit category"], horizontal=True, key="registry_edit_mode")
        existing_ids = registry["Product ID"].astype(int).tolist()
        if mode == "Add product":
            next_product_id = max(existing_ids, default=100) + 1
            product_id = st.number_input("New product ID", min_value=1, value=next_product_id, step=1, key="registry_add_id")
            if int(product_id) in existing_ids:
                st.warning("This product ID already exists. Choose Edit category instead.")
        else:
            if not existing_ids:
                st.info("Add a product before editing its category.")
                return
            product_id = st.selectbox("Product to edit", existing_ids, key="registry_edit_id")
        category_options = CORE_CATEGORIES + ["Custom category"]
        chosen = st.selectbox("Category", category_options, key="registry_category")
        category = (
            st.text_input("Custom category name", key="registry_custom_category")
            if chosen == "Custom category"
            else chosen
        )
        if st.button("Save registry changes", type="primary", key="registry_save"):
            if not category.strip():
                st.error("Enter a category name.")
            elif mode == "Add product" and int(product_id) in existing_ids:
                st.error("That product ID is already registered.")
            else:
                _save_product(int(product_id), category)
                st.success(f"Product {product_id} is saved under {category.strip()}.")
                st.rerun()

    with delete_tab:
        if registry.empty:
            st.info("There are no registered products to delete.")
        else:
            product_id = st.selectbox(
                "Product to delete",
                registry["Product ID"].astype(int).tolist(),
                key="registry_delete_id",
            )
            row = registry.loc[registry["Product ID"] == product_id].iloc[0]
            st.warning(f"Delete product {product_id} ({row['Category']}) from the SKU registry? This cannot be undone.")
            confirmed = st.checkbox("I confirm this registry deletion", key=f"confirm_delete_{product_id}")
            if st.button("Delete product", type="secondary", disabled=not confirmed, key="registry_delete"):
                with connect_db() as conn:
                    conn.execute("DELETE FROM product_metadata WHERE product_id = ?", (int(product_id),))
                st.success(f"Product {product_id} was removed from the registry.")
                st.rerun()
