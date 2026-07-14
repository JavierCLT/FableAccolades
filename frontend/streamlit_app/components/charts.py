"""Plotly chart builders shared across pages."""

from __future__ import annotations

import textwrap

import pandas as pd
import plotly.graph_objects as go

BROKER_COLORS = {
    "fidelity": "#16825D",
    "schwab": "#2563EB",
    "vanguard": "#C83E4D",
    "robinhood": "#C28A00",
    "ibkr": "#F26B38",
    "etrade": "#7A4CC2",
    "merrill": "#008C95",
    "sofi": "#3949AB",
    "webull": "#D64F8C",
    "public": "#364152",
    "jpmorgan": "#9A6A2F",
    "ally": "#8B7286",
}

BROKER_MARKERS = {
    "fidelity": "circle",
    "schwab": "square",
    "vanguard": "diamond",
    "robinhood": "triangle-up",
    "ibkr": "x",
    "etrade": "pentagon",
    "merrill": "hexagon",
    "sofi": "star",
    "webull": "triangle-down",
    "public": "cross",
    "jpmorgan": "hourglass",
}


DIMENSION_SCORING_BASIS = {
    "costs_fees": (
        "Current stock/ETF commissions, options contract fees, margin rates, and account fees; "
        "then available customer and expert evidence."
    ),
    "cash_yield": (
        "Current automatic sweep APY carries 65% of the objective cash score and the best "
        "available APY carries 35%; customer and expert evidence are added when available."
    ),
    "ease_of_use": (
        "Customer reports and expert assessments of onboarding, navigation, and web/desktop "
        "friction. There is no invented objective proxy for usability."
    ),
    "mobile_app": (
        "Review-count-weighted Apple and Google app-store ratings, customer app themes, and "
        "expert mobile-app assessments."
    ),
    "research_education": (
        "Customer reports and expert assessments of screeners, research, market data, and "
        "education. There is no objective product-fact component."
    ),
    "retirement_rollover": (
        "Current IRA-match terms where offered, plus customer and expert evidence about IRA "
        "accounts, rollovers, and retirement planning."
    ),
    "trading_tools": (
        "Customer reports and expert assessments of platforms, order types, and advanced "
        "trading capability. There is no objective product-fact component."
    ),
    "product_breadth": (
        "Verified access to crypto, futures, international markets, and bonds/CDs, plus "
        "available customer and expert evidence."
    ),
    "customer_support": (
        "Verified 24/7 support and branch access, service-related customer themes, attributable "
        "CFPB complaint friction, and expert support assessments."
    ),
    "transfer_acat": (
        "Current outgoing ACAT fee, transfer-related customer complaints or praise, and "
        "available expert assessments."
    ),
    "banking_integration": (
        "Verified checking, debit, ATM, bill-pay, and cash-movement capabilities, plus available "
        "customer and expert evidence."
    ),
    "advisory_options": (
        "Current robo-advisor availability and fee, verified human-advisor access, and available "
        "customer and expert evidence."
    ),
    "reliability": (
        "Customer outage and stability reports plus expert reliability assessments. There is no "
        "invented objective outage metric."
    ),
    "security": (
        "Verified authentication and account-protection features, security-related customer "
        "friction, and available expert assessments."
    ),
    "tax_reporting": (
        "Verified tax-lot selection and cost-basis controls, tax-form customer experience, and "
        "available expert assessments."
    ),
    "fractional_shares": (
        "Current purchase scope: 0 = unavailable, 0.5 = broker ETFs only, 1 = limited stock "
        "universe, 2 = broad stocks and ETFs; then available customer and expert evidence."
    ),
}


def _hover_wrap(value: object, width: int = 58) -> str:
    return "<br>".join(textwrap.wrap(str(value or ""), width=width))


def _with_alpha(color: str, alpha: float) -> str:
    value = color.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _dimension_help(frame: pd.DataFrame) -> list[list[object]]:
    return [
        [
            _hover_wrap(row.get("dim_description", "")),
            _hover_wrap(DIMENSION_SCORING_BASIS.get(row["dim_slug"], "See the published methodology.")),
            float(row.get("confidence", 0.0) or 0.0),
            int(row.get("evidence_count", 0) or 0),
        ]
        for _, row in frame.iterrows()
    ]


