import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
import textwrap
from utils.helper import (
    get_fy_start,
    get_last_completed_month,
    get_qtr_start,
    find_invalid_months
)

def render_exp_dashboard(expense_df, target_df, today):
    expense_df.columns = expense_df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
    target_df.columns = target_df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)

    required_cols_target_df = ["project", "dm inflow actual", "dm inflow target"]


    expense_df['target'] = pd.to_numeric(expense_df['target'], errors='coerce')
    expense_df['actual'] = pd.to_numeric(expense_df['actual'], errors='coerce')
    expense_df['expense category'] = expense_df['expense category'].str.strip().str.title()
    expense_df['expense'] = expense_df['expense'].str.strip().str.title()

    



    expense_df['month'] = expense_df['month'].astype(str).str.strip().str.title()
    expense_df['year'] = pd.to_numeric(expense_df['year'], errors='coerce')

    # Optional: Validate month names
    invalid_months = find_invalid_months(expense_df['month'])
    if invalid_months:
        st.error(f"Invalid month names in expense_df: {', '.join(invalid_months)}")
        st.stop()

    # Create monthstart
    expense_df['monthstart'] = pd.to_datetime(expense_df['month'] + " " + expense_df['year'].astype(str), errors='coerce')

    
    # Ensure numeric types for target_df
    target_df['year'] = pd.to_numeric(target_df['year'], errors='coerce')
    target_df['dm inflow actual'] = pd.to_numeric(target_df['dm inflow actual'], errors='coerce')
    target_df['dm inflow target'] = pd.to_numeric(target_df['dm inflow target'], errors='coerce')


    ##Warning for the missing columns
    if not all(col in target_df.columns for col in required_cols_target_df):
        missing = [col for col in required_cols_target_df if col not in target_df.columns]
        st.error(f"CSV is missing columns: {', '.join(missing)}")
        return
    

    if 'month' in target_df.columns and 'year' in target_df.columns:
        # Normalize 'month' values and check for typos
        target_df['month'] = target_df['month'].astype(str).str.strip().str.title()
        target_df['year'] = pd.to_numeric(target_df['year'], errors='coerce')
        target_df['dm inflow actual'] = pd.to_numeric(target_df['dm inflow actual'], errors='coerce')
        target_df['dm inflow target'] = pd.to_numeric(target_df['dm inflow target'], errors='coerce')

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

    target_df["monthstart"] = pd.to_datetime(target_df["monthstart"])



    # Time periods (last completed month)
    last_month_date = today.replace(day=1) - pd.DateOffset(days=1)
    start_mtd = last_month_date.replace(day=1)
    end_mtd = last_month_date

    # QTD
    q_month = last_month_date.month
    q_year = last_month_date.year
    if q_month <= 3:
        start_qtd = pd.Timestamp(q_year, 1, 1)
    elif q_month <= 6:
        start_qtd = pd.Timestamp(q_year, 4, 1)
    elif q_month <= 9:
        start_qtd = pd.Timestamp(q_year, 7, 1)
    else:
        start_qtd = pd.Timestamp(q_year, 10, 1)
    end_qtd = end_mtd

    # YTD
    if last_month_date.month >= 4:
        start_ytd = pd.Timestamp(last_month_date.year, 4, 1)
    else:
        start_ytd = pd.Timestamp(last_month_date.year - 1, 4, 1)
    end_ytd = end_mtd


    required_cols = {"expense", "month", "year", "actual", "target"}
    if not required_cols.issubset(set(expense_df.columns)):
        st.error(f"CSV must contain columns: {required_cols}")
        st.stop()


    df_melted = expense_df.melt(
        id_vars=["month", "year", "expense", "expense category"],
        value_vars=["actual", "target"],
        var_name="type",
        value_name="value"
    )

    df_melted["value"] = pd.to_numeric(df_melted["value"], errors="coerce")
    # Step 3: Pivot to get one column per (category, type)
    df_pivot = df_melted.pivot_table(
        index=["month", "year"],
        columns=["expense", "type"],
        values="value"
    ).reset_index()

    # Step 4: Flatten multi-level column names
    df_pivot.columns = [
    f"{col[0].lower()}_{col[1].lower()}" if isinstance(col, tuple) else col
    for col in df_pivot.columns
]

    # ✅ Rename 'month_' and 'year_' back to 'month' and 'year' if they exist
    df_pivot.rename(columns={"month_": "month", "year_": "year"}, inplace=True)

    # ✅ Now you can safely create the datetime column
    df_pivot["month"] = pd.to_datetime(
        df_pivot["year"].astype(str) + "-" + df_pivot["month"].astype(str).str.zfill(2) + "-01"
    )


    # After df_pivot["month"] = pd.to_datetime(...)
    for col in df_pivot.columns:
        if any(x in col for x in ["actual", "target"]):
            df_pivot[col] = pd.to_numeric(df_pivot[col], errors='coerce')


    # Step 6: Standardize column names
    df_pivot.columns = df_pivot.columns.str.strip().str.lower()

    # Step 7: Rename final DataFrame to `df` for consistency
    df = df_pivot.copy()

    # Step 8: Get list of actual expense columns
    expense_cols = [
        col for col in df.columns if any(x in col for x in [
            "salary", "legal and professional", "rent", "hotel & travel expenses",
            "marketing exp.", "misc expenses", "investments", "capex"
        ]) and "actual" in col
    ]

    # Step 9: Optional - Compute total actual expense
    df["total_actual_expense"] = df[expense_cols].sum(axis=1)
    # Create 'month' datetime column for filtering

    # Grouped inflow data
    df_ = (
        target_df.groupby(["project", "year", "month", "monthstart"], as_index=False)
        .agg({"dm inflow actual": "sum"})
        .rename(columns={"dm inflow actual": "inflow"})
    )




    # Create 'month' datetime column for filtering
    df_["month"] = pd.to_datetime(df_["year"].astype(str) + "-" + df_["month"].astype(str).str.zfill(2) + "-01")

    # Standardize column names for consistency
    df_.columns = df_.columns.str.strip().str.lower()



    # ---------- FILTER ----------
    if "project" in df_.columns:
        project_list = df_["project"].dropna().unique().tolist()
        selected_project = st.sidebar.selectbox("Select Project (Expense Dashboard)", ["All Projects"] + project_list)
        if selected_project != "All Projects":
            df_ = df_[df_["project"] == selected_project]

    # Last completed month – e.g., if today is July 11, 2025, then this is June 1, 2025
    last_month = get_last_completed_month(today)

    # ---------- MTD ----------
    start_mtd = last_month.replace(day=1)
    end_mtd = last_month  # Use entire last month

    # ---------- QTD ----------
    start_qtd = get_qtr_start(last_month)
    end_qtd = last_month

    # ---------- YTD ----------
    start_ytd = get_fy_start(last_month)
    end_ytd = last_month


