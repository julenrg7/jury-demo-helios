import streamlit as st

from noumenon_v2.ui.streamlit_app import render_app


st.session_state["v2_public_jury_mode"] = True
render_app()
