from __future__ import annotations

from datetime import datetime

import streamlit as st

from demand_dashboard.pages import (
    render_analytics,
    render_forecast,
    render_inventory,
    render_overview,
    render_portfolio,
    render_registry,
    render_reports,
)
from demand_dashboard.services import initialize_database


PAGES = {
    "Overview": ("⌂", render_overview),
    "Demand forecasting": ("↗", render_forecast),
    "Inventory & replenishment": ("▦", render_inventory),
    "SKU registry": ("▤", render_registry),
    "ABC / XYZ portfolio": ("◫", render_portfolio),
    "Pricing & analytics": ("⌁", render_analytics),
    "Reports & bulk operations": ("⇩", render_reports),
}


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        .stApp { background: #f4f7fb; color: #17243a; }
        [data-testid="stHeader"] { background: rgba(255,255,255,.96); }
        [data-testid="stMainBlockContainer"] {
            max-width: 1360px;
            padding: 2rem clamp(1rem, 3vw, 2.5rem) 3rem;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid #203854;
            background: #142941;
            color: #e7eef8;
        }
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button {
            visibility: visible !important;
        }
        [data-testid="stSidebarCollapseButton"] button {
            border-radius: 8px;
            color: #e7eef8;
        }
        [data-testid="stSidebarCollapseButton"] button:focus-visible {
            outline: 2px solid #8bb8f0;
            outline-offset: 2px;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
            background: #142941;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #c4d1e2;
        }
        [data-testid="stSidebar"] h2 { color: #fff; font-size: 1.35rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            margin: .12rem 0;
            padding: .58rem .65rem;
            border-radius: .6rem;
            color: #c4d1e2;
            transition: background-color .15s ease, color .15s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: #203b5a;
            color: #fff;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: #245ca6;
            color: #fff;
        }
        [data-testid="stMainBlockContainer"] h1,
        [data-testid="stMainBlockContainer"] h2,
        [data-testid="stMainBlockContainer"] h3 {
            color: #17243a;
            letter-spacing: -.025em;
        }
        [data-testid="stMainBlockContainer"] h1 {
            margin: .1rem 0 .4rem;
            font-size: clamp(1.9rem, 3vw, 2.35rem);
            line-height: 1.2;
        }
        [data-testid="stMainBlockContainer"] h4 {
            margin: .35rem 0 .85rem;
            color: #24436b;
            font-size: 1.08rem;
            font-weight: 650;
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.2rem;
            padding: .2rem 0 .9rem;
            border-bottom: 1px solid #e5eaf2;
            color: #607089;
            font-size: .88rem;
        }
        .topbar-brand { color: #152743; font-size: 1rem; font-weight: 700; }
        .topbar-right { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; }
        .eyebrow {
            margin: 0 0 .3rem;
            color: #5275ab;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        [data-testid="stMetric"] {
            height: 100%;
            padding: 1rem;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            background: #fff;
            box-shadow: 0 3px 12px rgba(20, 39, 70, .035);
        }
        [data-testid="stMetricLabel"] { color: #64748b; }
        [data-testid="stMetricValue"] { color: #19365f; font-size: 1.8rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e5eaf2;
            border-radius: 12px;
            background: #fff;
            box-shadow: 0 3px 12px rgba(20, 39, 70, .035);
        }
        .stButton > button, [data-testid="stDownloadButton"] > button {
            min-height: 2.6rem;
            border-color: #d7e0ed;
            border-radius: 8px;
            color: #1e3a63;
            font-weight: 600;
        }
        .stButton > button[kind="primary"] {
            border-color: #245ca6;
            background: #245ca6;
            color: white;
        }
        .stButton > button:focus-visible,
        [data-testid="stDownloadButton"] > button:focus-visible {
            outline: 2px solid #245ca6;
            outline-offset: 2px;
        }
        [data-testid="stDataFrame"] { overflow: hidden; border: 1px solid #e5eaf2; border-radius: 11px; }
        [data-testid="stExpander"] { border-color: #e5eaf2; border-radius: 10px; background: #fff; }
        [data-testid="stAlert"] { border-radius: 10px; }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] { padding: 1.5rem .8rem 2rem; }
            .topbar { align-items: flex-start; flex-direction: column; }
            .topbar-right { gap: .4rem .75rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run() -> None:
    st.set_page_config(
        page_title="Demand Intelligence",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="auto",
    )
    _apply_styles()
    initialize_database()

    with st.sidebar:
        st.markdown("## ◈ Demand Intelligence")
        st.caption("Planning & operations workspace")
        st.markdown("---")
        st.caption("WORKSPACES")
        page_names = list(PAGES)
        selected = st.radio(
            "Navigate workspace",
            page_names,
            format_func=lambda name: f"{PAGES[name][0]}  {name}",
            label_visibility="collapsed",
            key="workspace_navigation",
        )
        st.markdown("---")
        st.caption("Forecasting service")
        service_state = st.session_state.get("forecast_service_online")
        service_label = "● Connected" if service_state is True else "○ Not reachable" if service_state is False else "○ Status on overview"
        st.caption(service_label)

    notification_count = int(st.session_state.get("unread_alert_count", 0))
    st.markdown(
        f'<div class="topbar"><span class="topbar-brand">Demand Intelligence</span>'
        f'<div class="topbar-right"><span>{datetime.now().strftime("%A, %B %d, %Y")}</span>'
        f'<span title="Planning alerts">🔔 {notification_count} alerts</span>'
        f'<span>◉ Operations user</span></div></div>',
        unsafe_allow_html=True,
    )

    PAGES[selected][1]()