# ---------- SECTION 1: INFLOW DISTRIBUTION COMBINED ----------
    st.subheader("Inflow Distribution by Project")

    # Helper to compute inflow by period
    def get_inflow_by_project(df, start_date, end_date):
        return df[(df["month"] >= start_date) & (df["month"] <= end_date)] \
                .groupby("project")["inflow"].sum()

    # Compute inflow summaries
    inflow_mtd = get_inflow_by_project(df_, start_mtd, end_mtd)
    inflow_qtd = get_inflow_by_project(df_, start_qtd, end_qtd)
    inflow_ytd = get_inflow_by_project(df_, start_ytd, end_ytd)

    # Merge all inflows
    inflow_summary = pd.concat([inflow_mtd, inflow_qtd, inflow_ytd], axis=1)
    inflow_summary.columns = ["MTD Inflow", "QTD Inflow", "YTD Inflow"]
    inflow_summary = inflow_summary.fillna(0).reset_index()

    # ----- Styled HTML Table -----
    inflow_table_html = """
    <style>
        .inflow-table th, .inflow-table td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: center;
        }
        .inflow-table {
            border-collapse: collapse;
            width: 100%;
            font-size: 14px;
            margin-top: 10px;
        }
        .inflow-header {
            background-color: #f2f2f2;
            font-weight: bold;
        }
    </style>

    <table class='inflow-table'>
        <tr class='inflow-header'>
            <th>Project</th>
            <th>MTD Inflow</th>
            <th>QTD Inflow</th>
            <th>YTD Inflow</th>
        </tr>
    """

    # Add each project row
    # Add each project row
    for _, row in inflow_summary.iterrows():
        inflow_table_html += f"""
    <tr>
        <td>{row['project']}</td>
        <td>{row['MTD Inflow']:,.2f}</td>
        <td>{row['QTD Inflow']:,.2f}</td>
        <td>{row['YTD Inflow']:,.2f}</td>
    </tr>
    """

    # 👉 Add Total row
    total_row = inflow_summary[["MTD Inflow", "QTD Inflow", "YTD Inflow"]].sum()
    inflow_table_html += f"""
    <tr style='font-weight:bold; background-color:#f0f0f0'>
        <td><strong>Total</strong></td>
        <td>{total_row['MTD Inflow']:,.2f}</td>
        <td>{total_row['QTD Inflow']:,.2f}</td>
        <td>{total_row['YTD Inflow']:,.2f}</td>
    </tr>
    """

    inflow_table_html += "</table>"

    # Display table
    st.markdown(inflow_table_html, unsafe_allow_html=True)


    # ---------- Plot ----------
    inflow_long = inflow_summary.melt(id_vars="project", 
                                    var_name="Period", 
                                    value_name="Inflow")

    fig = px.bar(
        inflow_long,
        x="project",
        y="Inflow",  # ⚠️ use correct column name with capital 'I'
        color="Period",
        barmode="group",
        text_auto=True,
        title="Inflow by Project – MTD vs QTD vs YTD"
    )

    st.plotly_chart(fig, use_container_width=True)


    # Add expense category back into the flat dict
    def compute_category_sums(expense_df, mtd_exp, qtd_exp, ytd_exp):
        expense_df['expense'] = expense_df['expense'].str.strip().str.title()

        categories = expense_df[['expense', 'expense category']].drop_duplicates().set_index('expense').to_dict()['expense category']

        # Build category-wise groupings
        cat_totals = {}
        for exp, cat in categories.items():
            if cat not in cat_totals:
                cat_totals[cat] = {
                    "MTD": {"Target": 0, "Achieved": 0, "Delta": 0},
                    "QTD": {"Target": 0, "Achieved": 0, "Delta": 0},
                    "YTD": {"Target": 0, "Achieved": 0, "Delta": 0}
                }
            for period, exp_data in zip(["MTD", "QTD", "YTD"], [mtd_exp, qtd_exp, ytd_exp]):
                if exp in exp_data:
                    cat_totals[cat][period]["Target"] += exp_data[exp]["Target"]
                    cat_totals[cat][period]["Achieved"] += exp_data[exp]["Achieved"]
                    cat_totals[cat][period]["Delta"] += exp_data[exp]["Delta"]
        return cat_totals

    # ---------- SECTION 2: EXPENSE SUMMARY (MTD/QTD/YTD) ----------
