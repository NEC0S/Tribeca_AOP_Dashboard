import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.helper import (
    plot_fy_metric,
    compute_monthly_html_table,
    get_financial_year_start,
    get_last_completed_month,
    get_quarter_start,
    safe_parse_dm_inflows,
    find_invalid_months
)

def render_target_dashboard(target_df, expense_df, today):
    # Check and warn for invalid month spellings
    # --- Step 1: Validate and Create 'monthstart' from 'month' and 'year' ---

    target_df.columns = target_df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)

    if 'month' in target_df.columns and 'year' in target_df.columns:
        # Normalize 'month' values and check for typos
        target_df['month'] = target_df['month'].astype(str).str.strip().str.title()
        invalid_months = find_invalid_months(target_df['month'])

        if invalid_months:
            st.warning(f"⚠️ The following month values are invalid: {', '.join(map(str, invalid_months))}")
            st.stop()
        
        # Try creating the 'monthstart' column
        try:
            target_df['monthstart'] = pd.to_datetime(target_df['month'] + ' ' + target_df['year'].astype(str), errors='coerce')
        except Exception as e:
            st.error(f"❌ Error parsing 'monthstart': {e}")
            st.stop()

        if target_df['monthstart'].isna().any():
            st.warning("⚠️ Some rows have invalid month/year combinations. Please check the 'month' and 'year' columns.")
            st.stop()
    else:
        st.error("❌ CSV must include 'month' and 'year' columns to compute 'monthstart'.")
        st.stop()


    # Sidebar - File Upload
    target_df.columns = target_df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
    target_df.rename(columns={
        "sales value target": "sales target",
        "actual sales value": "sales achieved",
        "target sales unit": "unit target",
        "actual sales unit": "unit achieved",
        "collection target": "collection target",
        "collection achieved": "collection achieved",
        "monthstart": "monthstart",
        "dm inflow actual": "dm inflow actual",
        "dm inflow target": "dm inflow target",
        "project": "project"

    }, inplace=True)

    required_cols = ["project", "monthstart", "collection target", "collection achieved", "sales target", "sales achieved", "unit target", "unit achieved","dm inflow actual","dm inflow target"]
    if not all(col in target_df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in target_df.columns]
        st.error(f"CSV is missing columns: {', '.join(missing)}")
    else:
        target_df["monthstart"] = pd.to_datetime(target_df["monthstart"])

        # Project Filter
        projects = target_df["project"].unique().tolist()
        selected_project = st.sidebar.selectbox("Select Project", projects)
        target_df = target_df[target_df["project"] == selected_project]

        # Define Periods
        last_month_date = today.replace(day=1) - pd.DateOffset(days=1)

        start_mtd = last_month_date.replace(day=1)
        end_mtd = last_month_date.replace(day=last_month_date.days_in_month)

        q_month = last_month_date.month
        q_year = last_month_date.year
        if q_month in [1, 2, 3]:
            start_qtd = pd.Timestamp(q_year, 1, 1)
            end_qtd = pd.Timestamp(q_year, 3, 31)
        elif q_month in [4, 5, 6]:
            start_qtd = pd.Timestamp(q_year, 4, 1)
            end_qtd = pd.Timestamp(q_year, 6, 30)
        elif q_month in [7, 8, 9]:
            start_qtd = pd.Timestamp(q_year, 7, 1)
            end_qtd = pd.Timestamp(q_year, 9, 30)
        else:
            start_qtd = pd.Timestamp(q_year, 10, 1)
            end_qtd = pd.Timestamp(q_year, 12, 31)




        if last_month_date.month >= 4:
            start_ytd = pd.Timestamp(last_month_date.year, 4, 1)
        else:
            start_ytd = pd.Timestamp(last_month_date.year - 1, 4, 1)
        end_ytd = end_mtd

        # Aggregator
        def compute_metrics(start_date, end_date):
            d = target_df[(target_df["monthstart"] >= start_date) & (target_df["monthstart"] <= end_date)]
            result = {}
            for metric, target_col, achieved_col in [
                ("Sales Unit", "unit target", "unit achieved"),
                ("Sales Value", "sales target", "sales achieved"),
                ("Collection", "collection target", "collection achieved"),
                ("DM Inflows", "dm inflow target", "dm inflow actual"),
            ]:
                target = d[target_col].sum()
                achieved = d[achieved_col].sum()
                delta = achieved - target
                result[metric] = {
                    "Target": target,
                    "Achieved": achieved,
                    "Delta": delta
                }
            return result

        mtd = compute_metrics(start_mtd, end_mtd)
        qtd = compute_metrics(start_qtd, end_mtd)
        ytd = compute_metrics(start_ytd, end_mtd)

        def display_summary_table(mtd, qtd, ytd):
            st.markdown("### Performance Summary")

            def format_row(label, key):
                return [
                    f"{label}",
                    f"{mtd[key]['Target']:,.0f}", f"{mtd[key]['Achieved']:,.0f}", format_delta(mtd[key]['Delta']),
                    f"{qtd[key]['Target']:,.0f}", f"{qtd[key]['Achieved']:,.0f}", format_delta(qtd[key]['Delta']),
                    f"{ytd[key]['Target']:,.0f}", f"{ytd[key]['Achieved']:,.0f}", format_delta(ytd[key]['Delta'])
                ]

            def format_delta(val):
                if val == "":
                    return ""
                color = "green" if val >= 0 else "red"
                arrow = "↑" if val >= 0 else "↓"
                return f"<span style='color:{color}; font-weight:bold'>{arrow} {val:,.0f}</span>"

            metrics = ["Sales Unit", "Sales Value", "Collection", "DM Inflows"]

            table_html = """
            <style>
                .aop-table th, .aop-table td {
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: center;
                }
                .aop-table {
                    border-collapse: collapse;
                    width: 100%;
                    font-size: 14px;
                }
                .aop-header {
                    background-color: #f2f2f2;
                    font-weight: bold;
                }
            </style>

            <table class='aop-table'>
                <tr class='aop-header'>
                    <th rowspan='2'>Metric</th>
                    <th colspan='3'>MTD</th>
                    <th colspan='3'>QTD</th>
                    <th colspan='3'>YTD</th>
                </tr>
                <tr class='aop-header'>
                    <th>Target</th><th>Achieved</th><th>Delta</th>
                    <th>Target</th><th>Achieved</th><th>Delta</th>
                    <th>Target</th><th>Achieved</th><th>Delta</th>
                </tr>
            """

            for metric in metrics:
                row = format_row(metric, metric)
                table_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"

            table_html += "</table>"

            st.markdown(table_html, unsafe_allow_html=True)

        display_summary_table(mtd, qtd, ytd)

        st.caption("MTD = Last completed month | QTD = Current quarter till last completed month | YTD = Financial year till last completed month ")


    # Fiscal logic
    # Today’s date
    this_month = today.month

    # Determine the correct FY to show: always one FY behind current month
    # e.g., if today is April 2025, show Apr 2023 to Mar 2024
    if this_month == 4:  # April → go one year back
        fy_start = pd.Timestamp(today.year - 1, 4, 1)
    else:  # May–March → current year FY start
        fy_start = pd.Timestamp(today.year if this_month > 4 else today.year - 1, 4, 1)

    fy_end = fy_start.replace(year=fy_start.year + 1) - pd.DateOffset(days=1)  # Mar 31 next year

    # Now generate months from Apr to Mar
    months_list = pd.date_range(start=fy_start, end=fy_end, freq='MS')
    fy_year = fy_start.year
    st.markdown(f"### Monthly Breakdown Table (FY Apr {fy_year}–Mar {fy_year+1})", unsafe_allow_html=True)


    for metric, t_col, a_col in [
        ("Sales Unit", "unit target", "unit achieved"),
        ("Sales Value", "sales target", "sales achieved"),
        ("Collection", "collection target", "collection achieved"),
        ("DM Inflows", "dm inflow target", "dm inflow actual")
    ]:
        html_table = compute_monthly_html_table(target_df, months_list, metric, t_col, a_col)
        st.markdown(html_table, unsafe_allow_html=True)

        # 🔷 Plot Below the Table
        fig = plot_fy_metric(target_df, months_list, metric, t_col, a_col)
        st.plotly_chart(fig, use_container_width=True)

