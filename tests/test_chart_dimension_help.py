import pandas as pd

from frontend.streamlit_app.components.charts import (
    BROKER_COLORS,
    competitive_gap_chart,
    radar_chart,
    review_platform_heatmap,
    sentiment_balance_chart,
)


def _scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "broker_slug": "merrill",
                "broker_name": "Merrill Edge",
                "dim_slug": "fractional_shares",
                "dim_name": "Fractional Shares Support",
                "dim_description": "Availability and breadth of fractional-share investing.",
                "sort_order": 16,
                "score": 34.0,
                "confidence": 72.0,
                "evidence_count": 5,
            },
            {
                "broker_slug": "fidelity",
                "broker_name": "Fidelity",
                "dim_slug": "fractional_shares",
                "dim_name": "Fractional Shares Support",
                "dim_description": "Availability and breadth of fractional-share investing.",
                "sort_order": 16,
                "score": 92.0,
                "confidence": 88.0,
                "evidence_count": 7,
            },
        ]
    )


def test_competitive_gap_hover_explains_measurement() -> None:
    figure = competitive_gap_chart(_scores(), "merrill", limit=1)
    trace, category_labels = figure.data

    assert "How it is measured" in trace.hovertemplate
    assert "0.5 = broker ETFs only" in trace.customdata[0][1].replace("<br>", " ")
    assert trace.customdata[0][5] == "Fidelity"
    assert trace.customdata[0][6] == 92.0
    assert category_labels.text[0] == "Fractional Shares Support"
    assert "How it is measured" in category_labels.hovertemplate
    assert trace.xaxis == "x2"
    assert tuple(figure.layout.xaxis2.range) == (-65, 3)
    assert tuple(figure.layout.xaxis2.domain) == (0.31, 1.0)
    assert tuple(figure.layout.yaxis.range) == (-0.5, 0.5)


def test_radar_hover_includes_description_and_evidence() -> None:
    figure = radar_chart(_scores(), ["merrill"], ["fractional_shares"])
    trace = figure.data[0]
    category_labels = figure.data[-1]

    assert "How it is measured" in trace.hovertemplate
    assert "Availability and breadth" in trace.customdata[0][0]
    assert trace.customdata[0][2:] == [72.0, 5]
    assert category_labels.text[0] == "Fractional Shares Support"
    assert "Current purchase scope" in category_labels.customdata[0][1]
    assert figure.layout.polar.angularaxis.showticklabels is False
    assert category_labels.r[0] == 124
    assert tuple(figure.layout.polar.radialaxis.range) == (0, 136)


def test_active_broker_palette_uses_distinct_colors() -> None:
    active_slugs = {
        "fidelity", "schwab", "vanguard", "robinhood", "ibkr", "etrade",
        "merrill", "sofi", "webull", "public", "jpmorgan",
    }
    active_colors = [BROKER_COLORS[slug] for slug in active_slugs]

    assert len(active_colors) == len(set(active_colors))


def test_radar_uses_strong_lines_and_light_distinct_fills() -> None:
    figure = radar_chart(_scores(), ["merrill", "fidelity"], ["fractional_shares"])
    first, second = figure.data[:2]

    assert first.line.color != second.line.color
    assert first.fillcolor != second.fillcolor
    assert first.line.width == 2.6
    assert first.marker.symbol != second.marker.symbol
    assert first.fillcolor.endswith(", 0.14)")


def test_review_comparison_charts_expose_source_context() -> None:
    ratings = pd.DataFrame(
        [
            {
                "broker_name": "Fidelity",
                "source_slug": "apple_app_store",
                "rating_raw": 4.8,
                "review_count": 2_400_000,
                "as_of_date": "2026-07-01",
                "source_notes": "Prompted public app-store ratings.",
            },
            {
                "broker_name": "Fidelity",
                "source_slug": "trustpilot",
                "rating_raw": 1.6,
                "review_count": 3_500,
                "as_of_date": "2026-07-01",
                "source_notes": "Self-selected reviews.",
            },
        ]
    )
    sentiment = pd.DataFrame(
        [
            {
                "broker_name": "Fidelity",
                "positive": 80,
                "negative": 20,
                "mixed": 5,
                "positive_share": 80.0,
                "negative_share": 20.0,
                "net": 60.0,
                "evidence_count": 8,
            }
        ]
    )

    heatmap = review_platform_heatmap(ratings)
    balance = sentiment_balance_chart(sentiment)

    assert "public ratings" in heatmap.data[0].hovertemplate
    assert heatmap.data[0].customdata[0][0][0] == 2_400_000
    assert [trace.name for trace in balance.data] == ["Negative", "Positive"]
