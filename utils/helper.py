import streamlit as st
import pandas as pd
import plotly.graph_objects as go

valid_months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def find_invalid_months(month_series):
    """
    Checks a pandas Series of month names for invalid values.
    Returns a list of invalid month names (after stripping and title-casing).
    """
    seen = set()
    invalid_months = []
    for raw_month in month_series.dropna().unique():
        month = str(raw_month).strip().title()
        if month not in valid_months and month not in seen:
            invalid_months.append(raw_month)
            seen.add(month)
    return invalid_months



def get_financial_year_start(current_date):
    return pd.Timestamp(year=current_date.year if current_date.month >= 4 else current_date.year - 1, month=4, day=1)

def get_financial_year_start(current_date):
    return pd.Timestamp(year=current_date.year if current_date.month >= 4 else current_date.year - 1, month=4, day=1)

def get_last_completed_month(today):
    return today.replace(day=1) - pd.DateOffset(days=1)

def get_quarter_start(current_date):
    month = current_date.month
    if month in [4, 5, 6]: return pd.Timestamp(current_date.year, 4, 1)
    elif month in [7, 8, 9]: return pd.Timestamp(current_date.year, 7, 1)
    elif month in [10, 11, 12]: return pd.Timestamp(current_date.year, 10, 1)
    else: return pd.Timestamp(current_date.year, 1, 1)

def safe_parse_dm_inflows(df):
    if "dm inflows actual" in df.columns:
        df["DM Inflows achieved"] = pd.to_numeric(df["dm inflows actual"], errors="coerce")
    if "dm inflows target" in df.columns:
        df["DM Inflows target"] = pd.to_numeric(df["dm inflows target"], errors="coerce")
    return df
def compute_monthly_html_table(df, months_list, metric_name, target_col, achieved_col):
        month_names = [dt.strftime('%b-%y') for dt in months_list]

        html = f"<h4 style='margin-top: 30px;'>{metric_name}</h4>"
        html += """
        <table style='border-collapse: collapse; font-size: 16px; width: 100%;'>
            <thead>
                <tr>
                    <th style='padding:10px;border:1px solid #ddd;text-align:left;'>Type</th>
        """
        for m in month_names:
            html += f"<th style='padding:10px;border:1px solid #ddd;text-align:center;'>{m}</th>"
        html += "</tr></thead><tbody>"

        for row_type in ["Target", "Achieved", "Delta"]:
            html += f"<tr><td style='padding:10px;border:1px solid #ddd; font-weight: bold;'>{row_type}</td>"
            for dt in months_list:
                month_data = df[df["monthstart"] == dt]
                target = month_data[target_col].sum() if not month_data.empty else ""
                achieved = month_data[achieved_col].sum() if not month_data.empty else ""
                delta = achieved - target if target != "" and achieved != "" else ""

                if row_type == "Target":
                    value = f"{target:,.0f}" if target != "" else ""
                    html += f"<td style='padding:10px;border:1px solid #ddd; text-align:center;'>{value}</td>"
                elif row_type == "Achieved":
                    value = f"{achieved:,.0f}" if achieved != "" else ""
                    html += f"<td style='padding:10px;border:1px solid #ddd; text-align:center;'>{value}</td>"
                else:
                    if delta == "":
                        html += "<td style='padding:10px;border:1px solid #ddd;'></td>"
                    else:
                        color = "green" if delta >= 0 else "red"
                        arrow = "↑" if delta >= 0 else "↓"
                        html += f"<td style='padding:10px;border:1px solid #ddd; text-align:center; color:{color}; font-weight:bold;'>{arrow} {delta:,.0f}</td>"
            html += "</tr>"
        html += "</tbody></table><br>"
        return html
def plot_fy_metric(df, months_list, metric_name, target_col, achieved_col):
        # Prepare data
        month_labels = [dt.strftime('%b-%y') for dt in months_list]
        targets, achieveds = [], []

        for dt in months_list:
            month_data = df[df["monthstart"] == dt]
            target = month_data[target_col].sum() if not month_data.empty else None
            achieved = month_data[achieved_col].sum() if not month_data.empty else None

            targets.append(target)
            achieveds.append(achieved)

        # Build base figure
        fig = go.Figure()

        # Line 1: Target
        fig.add_trace(go.Scatter(
            x=month_labels,
            y=targets,
            mode='lines+markers',
            name='Target',
            line=dict(color='#ff7f0e'),
            marker=dict(size=6)
        ))

        # Line 2: Achieved
        fig.add_trace(go.Scatter(
            x=month_labels,
            y=achieveds,
            mode='lines+markers',
            name='Achieved',
            line=dict(color='#1f77b4'),
            marker=dict(size=6)
        ))

        for i, (x, t, a) in enumerate(zip(month_labels, targets, achieveds)):
            if t is not None and a is not None:
                color = "green" if a >= t else "red"
                fig.add_annotation(
                    x=x,
                    y=a,
                    ax=x,
                    ay=t,
                    xref="x",
                    yref="y",
                    axref="x",
                    ayref="y",
                    showarrow=True,
                    arrowhead=5,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=color,
                    opacity=0.2,
                    hovertext=f"Delta: {a - t:,.0f}",
                    hoverlabel=dict(bgcolor=color)
                )


        fig.update_layout(
            title=f"{metric_name} – Target vs Achieved with Delta",
            xaxis_title="Month",
            yaxis_title=metric_name,
            height=420,
            margin=dict(t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        return fig

















def get_fy_start(date):
        return pd.Timestamp(date.year if date.month >= 4 else date.year - 1, 4, 1)

def get_qtr_start(date):
    month = date.month
    if month in [4, 5, 6]: return pd.Timestamp(date.year, 4, 1)
    if month in [7, 8, 9]: return pd.Timestamp(date.year, 7, 1)
    if month in [10, 11, 12]: return pd.Timestamp(date.year, 10, 1)
    return pd.Timestamp(date.year, 1, 1)

def compute_metrics(df, start_date, end_date, inflow_col, expense_cols):
    data = df[(df["month"] >= start_date) & (df["month"] <= end_date)].copy()
    # Ensure numeric types
    data[inflow_col] = pd.to_numeric(data[inflow_col], errors='coerce')
    data[expense_cols] = data[expense_cols].apply(pd.to_numeric, errors='coerce')
    total_inflow = data[inflow_col].sum()
    expenses = data[expense_cols].sum()
    total_outflow = expenses.sum()
    net_cash = total_inflow - total_outflow
    return total_inflow, expenses, total_outflow, net_cash

def style_delta(val):
    color = "green" if val >= 0 else "red"
    arrow = "↑" if val >= 0 else "↓"
    return f"<span style='color:{color}; font-weight:bold'>{arrow} {val:,.0f}</span>"


