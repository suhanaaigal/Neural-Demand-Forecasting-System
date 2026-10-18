from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def page_heading(section: str, title: str, description: str) -> None:
    st.markdown(f'<p class="eyebrow">{section}</p>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def metric_row(items: list[tuple[str, str, str | None]]) -> None:
    for start in range(0, len(items), 3):
        row = items[start : start + 3]
        columns = st.columns(len(row))
        for column, (label, value, help_text) in zip(columns, row):
            column.metric(label, value, help=help_text)


def go_to(label: str, destination: str, *, key: str, primary: bool = False) -> None:
    st.button(
        label,
        key=key,
        type="primary" if primary else "secondary",
        width="stretch",
        on_click=lambda: st.session_state.update(workspace_navigation=destination),
    )


def empty_state(title: str, detail: str, action: Callable[[], None] | None = None) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(detail)
        if action is not None:
            action()