def _category_help(frame: pd.DataFrame) -> list[list[str]]:
    return [
        [
            _hover_wrap(row.get("dim_description", "")),
            _hover_wrap(DIMENSION_SCORING_BASIS.get(row["dim_slug"], "See the published methodology.")),
        ]
        for _, row in frame.iterrows()
    ]


def radar_chart(
    ds: pd.DataFrame,
    broker_slugs: list[str],
    dimension_slugs: list[str] | None = None,
    *,
    height: int = 430,
) -> go.Figure:
    """ds: dimension_scores frame from components.data.dimension_scores()."""
    fig = go.Figure()
    filtered = ds[ds["dim_slug"].isin(dimension_slugs)] if dimension_slugs else ds
    dims = filtered.sort_values("sort_order")["dim_name"].unique().tolist()
    for slug in broker_slugs:
        sub = filtered[filtered["broker_slug"] == slug].set_index("dim_name").reindex(dims)
        if sub.empty or sub["score"].dropna().empty:
            continue
        hover_data = _dimension_help(sub)
        color = BROKER_COLORS.get(slug, "#687972")
        fig.add_trace(
            go.Scatterpolar(
                r=sub["score"].tolist() + [sub["score"].iloc[0]],
                theta=dims + [dims[0]],
                customdata=hover_data + [hover_data[0]],
                name=sub["broker_name"].dropna().iloc[0] if not sub["broker_name"].dropna().empty else slug,
                line={"color": color, "width": 2.6},
                marker={
                    "color": color,
                    "size": 7,
                    "symbol": BROKER_MARKERS.get(slug, "circle"),
                    "line": {"color": "#ffffff", "width": 1},
                },
                fill="toself",
                fillcolor=_with_alpha(color, 0.14),
                hovertemplate=(
                    "<b>%{theta}</b><br>%{customdata[0]}"
                    "<br><br><b>How it is measured</b><br>%{customdata[1]}"
                    "<br><br><b>Score</b> %{r:.0f}/100"
                    "<br>Confidence %{customdata[2]:.0f}/100 · %{customdata[3]} evidence items"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
    if dims:
        dimension_meta = (
            filtered.sort_values("sort_order")
            .drop_duplicates("dim_name")
            .set_index("dim_name")
            .reindex(dims)
        )
        fig.add_trace(
            go.Scatterpolar(
                r=[124] * len(dims),
                theta=dims,
                mode="text+markers",
                text=dims,
                textposition="middle center",
                textfont={"size": 10, "color": "#34433d"},
                marker={
                    "size": [min(180, max(100, len(name) * 6)) for name in dims],
                    "color": "rgba(255, 255, 255, 0.01)",
                    "line": {"width": 0},
                },
                customdata=_category_help(dimension_meta),
                hovertemplate=(
                    "<b>%{text}</b><br>%{customdata[0]}"
                    "<br><br><b>How it is measured</b><br>%{customdata[1]}"
                    "<extra></extra>"
                ),
                showlegend=False,
                name="Category definitions",
            )
        )
    fig.update_layout(
        polar={
            "radialaxis": {
                "range": [0, 136],
                "tickvals": [25, 50, 75, 100],
                "tickfont": {"size": 9, "color": "#74827c"},
                "gridcolor": "#dfe7e3",
            },
            "angularaxis": {"gridcolor": "#e5ebe8", "showticklabels": False},
            "bgcolor": "#ffffff",
        },
        template="plotly_white",
        paper_bgcolor="#ffffff",
        font={"color": "#18211e"},
        height=height,
        legend={"orientation": "h", "y": -0.08, "x": 0},
        hoverlabel={"align": "left", "bgcolor": "#ffffff", "font": {"color": "#18211e"}},
        margin={"t": 25, "b": 45, "l": 55, "r": 55},
    )
    return fig


def ranking_bar_chart(scores: pd.DataFrame, *, limit: int = 8, height: int = 430) -> go.Figure:
    view = scores.head(limit).sort_values("score", ascending=True).copy()
    colors = [BROKER_COLORS.get(slug, "#72827b") for slug in view["broker_slug"]]
    fig = go.Figure(
        go.Bar(
            x=view["score"],
            y=view["broker_name"],
            orientation="h",
            marker={"color": colors},
            text=[f"{value:.1f}" for value in view["score"]],
            textposition="outside",
            customdata=view[["confidence", "evidence_count"]],
            hovertemplate=(
                "%{y}<br>Fit %{x:.1f}/100<br>Confidence %{customdata[0]:.0f}"
                "<br>%{customdata[1]} linked evidence items<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#18211e", "size": 11},
        height=height,
        xaxis={"range": [0, 104], "gridcolor": "#e6ece8", "title": "Fit score"},
        yaxis={"title": "", "automargin": True},
        margin={"t": 20, "b": 45, "l": 20, "r": 42},
        showlegend=False,
    )
    return fig


def compact_leaderboard(
    frame: pd.DataFrame,
    *,
    value_col: str = "score",
    limit: int = 5,
    suffix: str = "",
    height: int = 245,
) -> go.Figure:
    view = frame.head(limit).sort_values(value_col, ascending=True).copy()
    fig = go.Figure(
        go.Bar(
            x=view[value_col],
            y=view["broker_name"],
            orientation="h",
            marker={"color": [BROKER_COLORS.get(slug, "#687972") for slug in view["broker_slug"]]},
            text=[f"{value:.1f}{suffix}" for value in view[value_col]],
            textposition="outside",
            hovertemplate=f"%{{y}}<br>%{{x:.2f}}{suffix}<extra></extra>",
        )
    )
    upper = max(100.0, float(view[value_col].max()) * 1.13) if not view.empty else 100.0
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#18211e", "size": 11},
        height=height,
        xaxis={"range": [0, upper], "showgrid": False, "showticklabels": False, "zeroline": False},
        yaxis={"title": "", "automargin": True},
        margin={"t": 8, "b": 8, "l": 8, "r": 44},
        showlegend=False,
    )
    return fig


def review_platform_heatmap(frame: pd.DataFrame, *, height: int = 420) -> go.Figure:
    source_order = ["apple_app_store", "google_play", "trustpilot"]
    source_labels = {
        "apple_app_store": "Apple App Store",
        "google_play": "Google Play",
        "trustpilot": "Trustpilot",
    }
    brokers = sorted(frame["broker_name"].dropna().unique().tolist())
    ratings = frame.pivot_table(
        index="broker_name", columns="source_slug", values="rating_raw", aggfunc="first"
    ).reindex(index=brokers, columns=source_order)
    counts = frame.pivot_table(
        index="broker_name", columns="source_slug", values="review_count", aggfunc="first"
    ).reindex(index=brokers, columns=source_order)
    dates = frame.pivot_table(
        index="broker_name", columns="source_slug", values="as_of_date", aggfunc="first"
    ).reindex(index=brokers, columns=source_order)
    notes = frame.pivot_table(
        index="broker_name", columns="source_slug", values="source_notes", aggfunc="first"
    ).reindex(index=brokers, columns=source_order)
    text = [
        [f"{value:.1f}" if pd.notna(value) else "" for value in row]
        for row in ratings.values
    ]
    customdata = [
        [
            [
                int(counts.loc[broker, source]) if pd.notna(counts.loc[broker, source]) else 0,
                dates.loc[broker, source] if pd.notna(dates.loc[broker, source]) else "Not available",
                _hover_wrap(notes.loc[broker, source]) if pd.notna(notes.loc[broker, source]) else "",
            ]
            for source in source_order
        ]
        for broker in brokers
    ]
    fig = go.Figure(
        go.Heatmap(
            z=ratings.values,
            x=[source_labels[source] for source in source_order],
            y=brokers,
            zmin=1,
            zmax=5,
            colorscale=[[0, "#bd594b"], [0.47, "#e7bf59"], [1, "#138568"]],
            text=text,
            texttemplate="%{text}",
            textfont={"size": 11},
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>%{x}: %{z:.1f}/5"
                "<br>%{customdata[0]:,} public ratings"
                "<br>As of %{customdata[1]}"
                "<br><br>%{customdata[2]}<extra></extra>"
            ),
            colorbar={"title": "/5", "thickness": 10, "len": 0.72},
            hoverongaps=False,
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f2f5f3",
        font={"color": "#18211e", "size": 10},
        height=height,
        xaxis={"side": "top", "tickfont": {"size": 10}, "fixedrange": True},
        yaxis={"autorange": "reversed", "automargin": True, "fixedrange": True},
        hoverlabel={"align": "left", "bgcolor": "#ffffff", "font": {"color": "#18211e"}},
        margin={"t": 48, "b": 18, "l": 15, "r": 18},
    )
    return fig


def sentiment_balance_chart(frame: pd.DataFrame, *, height: int = 420) -> go.Figure:
    view = frame.sort_values(["net", "positive"], ascending=True).copy()
    positive_custom = view[["positive", "mixed", "evidence_count"]].to_numpy()
    negative_custom = view[["negative", "mixed", "evidence_count"]].to_numpy()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=-view["negative_share"],
            y=view["broker_name"],
            orientation="h",
            name="Negative",
            marker_color="#c45f4b",
            text=[f"{value:.0f}%" if value >= 12 else "" for value in view["negative_share"]],
            textposition="inside",
            customdata=negative_custom,
            hovertemplate=(
                "<b>%{y}</b><br>Negative: %{customdata[0]:,.0f} approximate mentions"
                "<br>Mixed: %{customdata[1]:,.0f}"
                "<br>%{customdata[2]:,.0f} linked theme records<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            x=view["positive_share"],
            y=view["broker_name"],
            orientation="h",
            name="Positive",
            marker_color="#138568",
            text=[f"{value:.0f}%" if value >= 12 else "" for value in view["positive_share"]],
            textposition="inside",
            customdata=positive_custom,
            hovertemplate=(
                "<b>%{y}</b><br>Positive: %{customdata[0]:,.0f} approximate mentions"
                "<br>Mixed: %{customdata[1]:,.0f}"
                "<br>%{customdata[2]:,.0f} linked theme records<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        barmode="relative",
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#18211e", "size": 10},
        height=height,
        xaxis={
            "range": [-100, 100],
            "tickvals": [-100, -50, 0, 50, 100],
            "ticktext": ["100% negative", "50%", "0", "50%", "100% positive"],
            "gridcolor": "#e5ebe8",
            "zeroline": True,
            "zerolinecolor": "#66766f",
            "fixedrange": True,
        },
        yaxis={"title": "", "automargin": True, "fixedrange": True},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        hoverlabel={"align": "left", "bgcolor": "#ffffff", "font": {"color": "#18211e"}},
        margin={"t": 48, "b": 38, "l": 15, "r": 18},
    )
    return fig


def competitive_gap_chart(
    dimension_scores: pd.DataFrame,
    broker_slug: str,
    *,
    limit: int = 8,
    height: int = 350,
) -> go.Figure:
    leader_index = dimension_scores.groupby("dim_slug")["score"].idxmax()
    market_leaders = dimension_scores.loc[
        leader_index, ["dim_slug", "broker_name", "score"]
    ].rename(columns={"broker_name": "leader_name", "score": "leader_score"})
    selected = dimension_scores[dimension_scores["broker_slug"] == broker_slug].copy()
    selected = selected.merge(market_leaders, on="dim_slug", how="left")
    selected["gap"] = selected["score"] - selected["leader_score"]
    selected = selected.sort_values("gap").head(limit).sort_values("gap", ascending=False)
    colors = ["#178465" if value >= -3 else "#c8644b" for value in selected["gap"]]
    help_data = _dimension_help(selected)
    customdata = [
        [*help_row, float(row["score"]), row["leader_name"], float(row["leader_score"])]
        for help_row, (_, row) in zip(help_data, selected.iterrows())
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=selected["gap"],
            y=selected["dim_name"],
            xaxis="x2",
            orientation="h",
            marker_color=colors,
            text=["Leader" if value >= -0.05 else f"{value:.0f}" for value in selected["gap"]],
            textposition="auto",
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>%{customdata[0]}"
                "<br><br><b>How it is measured</b><br>%{customdata[1]}"
                "<br><br><b>Selected score</b> %{customdata[4]:.0f}/100"
                "<br><b>Category leader</b> %{customdata[5]} · %{customdata[6]:.0f}/100"
                "<br><b>Gap</b> %{x:.1f} points"
                "<br>Confidence %{customdata[2]:.0f}/100 · %{customdata[3]} evidence items"
                "<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0.5] * len(selected),
            y=selected["dim_name"],
            mode="text+markers",
            text=selected["dim_name"],
            textposition="middle center",
            textfont={"size": 11, "color": "#53625c"},
            marker={
                "size": [min(230, max(120, len(name) * 7)) for name in selected["dim_name"]],
                "symbol": "square",
                "color": "rgba(255, 255, 255, 0.01)",
                "line": {"width": 0},
            },
            customdata=_category_help(selected),
            hovertemplate=(
                "<b>%{text}</b><br>%{customdata[0]}"
                "<br><br><b>How it is measured</b><br>%{customdata[1]}"
                "<extra></extra>"
            ),
            showlegend=False,
            name="Category definitions",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#18211e", "size": 11},
        height=height,
        xaxis={"domain": [0.0, 0.29], "range": [0, 1], "visible": False, "fixedrange": True},
        xaxis2={
            "domain": [0.31, 1.0],
            "title": "Points behind category leader",
            "gridcolor": "#e5ebe8",
            "range": [-65, 3],
            "anchor": "y",
            "fixedrange": True,
        },
        yaxis={
            "title": "",
            "showticklabels": False,
            "range": [-0.5, max(0.5, len(selected) - 0.5)],
            "fixedrange": True,
        },
        hoverlabel={"align": "left", "bgcolor": "#ffffff", "font": {"color": "#18211e"}},
        margin={"t": 10, "b": 45, "l": 15, "r": 20},
        showlegend=False,
    )
    return fig


def dimension_heatmap(
    ds: pd.DataFrame,
    broker_slugs: list[str],
    dimension_slugs: list[str],
    *,
    height: int = 360,
) -> go.Figure:
    view = ds[
        ds["broker_slug"].isin(broker_slugs) & ds["dim_slug"].isin(dimension_slugs)
    ].copy()
    names = view.drop_duplicates("broker_slug").set_index("broker_slug")["broker_name"]
    dim_names = view.drop_duplicates("dim_slug").set_index("dim_slug")["dim_name"]
    matrix = view.pivot_table(index="dim_slug", columns="broker_slug", values="score")
    matrix = matrix.reindex(index=dimension_slugs, columns=broker_slugs)
    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=[names.get(slug, slug) for slug in broker_slugs],
            y=[dim_names.get(slug, slug) for slug in dimension_slugs],
            zmin=30,
            zmax=100,
            colorscale=[[0, "#b85c4d"], [0.45, "#f0cf78"], [1, "#0b8062"]],
            text=[[f"{value:.0f}" if pd.notna(value) else "-" for value in row] for row in matrix.values],
            texttemplate="%{text}",
            hovertemplate="%{y}<br>%{x}: %{z:.0f}/100<extra></extra>",
            colorbar={"title": "Score", "thickness": 10},
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        font={"color": "#18211e", "size": 10},
        height=height,
        margin={"t": 20, "b": 55, "l": 20, "r": 20},
        xaxis={"side": "bottom"},
        yaxis={"autorange": "reversed", "automargin": True},
    )
    return fig


def score_bar(df: pd.DataFrame, x: str, y: str, color_slug_col: str | None = None,
              title: str | None = None, *, height: int = 360) -> go.Figure:
    colors = (
        [BROKER_COLORS.get(s, "#888") for s in df[color_slug_col]]
        if color_slug_col
        else "#4c78a8"
    )
    fig = go.Figure(go.Bar(x=df[x], y=df[y], marker_color=colors,
                           text=[f"{v:.1f}" for v in df[y]], textposition="outside"))
    fig.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#18211e"},
        yaxis={"range": [0, 105], "gridcolor": "#e6ece8"},
        height=height,
        margin={"t": 40, "b": 20, "l": 30, "r": 20},
    )
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
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        font={"color": "#18211e"},
        height=420,
        margin={"t": 20, "b": 20},
        xaxis={"tickangle": -35},
    )
    return fig
