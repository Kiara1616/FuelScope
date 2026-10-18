"""Punto de entrada de FuelScope."""

import streamlit as st

from fuelscope.dashboard import render

st.set_page_config(page_title="FuelScope", page_icon="⛽", layout="wide")
render()
