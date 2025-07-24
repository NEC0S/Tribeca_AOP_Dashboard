import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from components.exp_dashboard import render_exp_dashboard
from components.target_dashboard import render_target_dashboard
from utils.load_data import render_svg,read_file

#This is for logo --------------------------------------------------------------------------------------------
st.set_page_config(page_title="Tribeca AaOP Dashboard", layout="wide", page_icon='assets/logo.webp')

def get_base_path():    
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

logo_path = get_base_path() / "assets" / "TribecaLogo.svg"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
render_svg(str(logo_path))
#--------------------------------------------------------------------------------------------------------------


st.title("AOP Dashboard")


# --- Sidebar File Uploads ------------------------------------------------------------------------------------
st.sidebar.header("📁 Upload Your Data")
target_file = st.sidebar.file_uploader("Upload Target File (CSV or Excel)", type=["csv", "xlsx", "xls"])
expense_file = st.sidebar.file_uploader("Upload Expense File (CSV or Excel)", type=["csv", "xlsx", "xls"])
today = pd.to_datetime(st.sidebar.date_input("📅 Select Today's Date", value=pd.to_datetime("today")))
#--------------------------------------------------------------------------------------------------------------


# --- Tabs ----------------------------------------------------------------------------------------------------
# --- Tabs ----------------------------------------------------------------------------------------------------
if target_file and expense_file:
    try:
        target_df = read_file(target_file)
        expense_df = read_file(expense_file)
    except Exception as e:
        st.error(f"Error reading uploaded files: {e}")
        st.stop()

    # --- Tabs for views ---
    tab1, tab2 = st.tabs(["Target Dashboard", "Expense Dashboard"])

    with tab1:
        render_target_dashboard(target_df, expense_df, today)

    with tab2:
        render_exp_dashboard(expense_df, target_df, today)

else:
    st.warning("Please upload both Target and Expense files.")
