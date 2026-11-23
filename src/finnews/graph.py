from __future__ import annotations

import math

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

NEGATIVE = "#ff7887"
NEUTRAL = "#c1c4c9"
POSITIVE = "#82dc98"


def make_constellation(summary: pd.DataFrame, edges: pd.DataFrame, selected: str | None = None) -> go.Figure:
    """Draw an undirected co-mention network on a stable company ring.

    Position is a stable force-directed layout. Edges represent shared article
    coverage, and their width represents the number of unique shared articles.
    """
    graph = nx.Graph()
    for _, row in summary.iterrows():
        graph.add_node(row["ticker"], company=row["company"])
    for _, row in edges.iterrows():
        if row["source"] in graph and row["target"] in graph:
            graph.add_edge(row["source"], row["target"], weight=max(1, int(row["weight"])))

    if graph.number_of_nodes() == 0:
        return go.Figure()
    ordered_nodes = sorted(graph.nodes)
    if len(ordered_nodes) == 1:
        positions = {ordered_nodes[0]: (0.0, 0.0)}
    elif graph.number_of_edges() == 0:
        positions = nx.circular_layout(ordered_nodes, scale=1.45)
    else:
        positions = nx.spring_layout(
            graph.subgraph(ordered_nodes),
            seed=19,
            k=1.35 / math.sqrt(len(ordered_nodes)),
            iterations=140,
            weight="weight",
            scale=1.55,
        )

    fig = go.Figure()
    edge_rows = list(graph.edges(data=True))
    for source, target, attrs in edge_rows:
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        count = int(attrs.get("weight", 1))
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line={"width": min(3.0, 0.8 + 0.55 * math.sqrt(count)), "color": "#858b91"},
            hoverinfo="text", hovertext=f"{source} ↔ {target}<br>Co-mentioned in {count} article{'s' if count != 1 else ''}",
            showlegend=False,
        ))

    summary_by_ticker = summary.set_index("ticker")
    node_tickers = list(graph.nodes)
    node_x = [positions[ticker][0] for ticker in node_tickers]
    node_y = [positions[ticker][1] for ticker in node_tickers]
    node_text = [str(summary_by_ticker.loc[ticker, "company"]) for ticker in node_tickers]
    scores = [float(summary_by_ticker.loc[ticker, "sentiment_score"]) for ticker in node_tickers]
    sentiment_colors = [
        NEGATIVE if score <= -0.12 else POSITIVE if score >= 0.12 else NEUTRAL
        for score in scores
    ]
    articles = [int(summary_by_ticker.loc[ticker, "article_count"]) for ticker in node_tickers]
    confidence = [float(summary_by_ticker.loc[ticker, "confidence"]) for ticker in node_tickers]
    sentiment_labels = ["Positive" if value >= 0.12 else "Negative" if value <= -0.12 else "Mixed / near neutral" for value in scores]
    sizes = [min(48, 25 + 7 * math.sqrt(count)) for count in articles]
    line_colors = ["#fa7182" if ticker == selected else "#242424" for ticker in node_tickers]
    line_widths = [3.2 if ticker == selected else 1.5 for ticker in node_tickers]

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[ticker for ticker in node_tickers], textposition="bottom center",
        textfont={"family": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif", "size": 11, "color": "#e4e2df"},
        customdata=[[ticker, name, label, count, score, conf] for ticker, name, label, count, score, conf in zip(node_tickers, node_text, sentiment_labels, articles, scores, confidence)],
        marker={
            "size": sizes,
            "symbol": "circle",
            "color": sentiment_colors,
            "showscale": False,
            "line": {"color": line_colors, "width": line_widths},
        },
        hovertemplate=(
            "<b>%{customdata[1]}</b> · %{customdata[0]}<br>"
            "%{customdata[2]}<br>"
            "Sentiment index: %{customdata[4]:+.2f}<br>"
            "Articles: %{customdata[3]}<extra></extra>"
        ),
        showlegend=False,
    ))
    fig.update_layout(
        height=360,
        margin={"l": 24, "r": 24, "t": 16, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#f4f2ef", "bordercolor": "#c43a50", "font": {"color": "#181818", "size": 12}},
        clickmode="event+select",
        dragmode="pan",
        xaxis={"visible": False, "fixedrange": False, "showgrid": False, "zeroline": False, "range": [-2.05, 2.05]},
        yaxis={"visible": False, "fixedrange": False, "showgrid": False, "zeroline": False, "scaleanchor": "x", "scaleratio": 1, "range": [-1.9, 1.9]},
        uirevision="constellation:" + ",".join(ordered_nodes) + ":" + str(int(summary["article_count"].sum())),
    )
    return fig