# ---------- SECTION 2: EXPENSE SUMMARY (MTD/QTD/YTD) ----------
    st.markdown("### Cash Flow Summary")

    # ---------- Format Delta Helper ----------
    def format_delta(val):
        if val == "":
            return ""
        color = "green" if val >= 0 else "red"
        arrow = "↑" if val >= 0 else "↓"
        return f"<span style='color:{color}; font-weight:bold'>{arrow} {val:,.2f}</span>"
    
    def compute_dm_inflows(target_df, start, end):
        d = target_df[(target_df["monthstart"] >= start) & (target_df["monthstart"] <= end)]
        target = d['dm inflow target'].sum()
        actual = d['dm inflow actual'].sum()
        delta = actual - target
        return {"Target": target, "Achieved": actual, "Delta": delta}

    mtd_inflow = compute_dm_inflows(target_df, start_mtd, end_mtd)
    qtd_inflow = compute_dm_inflows(target_df, start_qtd, end_qtd)
    ytd_inflow = compute_dm_inflows(target_df, start_ytd, end_ytd)


    # ---------- Expense Data Processing ----------
    def get_expense_dict(df, start, end):
        filtered = df[(df["month"] >= start) & (df["month"] <= end)]
        result = {}
        for col in expense_cols:
            if "actual" in col:
                expense = col.replace("_actual", "")
                actual_col = col
                target_col = f"{expense}_target"
                if target_col in filtered.columns:
                    actual = pd.to_numeric(filtered[actual_col], errors='coerce').sum()
                    target = pd.to_numeric(filtered[target_col], errors='coerce').sum()
                    delta = actual - target
                    result[expense.title()] = {
                        "Achieved": actual,
                        "Target": target,
                        "Delta": delta
                    }
        return result

    mtd_exp = get_expense_dict(df, start_mtd, end_mtd)
    qtd_exp = get_expense_dict(df, start_qtd, end_qtd)
    ytd_exp = get_expense_dict(df, start_ytd, end_ytd)

    expense_heads = sorted(mtd_exp.keys())

    # Map each expense head to its category
    category_map = expense_df[['expense', 'expense category']].drop_duplicates().set_index('expense')['expense category'].to_dict()

    # Organize expense heads under categories
    from collections import defaultdict
    category_heads = defaultdict(list)
    for head in expense_heads:
        cat = category_map.get(head, "Uncategorized")
        category_heads[cat].append(head)


    # ---------- Simulated Inflow ----------
    inflow_row = [
    "<strong>Total Inflow</strong>",
    f"{mtd_inflow['Target']:,.2f}", f"{mtd_inflow['Achieved']:,.2f}", format_delta(mtd_inflow['Delta']),
    f"{qtd_inflow['Target']:,.2f}", f"{qtd_inflow['Achieved']:,.2f}", format_delta(qtd_inflow['Delta']),
    f"{ytd_inflow['Target']:,.2f}", f"{ytd_inflow['Achieved']:,.2f}", format_delta(ytd_inflow['Delta'])
    ]


    # ---------- Expense Head Rows ----------
    expense_heads = sorted(mtd_exp.keys())
    expense_rows_html = ""
    totals = {"MTD": {"Target": 0, "Achieved": 0, "Delta": 0},
            "QTD": {"Target": 0, "Achieved": 0, "Delta": 0},
            "YTD": {"Target": 0, "Achieved": 0, "Delta": 0}}

    # Map each expense head to its category

    
    category_map = expense_df[['expense', 'expense category']].drop_duplicates().set_index('expense')['expense category'].to_dict()

    # Organize expense heads under categories
    category_rows_html = ""
    for category in sorted(category_heads.keys()):
        cat_mtd = {"Target": 0, "Achieved": 0, "Delta": 0}
        cat_qtd = {"Target": 0, "Achieved": 0, "Delta": 0}
        cat_ytd = {"Target": 0, "Achieved": 0, "Delta": 0}
        subrows = ""

        for head in category_heads[category]:
            row = [
                head,
                f"{mtd_exp[head]['Target']:,.2f}", f"{mtd_exp[head]['Achieved']:,.2f}", format_delta(mtd_exp[head]['Delta']),
                f"{qtd_exp[head]['Target']:,.2f}", f"{qtd_exp[head]['Achieved']:,.2f}", format_delta(qtd_exp[head]['Delta']),
                f"{ytd_exp[head]['Target']:,.2f}", f"{ytd_exp[head]['Achieved']:,.2f}", format_delta(ytd_exp[head]['Delta'])
            ]
            subrows += "<tr class='exp-detail-row'>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"

            for p, data in zip(["MTD", "QTD", "YTD"], [mtd_exp, qtd_exp, ytd_exp]):
                for k in ["Target", "Achieved", "Delta"]:
                    locals()[f"cat_{p.lower()}"][k] += data[head][k]
                    totals[p][k] += data[head][k]

        # Add subtotal row for this category
        subtotal_row = [
            f"<strong>{category} Subtotal</strong>",
            f"{cat_mtd['Target']:,.2f}", f"{cat_mtd['Achieved']:,.2f}", format_delta(cat_mtd['Delta']),
            f"{cat_qtd['Target']:,.2f}", f"{cat_qtd['Achieved']:,.2f}", format_delta(cat_qtd['Delta']),
            f"{cat_ytd['Target']:,.2f}", f"{cat_ytd['Achieved']:,.2f}", format_delta(cat_ytd['Delta'])
        ]
        category_rows_html += (
            "<tr style='font-weight:bold; background-color:#f0f0f0'>"
            + "".join(f"<td>{cell}</td>" for cell in subtotal_row)
            + "</tr>"
            + subrows
        )

    # ---------- Total Outflow Row (Collapsible Header) ----------
    outflow_row = [
        "<strong>Total Outflow</strong>",
        f"{totals['MTD']['Target']:,.2f}", f"{totals['MTD']['Achieved']:,.2f}", format_delta(totals['MTD']['Delta']),
        f"{totals['QTD']['Target']:,.2f}", f"{totals['QTD']['Achieved']:,.2f}", format_delta(totals['QTD']['Delta']),
        f"{totals['YTD']['Target']:,.2f}", f"{totals['YTD']['Achieved']:,.2f}", format_delta(totals['YTD']['Delta'])
    ]
    

    net_cash = {
    "MTD": {
        "Target": mtd_inflow['Target'] - totals["MTD"]["Target"],
        "Achieved": mtd_inflow['Achieved'] - totals["MTD"]["Achieved"]
    },
    "QTD": {
        "Target": qtd_inflow['Target'] - totals["QTD"]["Target"],
        "Achieved": qtd_inflow['Achieved'] - totals["QTD"]["Achieved"]
    },
    "YTD": {
        "Target": ytd_inflow['Target'] - totals["YTD"]["Target"],
        "Achieved": ytd_inflow['Achieved'] - totals["YTD"]["Achieved"]
    }
}

