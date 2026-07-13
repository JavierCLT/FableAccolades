"""Plotly chart builders shared across pages."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

BROKER_COLORS = {
    "fidelity": "#00754a",
    "schwab": "#00a0df",
    "vanguard": "#96151d",
    "robinhood": "#00c805",
    "ibkr": "#d81222",
    "etrade": "#6633cc",
}


def radar_chart(ds: pd.DataFrame, broker_slugs: list[str]) -> go.Figure:
    """ds: dimension_scores frame from components.data.dimension_scores()."""
    fig = go.Figure()
    dims = ds.sort_values("sort_order")["dim_name"].unique().tolist()
    for slug in broker_slugs:
        sub = ds[ds["broker_slug"] == slug].set_index("dim_name").reindex(dims)
        fig.add_trace(
            go.Scatterpolar(
                r=sub["score"].tolist() + [sub["score"].iloc[0]],
                theta=dims + [dims[0]],
                name=sub["broker_name"].dropna().iloc[0] if not sub["broker_name"].dropna().empty else slug,
                line={"color": BROKER_COLORS.get(slug)},
                fill="toself",
                opacity=0.75,
            )
        )
    fig.update_layout(
        polar={"radialaxis": {"range": [0, 100], "showticklabels": True}},
        height=560,
        legend={"orientation": "h", "y": -0.1},
        margin={"t": 30, "b": 30},
    )
    return fig


def score_bar(df: pd.DataFrame, x: str, y: str, color_slug_col: str | None = None,
              title: str | None = None) -> go.Figure:
    colors = (
        [BROKER_COLORS.get(s, "#888") for s in df[color_slug_col]]
        if color_slug_col
        else "#4c78a8"
    )
    fig = go.Figure(go.Bar(x=df[x], y=df[y], marker_color=colors,
                           text=[f"{v:.1f}" for v in df[y]], textposition="outside"))
    fig.update_layout(title=title, yaxis_range=[0, 105], height=380, margin={"t": 40, "b": 10})
    return fig


def contradiction_heatmap(matrix: pd.DataFrame) -> go.Figure:
    """matrix: index=broker names, columns=dimension names, values=max gap (NaN = agreement)."""
    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=matrix.columns.tolist(),
            y=matrix.index.tolist(),
            colorscale=[[0.0, "#f0f0f0"], [0.35, "#ffe08a"], [0.65, "#ff9d5c"], [1.0, "#d7191c"]],
            zmin=0,
            zmax=50,
            colorbar={"title": "Max gap<br>(0-100 pts)"},
            hovertemplate="%{y} · %{x}<br>Max expert gap: %{z:.0f} pts<extra></extra>",
        )
    )
    fig.update_layout(height=420, margin={"t": 20, "b": 10}, xaxis={"tickangle": -35})
    return fig
