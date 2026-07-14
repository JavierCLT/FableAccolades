"""Shared application shell, navigation, and visual design system."""

from __future__ import annotations

import streamlit as st

from components import data

DISCLAIMER = (
    "Independent research from public data. Scores are estimates, not financial advice. "
    "Verify current terms with the broker before moving money."
)

GLOBAL_CSS = """
<style>
:root {
  --bbi-ink: #18211e;
  --bbi-muted: #5f6d67;
  --bbi-line: #d8e1dc;
  --bbi-canvas: #f4f7f5;
  --bbi-surface: #ffffff;
  --bbi-green: #08785e;
  --bbi-green-dark: #075744;
  --bbi-blue: #1556a0;
  --bbi-amber: #a96508;
  --bbi-red: #ad2e3e;
}

html, body, .stApp {
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  letter-spacing: 0;
}

.stApp,
[data-testid="stAppViewContainer"] {
  background: var(--bbi-canvas);
  color: var(--bbi-ink);
}

header[data-testid="stHeader"] {
  background: transparent;
}

.main .block-container {
  max-width: 1280px;
  padding-top: 2rem;
  padding-bottom: 5rem;
}

h1, h2, h3, h4, p, span, label {
  letter-spacing: 0 !important;
}

[data-testid="stExpander"] [data-testid="stIconMaterial"] {
  font-size: 0 !important;
  width: 1rem;
}

[data-testid="stExpander"] [data-testid="stIconMaterial"]::after {
  content: ">";
  font-family: Inter, ui-sans-serif, sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1;
}

h1, h2, h3, h4 {
  color: var(--bbi-ink);
}

h2 {
  font-size: 1.45rem !important;
  margin-top: 2rem !important;
}

h3 {
  font-size: 1.05rem !important;
}

a {
  color: var(--bbi-blue);
}

[data-testid="stSidebar"] {
  background: #12201b;
  border-right: 1px solid #24362f;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding-top: 1.2rem;
}

[data-testid="stSidebar"] a,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
  color: #e9f2ee !important;
}

[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  border-radius: 6px;
  min-height: 2.55rem;
  padding: 0.45rem 0.65rem;
}

[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
  background: #21372f;
}

.bbi-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.35rem 0.2rem 1.15rem;
  border-bottom: 1px solid #2a4037;
  margin-bottom: 0.9rem;
}

.bbi-brand-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  background: #e8b84a;
  color: #12201b !important;
  font-size: 0.78rem;
  font-weight: 800;
  border-radius: 6px;
}

.bbi-brand-name {
  color: #ffffff !important;
  font-size: 0.95rem;
  font-weight: 750;
  line-height: 1.15;
}

.bbi-brand-sub {
  color: #9db1a9 !important;
  font-size: 0.72rem;
  margin-top: 0.18rem;
}

.bbi-nav-label {
  color: #8fa69d !important;
  font-size: 0.68rem;
  font-weight: 750;
  margin: 1.1rem 0 0.35rem 0.45rem;
  text-transform: uppercase;
}

.bbi-sidebar-foot {
  color: #8fa69d !important;
  font-size: 0.72rem;
  line-height: 1.45;
  border-top: 1px solid #2a4037;
  margin-top: 1.2rem;
  padding: 1rem 0.35rem 0;
}

.bbi-page-header {
  margin: 0 0 1.35rem;
  max-width: 850px;
}

.bbi-kicker {
  color: var(--bbi-green);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  margin-bottom: 0.45rem;
}

.bbi-page-header h1,
.bbi-hero h1 {
  color: var(--bbi-ink);
  font-size: 2.35rem;
  line-height: 1.08;
  margin: 0;
  max-width: 850px;
}

.bbi-page-header p,
.bbi-hero p {
  color: var(--bbi-muted);
  font-size: 1rem;
  line-height: 1.55;
  margin: 0.6rem 0 0;
  max-width: 780px;
}

.bbi-hero {
  margin: 0 0 1.1rem;
}

.bbi-trustline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 1.15rem;
  align-items: center;
  padding: 0.72rem 0;
  border-top: 1px solid var(--bbi-line);
  border-bottom: 1px solid var(--bbi-line);
  color: var(--bbi-muted);
  font-size: 0.82rem;
  margin-bottom: 1.25rem;
}

.bbi-trustline strong {
  color: var(--bbi-ink);
}

.bbi-trust-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--bbi-green);
  display: inline-block;
  margin-right: 0.35rem;
}

.bbi-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin: 2.2rem 0 0.8rem;
}

.bbi-section-head h2 {
  margin: 0 !important;
}

.bbi-section-head p {
  color: var(--bbi-muted);
  margin: 0.25rem 0 0;
  font-size: 0.88rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bbi-surface);
  border-color: var(--bbi-line) !important;
  border-radius: 8px !important;
}

div[data-testid="stMetric"] {
  background: var(--bbi-surface);
  border: 1px solid var(--bbi-line);
  border-radius: 8px;
  padding: 0.85rem 1rem;
}

div[data-testid="stMetricValue"] {
  color: var(--bbi-ink);
  font-weight: 750;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
  border-radius: 6px !important;
  min-height: 2.55rem;
  font-weight: 700;
}

[data-baseweb="select"] > div,
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"] {
  border-radius: 6px !important;
}

[data-testid="stDataFrame"],
.stPlotlyChart {
  border: 1px solid var(--bbi-line);
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.bbi-results-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 0.8rem;
  align-items: stretch;
}

.bbi-match-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 340px;
  background: var(--bbi-surface);
  border: 1px solid var(--bbi-line);
  border-top: 4px solid #789087;
  border-radius: 8px;
  padding: 1.15rem;
}

.bbi-match-card.featured {
  border-top-color: var(--bbi-green);
  box-shadow: 0 8px 24px rgba(18, 32, 27, 0.08);
}

.bbi-rank-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
}

.bbi-rank-label {
  color: var(--bbi-green);
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
}

.bbi-confidence {
  color: var(--bbi-muted);
  font-size: 0.75rem;
}

.bbi-match-card h3 {
  color: var(--bbi-ink);
  font-size: 1.35rem !important;
  margin: 0.75rem 0 0.25rem;
}

.bbi-score-row {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  margin-bottom: 0.6rem;
}

.bbi-score {
  color: var(--bbi-ink);
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
}

.bbi-score-denom {
  color: var(--bbi-muted);
  font-size: 0.8rem;
}

.bbi-score-track {
  height: 6px;
  background: #e8eeeb;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.9rem;
}

.bbi-score-fill {
  height: 100%;
  background: var(--bbi-green);
}

.bbi-edge-label {
  color: var(--bbi-muted);
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
  margin-top: 0.55rem;
}

.bbi-edge-text {
  color: var(--bbi-ink);
  font-size: 0.85rem;
  line-height: 1.45;
  margin-top: 0.22rem;
}

.bbi-risk-text {
  color: #7c3e18;
}

.bbi-fact-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.8rem 0;
}

.bbi-fact-chip {
  background: #eef3f0;
  color: #33423c;
  border-radius: 4px;
  padding: 0.28rem 0.42rem;
  font-size: 0.72rem;
}

.bbi-card-foot {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  border-top: 1px solid #e6ece8;
  margin-top: auto;
  padding-top: 0.8rem;
  font-size: 0.77rem;
}

.bbi-card-foot a {
  font-weight: 750;
  text-decoration: none;
}

.bbi-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--bbi-line);
  border-radius: 8px;
  background: var(--bbi-surface);
}

.bbi-decision-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
}

.bbi-decision-table th,
.bbi-decision-table td {
  padding: 0.78rem 0.9rem;
  border-bottom: 1px solid #e6ece8;
  text-align: left;
  vertical-align: middle;
  font-size: 0.82rem;
}

.bbi-decision-table th {
  color: var(--bbi-muted);
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
  background: #f8faf9;
}

.bbi-decision-table th:first-child,
.bbi-decision-table td:first-child {
  position: sticky;
  left: 0;
  background: #f8faf9;
  z-index: 2;
  color: var(--bbi-ink);
  font-weight: 700;
  min-width: 180px;
}

.bbi-cell-best {
  color: var(--bbi-green-dark);
  font-weight: 800;
}

.bbi-mini-bar {
  width: 100%;
  max-width: 115px;
  height: 4px;
  background: #e8eeeb;
  margin-top: 0.28rem;
}

.bbi-mini-bar > span {
  display: block;
  height: 100%;
  background: var(--bbi-blue);
}

.bbi-signal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
}

.bbi-signal {
  background: var(--bbi-surface);
  border: 1px solid var(--bbi-line);
  border-radius: 8px;
  padding: 0.9rem;
}

.bbi-signal-value {
  color: var(--bbi-ink);
  font-size: 1.4rem;
  font-weight: 800;
}

.bbi-signal-label {
  color: var(--bbi-muted);
  font-size: 0.75rem;
  line-height: 1.35;
}

.bbi-action-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
}

.bbi-action {
  display: block;
  color: var(--bbi-ink) !important;
  background: var(--bbi-surface);
  border: 1px solid var(--bbi-line);
  border-radius: 8px;
  padding: 1rem;
  min-height: 112px;
  text-decoration: none !important;
}

.bbi-action:hover {
  border-color: #9bb5aa;
  box-shadow: 0 4px 14px rgba(18, 32, 27, 0.07);
}

.bbi-action strong {
  display: block;
  color: var(--bbi-ink);
  margin-bottom: 0.3rem;
}

.bbi-action span {
  color: var(--bbi-muted);
  font-size: 0.8rem;
  line-height: 1.4;
}

.bbi-disclaimer {
  color: var(--bbi-muted);
  font-size: 0.75rem;
  border-top: 1px solid var(--bbi-line);
  margin-top: 2.5rem;
  padding-top: 1rem;
}

.bbi-dashboard-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--bbi-line);
}

.bbi-dashboard-head h1 {
  color: var(--bbi-ink);
  font-size: 1.9rem;
  line-height: 1.1;
  margin: 0;
}

.bbi-dashboard-status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.45rem;
}

.bbi-dashboard-status span {
  color: var(--bbi-muted);
  background: #eef3f0;
  border: 1px solid var(--bbi-line);
  border-radius: 4px;
  padding: 0.35rem 0.55rem;
  font-size: 0.72rem;
}

.bbi-dashboard-status b {
  color: var(--bbi-ink);
}

.bbi-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
}

.bbi-kpi {
  min-height: 94px;
  padding: 0.8rem 0.9rem;
  background: #ffffff;
  border: 1px solid var(--bbi-line);
  border-left: 4px solid #768982;
  border-radius: 6px;
}

.bbi-kpi.primary { border-left-color: var(--bbi-green); }
.bbi-kpi.good { border-left-color: #167a5d; }
.bbi-kpi.warning { border-left-color: #c48b22; }

.bbi-kpi span,
.bbi-insight-grid span,
.bbi-panel-heading span {
  display: block;
  color: var(--bbi-muted);
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
}

.bbi-kpi strong {
  display: block;
  color: var(--bbi-ink);
  font-size: 1.25rem;
  line-height: 1.2;
  margin-top: 0.2rem;
}

.bbi-kpi small,
.bbi-insight-grid small,
.bbi-dashboard-table small {
  display: block;
  color: var(--bbi-muted);
  font-size: 0.68rem;
  margin-top: 0.18rem;
}

.bbi-panel-heading {
  min-height: 50px;
  padding: 0 0.15rem 0.5rem;
  border-bottom: 2px solid #dfe7e3;
}

.bbi-panel-heading strong {
  display: block;
  color: var(--bbi-ink);
  font-size: 0.9rem;
  margin-top: 0.18rem;
}

.bbi-insight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  min-height: 76px;
  background: #ffffff;
  border: 1px solid var(--bbi-line);
  border-radius: 6px;
}

.bbi-insight-grid > div {
  min-width: 0;
  padding: 0.75rem 0.9rem;
  border-right: 1px solid var(--bbi-line);
}

.bbi-insight-grid > div:last-child { border-right: 0; }

.bbi-insight-grid strong,
.bbi-insight-value > b {
  display: block;
  color: var(--bbi-ink);
  font-size: 0.9rem;
  line-height: 1.25;
  margin-top: 0.2rem;
}

.bbi-dashboard-table {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
}

.bbi-dashboard-table th,
.bbi-dashboard-table td {
  padding: 0.68rem 0.72rem;
  border-bottom: 1px solid #e6ece8;
  text-align: left;
  vertical-align: top;
  font-size: 0.76rem;
}

.bbi-dashboard-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  color: #4d5d56;
  background: #eef3f0;
  font-size: 0.68rem;
  text-transform: uppercase;
}

.bbi-dashboard-table td:first-child {
  color: var(--bbi-ink);
  font-weight: 700;
  background: #f8faf9;
}

.bbi-withheld {
  display: inline-block;
  color: #8a4c3d;
  background: #f9ece8;
  border-radius: 3px;
  padding: 0.15rem 0.35rem;
  font-weight: 750;
}

@media (max-width: 900px) {
  .bbi-results-grid {
    grid-template-columns: 1fr 1fr;
  }

  .bbi-match-card.featured {
    grid-column: 1 / -1;
  }

  .bbi-signal-grid,
  .bbi-action-grid {
    grid-template-columns: 1fr 1fr;
  }

  .bbi-kpi-grid,
  .bbi-insight-grid {
    grid-template-columns: 1fr 1fr;
  }

  .bbi-insight-grid > div:nth-child(2) { border-right: 0; }

  .bbi-insight-grid > div:nth-child(-n+2) {
    border-bottom: 1px solid var(--bbi-line);
  }
}

@media (max-width: 760px) {
  .main .block-container {
    padding: 0.35rem 1rem 4rem;
  }

  .main [data-testid="stVerticalBlock"] {
    gap: 0.65rem;
  }

  .bbi-page-header h1,
  .bbi-hero h1 {
    font-size: 1.78rem;
  }

  .bbi-dashboard-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .bbi-dashboard-head h1 {
    font-size: 1.55rem;
  }

  .bbi-dashboard-status {
    justify-content: flex-start;
  }

  .bbi-page-header p,
  .bbi-hero p {
    font-size: 0.86rem;
    line-height: 1.45;
  }

  .bbi-hero {
    margin-bottom: 0.55rem;
  }

  .bbi-trustline {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.3rem 0.75rem;
    padding: 0.55rem 0;
    font-size: 0.72rem;
  }

  .bbi-trustline > span:nth-child(3) {
    grid-column: 1 / -1;
  }

  .bbi-trustline > span:nth-child(4) {
    display: none;
  }

  .bbi-results-grid,
  .bbi-signal-grid,
  .bbi-action-grid {
    grid-template-columns: 1fr;
  }

  .bbi-match-card.featured {
    grid-column: auto;
  }

  .bbi-match-card {
    min-height: 0;
  }

  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.35rem !important;
  }

  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 0 !important;
  }

  div.st-key-bbi_top_nav div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
  }

  div.st-key-bbi_top_nav div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    flex: 1 1 0 !important;
    width: auto !important;
  }
}

section[data-testid="stSidebar"],
button[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}

div.st-key-bbi_top_nav {
  background: #ffffff;
  border: 1px solid #c9d5cf;
  border-left: 4px solid var(--bbi-blue);
  border-radius: 7px;
  margin: -0.55rem 0 0.75rem;
  padding: 0.4rem 0.55rem;
  box-shadow: 0 3px 12px rgba(24, 33, 30, 0.06);
}

div.st-key-bbi_top_nav div[data-testid="stPageLink"] a {
  justify-content: center;
  min-height: 42px;
  border: 1px solid #a8bad0;
  border-radius: 6px;
  background: #f3f7fc;
  color: #17497e;
  font-weight: 800;
  font-size: 0.9rem;
}

div.st-key-bbi_top_nav div[data-testid="stPageLink"] a:hover {
  border-color: var(--bbi-blue);
  background: #e5eef9;
}

div.st-key-bbi_nav_dashboard_active div[data-testid="stPageLink"] a,
div.st-key-bbi_nav_fees_active div[data-testid="stPageLink"] a,
div.st-key-bbi_nav_compare_active div[data-testid="stPageLink"] a {
  border-color: var(--bbi-blue);
  background: var(--bbi-blue);
  color: #ffffff !important;
  box-shadow: 0 2px 7px rgba(21, 86, 160, 0.22);
}

div.st-key-bbi_nav_dashboard_active div[data-testid="stPageLink"] a *,
div.st-key-bbi_nav_fees_active div[data-testid="stPageLink"] a *,
div.st-key-bbi_nav_compare_active div[data-testid="stPageLink"] a * {
  color: #ffffff !important;
}

.bbi-top-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 38px;
  font-weight: 800;
  color: var(--bbi-ink);
}

.bbi-top-brand b {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  background: var(--bbi-green);
  color: #fff;
  border-radius: 4px;
  font-size: 0.72rem;
}

div.st-key-audience_mode {
  background: #e8f0fa;
  border: 1px solid #9fb7d1;
  border-radius: 7px;
  padding: 0.25rem;
}

div.st-key-audience_mode div[data-testid="stButtonGroup"] {
  width: 100%;
}

div.st-key-audience_mode button[data-variant="segmented_control"] {
  min-height: 42px;
  background: #ffffff;
  border-color: #9fb7d1;
  color: #17497e;
  font-weight: 800;
}

div.st-key-audience_mode button[data-variant="segmented_control"][data-selected] {
  background: var(--bbi-blue) !important;
  border-color: var(--bbi-blue) !important;
  color: #ffffff !important;
  box-shadow: 0 2px 7px rgba(21, 86, 160, 0.22);
}

div.st-key-audience_mode button[data-variant="segmented_control"] p {
  color: inherit !important;
  font-weight: inherit !important;
}

.bbi-winner-band {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(180px, 0.55fr);
  gap: 1.25rem;
  align-items: center;
  margin: 0.35rem 0 0.85rem;
  padding: 1rem 1.15rem;
  border-top: 3px solid var(--bbi-green);
  border-bottom: 1px solid var(--bbi-line);
  background: #fff;
}

.bbi-winner-band .label,
.bbi-benchmark-band .label {
  color: var(--bbi-muted);
  font-size: 0.72rem;
  font-weight: 750;
  text-transform: uppercase;
}

.bbi-winner-band h1,
.bbi-benchmark-band h1 {
  margin: 0.1rem 0 0.25rem;
  font-size: 1.75rem;
  line-height: 1.12;
  letter-spacing: 0;
}

.bbi-winner-band p,
.bbi-benchmark-band p {
  margin: 0;
  color: var(--bbi-muted);
  font-size: 0.92rem;
}

.bbi-winner-score {
  text-align: right;
}

.bbi-winner-score strong {
  display: block;
  color: var(--bbi-green);
  font-size: 2rem;
  line-height: 1;
}

.bbi-winner-score small {
  color: var(--bbi-muted);
  font-size: 0.74rem;
}

.bbi-verdict-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  border: 1px solid var(--bbi-line);
  border-radius: 5px;
  background: #fff;
}

.bbi-verdict-grid > div {
  padding: 0.72rem 0.85rem;
  border-right: 1px solid var(--bbi-line);
}

.bbi-verdict-grid > div:last-child { border-right: 0; }
.bbi-verdict-grid span { display: block; color: var(--bbi-muted); font-size: 0.68rem; font-weight: 750; text-transform: uppercase; }
.bbi-verdict-grid strong { display: block; margin-top: 0.15rem; font-size: 0.9rem; }
.bbi-verdict-grid .risk strong { color: #9a4939; }

.bbi-mini-board {
  border-top: 2px solid var(--bbi-ink);
  background: #fff;
  padding: 0.55rem 0.7rem 0.1rem;
}

.bbi-mini-board span { display: block; color: var(--bbi-muted); font-size: 0.68rem; font-weight: 750; text-transform: uppercase; }
.bbi-mini-board strong { display: block; margin-top: 0.12rem; font-size: 0.88rem; }

.bbi-benchmark-band {
  margin: 0.35rem 0 0.85rem;
  padding: 1rem 1.15rem;
  border-top: 3px solid #1556a0;
  border-bottom: 1px solid var(--bbi-line);
  background: #fff;
}

.bbi-research-note {
  color: var(--bbi-muted);
  font-size: 0.78rem;
  line-height: 1.5;
}

@media (max-width: 700px) {
  .bbi-top-brand span { display: none; }
  div.st-key-bbi_top_nav div[data-testid="stHorizontalBlock"]:has(.bbi-top-brand) > div[data-testid="stColumn"]:has(.bbi-top-brand) {
    display: none !important;
  }
  div.st-key-bbi_top_nav div[data-testid="stHorizontalBlock"]:has(.bbi-top-brand) > div[data-testid="stColumn"]:not(:has(.bbi-top-brand)) {
    flex: 1 1 100% !important;
    width: 100% !important;
  }
  div.st-key-bbi_top_nav div[data-testid="stPageLink"] a {
    min-height: 38px;
    padding-left: 0.3rem;
    padding-right: 0.3rem;
    font-size: 0.76rem;
  }
  .bbi-winner-band { grid-template-columns: 1fr; }
  .bbi-winner-score { text-align: left; }
  .bbi-verdict-grid { grid-template-columns: 1fr; }
  .bbi-verdict-grid > div { border-right: 0; border-bottom: 1px solid var(--bbi-line); }
  .bbi-verdict-grid > div:last-child { border-bottom: 0; }
}
</style>
"""


