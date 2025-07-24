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
    