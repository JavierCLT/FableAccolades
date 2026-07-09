import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.layout import page_setup

page_setup("Methodology", icon="📖", wide=False)

DOCS = Path(__file__).resolve().parents[3] / "docs"

tab1, tab2, tab3 = st.tabs(["Methodology", "Scoring logic (full)", "Sources"])
with tab1:
    st.markdown((DOCS / "methodology.md").read_text(encoding="utf-8"))
with tab2:
    st.markdown((DOCS / "scoring_logic.md").read_text(encoding="utf-8"))
with tab3:
    st.markdown((DOCS / "sources.md").read_text(encoding="utf-8"))
