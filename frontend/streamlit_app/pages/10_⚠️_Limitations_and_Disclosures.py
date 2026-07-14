import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.layout import page_setup

page_setup("Limitations & Disclosures", icon="⚠️", wide=False)

DOCS = Path(__file__).resolve().parents[3] / "docs"
st.markdown((DOCS / "limitations.md").read_text(encoding="utf-8"))