def _primary_navigation(current_title: str) -> None:
    active_page = {
        "Broker Dashboard": "dashboard",
        "Fees & Products": "fees",
        "Compare Brokers": "compare",
    }.get(current_title)

    def nav_link(page: str, label: str, slug: str) -> None:
        suffix = "_active" if active_page == slug else ""
        with st.container(key=f"bbi_nav_{slug}{suffix}"):
            st.page_link(page, label=label)

    with st.container(key="bbi_top_nav"):
        brand, navigation = st.columns([2.4, 1])
        with brand:
            st.markdown(
                '<div class="bbi-top-brand"><b>BBI</b><span>Best Broker Index</span></div>',
                unsafe_allow_html=True,
            )
        with navigation:
            dashboard, fees, compare = st.columns([1, 1.25, 0.9], gap="small")
            with dashboard:
                nav_link("app.py", "Dashboard", "dashboard")
            with fees:
                nav_link("pages/3_📋_Product_Facts.py", "Fees & Products", "fees")
            with compare:
                nav_link("pages/6_📈_Compare_Brokers.py", "Compare", "compare")


def page_setup(
    title: str,
    icon: str = "📊",
    wide: bool = True,
    *,
    subtitle: str | None = None,
    eyebrow: str = "Best Broker Index",
    show_title: bool = True,
) -> None:
    st.set_page_config(
        page_title=f"{title} | Best Broker Index",
        page_icon=icon,
        layout="wide" if wide else "centered",
        initial_sidebar_state="collapsed",
    )
    if data.db_missing():
        st.error(
            "Database not found. Build it first:\n\n"
            "```\npython -m backend.pipeline            # with live collectors\n"
            "python -m backend.pipeline --no-collect  # offline (seed data only)\n```"
        )
        st.stop()

    from components.hovercard import CSS, enable_flip

    st.markdown(GLOBAL_CSS + CSS, unsafe_allow_html=True)
    enable_flip()
    _primary_navigation(title)

    if show_title:
        description = f"<p>{subtitle}</p>" if subtitle else ""
        st.markdown(
            f"""
            <div class="bbi-page-header">
              <div class="bbi-kicker">{eyebrow}</div>
              <h1>{title}</h1>
              {description}
            </div>
            """,
            unsafe_allow_html=True,
        )


