"""Shared visual defaults for WeatherGuard Plotly charts."""
from __future__ import annotations

import plotly.graph_objects as go


def style_chart(fig: go.Figure, height: int = 350) -> go.Figure:
    """Apply consistent colors, legibility defaults, and responsive margins."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#CBD5E1", "family": "Inter, Segoe UI, sans-serif", "size": 12},
        title={"font": {"color": "#F1F5F9", "size": 16}, "x": 0.02, "xanchor": "left"},
        margin={"l": 48, "r": 18, "t": 58, "b": 48},
        legend={"orientation": "h", "yanchor": "top", "y": -0.22, "xanchor": "left", "x": 0},
        hoverlabel={"bgcolor": "#172235", "bordercolor": "#38BDF8", "font": {"color": "#F1F5F9", "size": 12}},
        colorway=["#38BDF8", "#2DD4BF", "#FBBF24", "#A78BFA", "#F87171", "#94A3B8"],
    )
    fig.update_xaxes(gridcolor="#26384E", zerolinecolor="#26384E", tickfont={"size": 10}, automargin=True)
    fig.update_yaxes(gridcolor="#26384E", zerolinecolor="#26384E", tickfont={"size": 10}, automargin=True)
    return fig