# Add Delta = Achieved - Target
    for period in ["MTD", "QTD", "YTD"]:
        net_cash[period]["Delta"] = net_cash[period]["Achieved"] - net_cash[period]["Target"]

    net_row = [
        "<strong>Net Cash Flow</strong>",
        f"{net_cash['MTD']['Target']:,.2f}", f"{net_cash['MTD']['Achieved']:,.2f}", format_delta(net_cash['MTD']['Delta']),
        f"{net_cash['QTD']['Target']:,.2f}", f"{net_cash['QTD']['Achieved']:,.2f}", format_delta(net_cash['QTD']['Delta']),
        f"{net_cash['YTD']['Target']:,.2f}", f"{net_cash['YTD']['Achieved']:,.2f}", format_delta(net_cash['YTD']['Delta'])
    ]


    # ---------- Final Table ----------
    # ---------- Inflow Row ----------
    # Final HTML Rows (only strings inside <tr>...</tr>)
    rows_html = ""

    # Inflow Row
    rows_html += f"""
    <tr style='font-weight:bold; background-color:#e8f5e9'>
        {"".join(f"<td>{cell}</td>" for cell in inflow_row)}
    </tr>
    """

    # Outflow Row
    rows_html += f"""
    <tr style='font-weight:bold; background-color:#f9f9f9'>
        {"".join(f"<td>{cell}</td>" for cell in outflow_row)}
    </tr>
    """

    # Add category breakdown if checkbox is selected
    if st.checkbox("▶ Show/Hide Detailed Expenses", value=False):
        rows_html += category_rows_html  # this must be a string of valid <tr>...</tr>

    # Net Cash Row
    rows_html += f"""
    <tr style='font-weight:bold; background-color:#fff8dc'>
        {"".join(f"<td>{cell}</td>" for cell in net_row)}
    </tr>
    """

    # Now wrap the full table
    table_html = f"""
    <style>
    .exp-table th, .exp-table td {{
        padding: 10px;
        border: 1px solid #ddd;
        text-align: center;
    }}
    .exp-table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 14px;
        margin-top: 10px;
    }}
    .exp-header {{
        background-color: #f2f2f2;
        font-weight: bold;
    }}
    </style>

    <table class='exp-table'>
        <tr class='exp-header'>
            <th rowspan='2'>Expenses</th>
            <th colspan='3'>MTD</th>
            <th colspan='3'>QTD</th>
            <th colspan='3'>YTD</th>
        </tr>
        <tr class='exp-header'>
            <th>Target</th><th>Achieved</th><th>Delta</th>
            <th>Target</th><th>Achieved</th><th>Delta</th>
            <th>Target</th><th>Achieved</th><th>Delta</th>
        </tr>
        {rows_html}
    </table>
    """

    # ✅ Render everything together here
    st.markdown(table_html, unsafe_allow_html=True)



    # ---------- SECTION 3: INFLOW / OUTFLOW / NET ----------
    # st.subheader("Net Cash Flow Summary")

    # inflow_mtd, exp_mtd, outflow_mtd, net_mtd = compute_metrics(df, start_mtd, end_mtd, "inflow", expense_cols)
    # inflow_qtd, exp_qtd, outflow_qtd, net_qtd = compute_metrics(df, start_qtd, end_qtd, "inflow", expense_cols)
    # inflow_ytd, exp_ytd, outflow_ytd, net_ytd = compute_metrics(df, start_ytd, end_ytd, "inflow", expense_cols)

    # net_table = pd.DataFrame({
    #     "Metric": ["Inflow", "Outflow", "Net Cash Flow"],
    #     "MTD": [inflow_mtd, outflow_mtd, net_mtd],
    #     "QTD": [inflow_qtd, outflow_qtd, net_qtd],
    #     "YTD": [inflow_ytd, outflow_ytd, net_ytd]
    # })

    # Format with deltas for net only
    # def style_net(val):
    #     if isinstance(val, str): return val
    #     return style_delta(val)

    # st.markdown("""
    # <style>
    #     .cash-table th, .cash-table td {
    #         padding: 10px;
    #         border: 1px solid #ccc;
    #         text-align: center;
    #     }
    #     .cash-table { border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 16px; }
    #     .cash-table th { background-color: #f0f0f0; }
    # </style>
    # """, unsafe_allow_html=True)

    # net_html = "<table class='cash-table'><tr><th>Metric</th><th>MTD</th><th>QTD</th><th>YTD</th></tr>"
    # for _, row in net_table.iterrows():
    #     net_html += "<tr>"
    #     net_html += f"<td>{row['Metric']}</td>"
    #     for val in [row["MTD"], row["QTD"], row["YTD"]]:
    #         if row["Metric"] == "Net Cash Flow":
    #             net_html += f"<td>{style_net(val)}</td>"
    #         else:
    #             net_html += f"<td>{val:,.0f}</td>"
    #     net_html += "</tr>"
    # net_html += "</table>"

    # st.markdown(net_html, unsafe_allow_html=True)

    st.caption("🧮 MTD = Last completed month | QTD = Current quarter till last completed month | YTD = Financial year till last completed month")