def section_header(title: str, description: str | None = None) -> None:
    detail = f"<p>{description}</p>" if description else ""
    st.markdown(
        f'<div class="bbi-section-head"><div><h2>{title}</h2>{detail}</div></div>',
        unsafe_allow_html=True,
    )


def compact_disclaimer() -> None:
    st.markdown(f'<div class="bbi-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
    with st.expander("Sources, methodology and disclosures"):
        st.markdown(
            '<div class="bbi-research-note">Full evidence remains available without occupying the primary decision workflow.</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(4)
        with columns[0]:
            st.page_link("pages/8_🔍_Evidence_Viewer.py", label="Evidence ledger")
        with columns[1]:
            st.page_link("pages/9_📖_Methodology.py", label="Methodology")
        with columns[2]:
            st.page_link("pages/11_🕳️_Withdrawn_Reviews.py", label="Withdrawn reviews")
        with columns[3]:
            st.page_link("pages/10_⚠️_Limitations_and_Disclosures.py", label="Limitations")


def confidence_badge(value: float) -> str:
    if value >= 70:
        return f"High · {value:.0f}"
    if value >= 45:
        return f"Moderate · {value:.0f}"
    return f"Low · {value:.0f}"


def severity_badge(severity: str) -> str:
    return {"moderate": "Moderate", "significant": "Significant", "severe": "Severe"}.get(
        severity, severity
    )


def method_label(method: str) -> str:
    return {
        "api": "official API",
        "scrape": "verified live",
        "bulk_download": "bulk download",
        "manual_curation": "curated from public page",
    }.get(method, method)
