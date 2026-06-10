"""Streamlit dashboard — main entry point."""

import streamlit as st

from dashboard.views.daily_plan import render as render_daily_plan

st.set_page_config(
    page_title="LinkedIn Engagement Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 LinkedIn Engagement Dashboard")

tabs = st.tabs(["📋 Daily Plan", "📈 Analytics", "👥 Leads"])

with tabs[0]:
    render_daily_plan()

with tabs[1]:
    st.header("📈 Analytics")
    st.info("Analytics tab — coming in Phase 2.")

with tabs[2]:
    st.header("👥 Leads")
    st.info("Leads tab — coming in Phase 2.")