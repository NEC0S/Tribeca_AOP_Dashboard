import pandas as pd
import base64
import streamlit as st

def render_svg(svg_path):
    with open(svg_path, "r") as f:
        svg_data = f.read()
    b64 = base64.b64encode(svg_data.encode()).decode()
    html = f"""
    <div style="text-align:center; padding: 10px;">
        <img src='data:image/svg+xml;base64,{b64}' style='width:400px; height:auto;'>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def read_file(file):
    try:
        file_ext = file.name.split('.')[-1].lower()

        if file_ext == "csv":
            try:
                return pd.read_csv(file, encoding="utf-8")
            except UnicodeDecodeError:
                # Fallback encodings for legacy Excel-exported CSVs
                return pd.read_csv(file, encoding="latin1")
        
        elif file_ext in ["xls", "xlsx"]:
            return pd.read_excel(file, sheet_name=0)  # Reads first sheet by default
        
        else:
            raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")
    
    except Exception as e:
        raise RuntimeError(f"File reading failed: {e}")
