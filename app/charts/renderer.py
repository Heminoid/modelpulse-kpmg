import matplotlib
matplotlib.use("Agg")  # headless backend, must be set before importing pyplot
import matplotlib.pyplot as plt
import io
import base64

from app.schemas.charts import ChartPayload

# Use dark theme
plt.style.use("dark_background")

def render_bar(ax, payload: ChartPayload):
    for series in payload.series:
        xs = [d["x"] for d in series.data]
        ys = [d["y"] for d in series.data]
        color = series.color if series.color else "#4C8BF5"
        ax.bar(xs, ys, label=series.name, color=color, alpha=0.85)
        # Rotate x labels if they are long strings
        if all(isinstance(x, str) for x in xs) and any(len(x) > 5 for x in xs):
            ax.tick_params(axis='x', rotation=45)

def render_line(ax, payload: ChartPayload):
    for series in payload.series:
        xs = [d["x"] for d in series.data]
        ys = [d["y"] for d in series.data]
        color = series.color if series.color else "#4C8BF5"
        ax.plot(xs, ys, label=series.name, color=color, marker="o", markersize=3)
        if all(isinstance(x, str) for x in xs) and any(len(x) > 5 for x in xs):
            ax.tick_params(axis='x', rotation=45)

def render_histogram(ax, payload: ChartPayload):
    # A histogram here is usually pre-binned data, so it acts like a bar chart
    # where the x-axis are bin edges or bin labels
    render_bar(ax, payload)

def render_scatter(ax, payload: ChartPayload):
    for series in payload.series:
        xs = [d["x"] for d in series.data]
        ys = [d["y"] for d in series.data]
        color = series.color if series.color else "#4C8BF5"
        ax.scatter(xs, ys, label=series.name, color=color, alpha=0.7)

def render_heatmap(ax, payload: ChartPayload):
    # For a heatmap, assume series contains rows of data
    pass # Simple stub, we only need bar/line/histogram for the 10 required charts mostly

CHART_TYPE_RENDERERS = {
    "bar": render_bar,
    "line": render_line,
    "histogram": render_histogram,
    "scatter": render_scatter,
    "heatmap": render_heatmap,
}

def render_chart(payload: ChartPayload, fmt: str = "png", dpi: int = 100) -> bytes:
    """Render a ChartPayload to PNG or SVG bytes using matplotlib."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    
    renderer_fn = CHART_TYPE_RENDERERS.get(payload.chart_type, render_bar)
    renderer_fn(ax, payload)
    
    ax.set_title(payload.title, pad=15, fontsize=12, fontweight="bold")
    if payload.x_label: 
        ax.set_xlabel(payload.x_label)
    if payload.y_label: 
        ax.set_ylabel(payload.y_label)
        
    if payload.annotations:
        for ann in payload.annotations:
            if "y" in ann:
                ax.axhline(ann["y"], color=ann.get("color", "red"), linestyle=ann.get("linestyle", "--"), alpha=0.7, label=ann.get("label"))
            elif "x" in ann:
                ax.axvline(ann["x"], color=ann.get("color", "red"), linestyle=ann.get("linestyle", "--"), alpha=0.7, label=ann.get("label"))
                
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    if payload.chart_type not in ["heatmap"]:
        ax.grid(True, axis='y', alpha=0.15)
        if len(payload.series) > 1 or (payload.annotations and any("label" in a for a in payload.annotations)):
            ax.legend(frameon=False, loc="upper right")
        
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, facecolor=fig.get_facecolor(), transparent=True)
    plt.close(fig)   # critical — prevents memory leak across requests
    buf.seek(0)
    return buf.read()

def render_to_base64(payload: ChartPayload, dpi: int = 100) -> str:
    """Render a ChartPayload to a base64 encoded PNG string."""
    image_bytes = render_chart(payload, fmt="png", dpi=dpi)
    return base64.b64encode(image_bytes).decode('utf-8')
