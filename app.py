# -*- coding: utf-8 -*-
"""
Created on Tue Dec  9 16:14:10 2025

@author: ChristinaBakatsi
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="OASA Metro Insight Hub", layout="wide")

FILE_PATH = r"C:\Users\ChristinaBakatsi\OneDrive - NAMA AE\oasa_ridership_2024\oasa_ridership_01_2024.xlsx"
SHEET_NAME = "Sheet1"

# =========================
# 6-COLOR PALETTE (stable)
# =========================
PALETTE6 = [
    "#3b82f6",  # blue
    "#ef4444",  # red
    "#f59e0b",  # amber
    "#22c55e",  # green
    "#a855f7",  # purple
    "#06b6d4",  # cyan
]

# =========================
# DARK UI (CSS)
# =========================
st.markdown(
    """
<style>
.stApp { background: #0b1220; color: #e5e7eb; }
.block-container { padding-top: 0.7rem; }

section[data-testid="stSidebar"]{
    background: #0f172a;
    border-right: 1px solid #1f2937;
}
section[data-testid="stSidebar"] * { color: #e5e7eb; }

.card {
    background: #0f172a;
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.card-title {
    font-weight: 800;
    font-size: 14px;
    color: #e5e7eb;
    margin-bottom: 6px;
}
.small-muted { color:#9ca3af; font-size: 12px; }
.status-green { color:#22c55e; font-weight: 800; }

.big-number { font-size: 30px; font-weight: 900; line-height: 1.0; color:#e5e7eb; }
.metric-label { color:#9ca3af; font-size: 12px; }

.plot-card { padding-top: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HELPERS
# =========================
def apply_dark_plotly(fig, height=None):
    """Force plotly into real dark mode (transparent backgrounds for cards)."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=10, r=10, t=45, b=10),
        title_font=dict(size=14),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(
        gridcolor="rgba(148,163,184,0.18)",
        zerolinecolor="rgba(148,163,184,0.25)",
        tickfont=dict(color="#cbd5e1"),
        titlefont=dict(color="#cbd5e1"),
    )
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.18)",
        zerolinecolor="rgba(148,163,184,0.25)",
        tickfont=dict(color="#cbd5e1"),
        titlefont=dict(color="#cbd5e1"),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def to_categorical_for_color(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Convert numeric/bool columns to string so Plotly uses discrete palette cleanly."""
    if col is None or col not in df.columns:
        return df
    d = df.copy()
    if pd.api.types.is_bool_dtype(d[col]) or pd.api.types.is_numeric_dtype(d[col]):
        d[col] = d[col].astype(str)
    return d


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=SHEET_NAME)

    df["date_hour"] = pd.to_datetime(df["date_hour"], errors="coerce")
    df = df.dropna(subset=["date_hour"]).copy()

    df["dv_validations"] = pd.to_numeric(df["dv_validations"], errors="coerce").fillna(0)

    df["date"] = df["date_hour"].dt.date
    df["hour"] = df["date_hour"].dt.hour
    df["dow"] = df["date_hour"].dt.day_name()
    df["is_weekend"] = df["date_hour"].dt.weekday >= 5

    # Clean text columns
    for col in ["dv_platenum_station", "dv_agency"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# =========================
# LOAD
# =========================
df = load_data(FILE_PATH)

min_dt = df["date_hour"].min()
max_dt = df["date_hour"].max()

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.header("Filters")

stops = sorted(df["dv_platenum_station"].dropna().unique()) if "dv_platenum_station" in df.columns else []
agencies = sorted(df["dv_agency"].dropna().unique()) if "dv_agency" in df.columns else []

default_stop = stops[:1] if stops else []
sel_stops = st.sidebar.multiselect("Stop", stops, default=default_stop)
sel_agencies = st.sidebar.multiselect("Agency", agencies, default=agencies)

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_dt.date(), max_dt.date()),
    min_value=min_dt.date(),
    max_value=max_dt.date(),
)

hour_range = st.sidebar.slider("Hour range", 0, 23, (0, 23))

only_weekend = st.sidebar.checkbox("Only weekend", value=False)
only_weekdays = st.sidebar.checkbox("Only weekdays", value=False)

if only_weekend and only_weekdays:
    st.sidebar.warning(
        "Both 'Only weekend' and 'Only weekdays' are selected. No day-type filter will be applied (All days)."
    )

# =========================
# CHART COLOR CONTROLS (restricted)
# =========================
st.sidebar.divider()
st.sidebar.subheader("Chart colors")

COLOR_CHOICES_COMMON = {
    "Stop": "dv_platenum_station",
    "Hour": "hour",
    "Day of week": "dow",
}

# Left panel: keep Stop
st.sidebar.selectbox(
    "Left panel (map placeholder): color by",
    options=["Stop"],
    index=0,
)
colorby_left_col = "dv_platenum_station"

# Trend line: Stop / Hour / Day of week
colorby_ts_label = st.sidebar.selectbox(
    "Trend line: color by",
    options=["Stop", "Hour", "Day of week"],
    index=2,
)
colorby_ts_col = COLOR_CHOICES_COMMON[colorby_ts_label]

# Top 5 bars: Stop / Hour / Day of week
colorby_top5_label = st.sidebar.selectbox(
    "Top 5 bars: color by",
    options=["Stop", "Hour", "Day of week"],
    index=0,
)
colorby_top5_col = COLOR_CHOICES_COMMON[colorby_top5_label]

# Avg by hour: Stop / Day of week
colorby_hourly_label = st.sidebar.selectbox(
    "Avg by hour: color by",
    options=["Stop", "Day of week"],
    index=1,
)
colorby_hourly_col = {"Stop": "dv_platenum_station", "Day of week": "dow"}[colorby_hourly_label]

# =========================
# APPLY FILTERS
# =========================
f = df.copy()

if sel_stops and "dv_platenum_station" in f.columns:
    f = f[f["dv_platenum_station"].isin(sel_stops)]
if sel_agencies and "dv_agency" in f.columns:
    f = f[f["dv_agency"].isin(sel_agencies)]

start_date, end_date = date_range
f = f[(f["date_hour"].dt.date >= start_date) & (f["date_hour"].dt.date <= end_date)]
f = f[(f["hour"] >= hour_range[0]) & (f["hour"] <= hour_range[1])]

# Day-type filters
if only_weekend and not only_weekdays:
    f = f[f["is_weekend"]]
elif only_weekdays and not only_weekend:
    f = f[~f["is_weekend"]]

if f.empty:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">No data</div>
            <div class="small-muted">The selected filters returned an empty dataset.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# =========================
# HEADER
# =========================
now = datetime.now().strftime("%A, %b %d, %Y, %H:%M")
st.markdown(
    f"""
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="font-weight:900; letter-spacing:0.3px;">OASA METRO INSIGHT HUB</div>
    <div class="small-muted">
      SYSTEM STATUS: <span class="status-green">● Normal Operations</span> | {now}
    </div>
  </div>
  <div class="small-muted" style="margin-top:8px;">
    Data coverage: {min_dt:%Y-%m-%d %H:00} to {max_dt:%Y-%m-%d %H:00}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# KPIs
# =========================
total_val = int(f["dv_validations"].sum())
active_hours = int(f["date_hour"].nunique())
mean_validations_per_hour = (total_val / active_hours) if active_hours else 0
active_stops = int(f["dv_platenum_station"].nunique()) if "dv_platenum_station" in f.columns else 0

peak_row = (
    f.groupby("date_hour", as_index=False)["dv_validations"].sum()
    .sort_values("dv_validations", ascending=False)
    .head(1)
)
peak_txt = "—"
if not peak_row.empty:
    peak_txt = f'{peak_row.iloc[0]["date_hour"]:%Y-%m-%d %H:00} ({int(peak_row.iloc[0]["dv_validations"]):,})'

# =========================
# MAIN LAYOUT
# =========================
left, right = st.columns([2.25, 1.0], gap="large")

# -------- LEFT: "Network view" placeholder + Top stops
with left:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">Network View</div>
            <div class="small-muted">Currently shown as a ranked panel. We can replace this with a GIS map / schematic once geometry/topology is provided.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    topN_left = 12
    top_left = (
        f.groupby("dv_platenum_station", as_index=False)["dv_validations"].sum()
        .sort_values("dv_validations", ascending=False)
        .head(topN_left)
        .rename(columns={"dv_platenum_station": "Stop", "dv_validations": "Validations"})
    )

    top_left = to_categorical_for_color(top_left, "Stop")

    fig_left = px.bar(
        top_left,
        x="Validations",
        y="Stop",
        orientation="h",
        title=f"Top {topN_left} Stops (current filters)",
        color="Stop",
        color_discrete_sequence=PALETTE6,
        labels={"Validations": "Validations", "Stop": "Stop"},
    )
    fig_left.update_layout(showlegend=False)
    fig_left = apply_dark_plotly(fig_left, height=520)
    fig_left.update_xaxes(title_text="Validations")
    fig_left.update_yaxes(title_text="Stop")

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_left, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

# -------- RIGHT: KPI + 2 charts stacked
with right:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Key Metrics (Filtered)</div>
            <div style="display:flex; gap:14px; justify-content:space-between;">
                <div style="flex:1;">
                    <div class="metric-label">Active Stops</div>
                    <div class="big-number">{active_stops:,}</div>
                </div>
                <div style="flex:1;">
                    <div class="metric-label">Mean validations/hour</div>
                    <div class="big-number">{mean_validations_per_hour:,.1f}</div>
                </div>
                <div style="flex:1;">
                    <div class="metric-label">Total Validations</div>
                    <div class="big-number">{total_val/1000:,.1f}K</div>
                </div>
            </div>
            <div class="small-muted" style="margin-top:10px;">Peak hour: {peak_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Trend (hourly sum)
    f_ts = to_categorical_for_color(f, colorby_ts_col)
    ts = (
        f_ts.groupby(["date_hour", colorby_ts_col], as_index=False)["dv_validations"].sum()
        .rename(columns={"dv_validations": "Validations"})
    )

    fig_ts = px.line(
        ts,
        x="date_hour",
        y="Validations",
        color=colorby_ts_col,
        title=f"Ridership Trend (Hourly sum) — by {colorby_ts_label}",
        color_discrete_sequence=PALETTE6,
        labels={"date_hour": "Date-hour", "Validations": "Validations"},
    )
    fig_ts.update_layout(legend_title_text=colorby_ts_label)
    fig_ts = apply_dark_plotly(fig_ts, height=260)
    fig_ts.update_xaxes(title_text="Date-hour")
    fig_ts.update_yaxes(title_text="Validations")

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_ts, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Top 5 bars (sum)
    top5_base = (
        f.groupby("dv_platenum_station", as_index=False)["dv_validations"].sum()
        .sort_values("dv_validations", ascending=False)
        .head(5)
        .rename(columns={"dv_platenum_station": "Stop", "dv_validations": "Validations"})
    )
    top5_stops = set(top5_base["Stop"].tolist())
    ff = f[f["dv_platenum_station"].isin(top5_stops)].copy()

    if colorby_top5_col == "dv_platenum_station":
        top5 = to_categorical_for_color(top5_base, "Stop")
        fig_top5 = px.bar(
            top5,
            x="Stop",
            y="Validations",
            title="Top 5 Stops (sum) — by Stop",
            color="Stop",
            color_discrete_sequence=PALETTE6,
            labels={"Stop": "Stop", "Validations": "Validations"},
        )
        fig_top5.update_layout(showlegend=False)
        fig_top5.update_xaxes(title_text="Stop")
    else:
        ff = to_categorical_for_color(ff, colorby_top5_col)
        top5 = (
            ff.groupby(colorby_top5_col, as_index=False)["dv_validations"].sum()
            .sort_values("dv_validations", ascending=False)
            .rename(columns={"dv_validations": "Validations"})
        )
        fig_top5 = px.bar(
            top5,
            x=colorby_top5_col,
            y="Validations",
            title=f"Top 5 Stops (sum) — aggregated by {colorby_top5_label}",
            color=colorby_top5_col,
            color_discrete_sequence=PALETTE6,
            labels={"Validations": "Validations"},
        )
        fig_top5.update_layout(showlegend=False)
        fig_top5.update_xaxes(title_text=colorby_top5_label)

    fig_top5 = apply_dark_plotly(fig_top5, height=260)
    fig_top5.update_yaxes(title_text="Validations")

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_top5, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# BOTTOM ROW: Avg by hour + Heatmap
# =========================
st.markdown('<div class="card"><div class="card-title">Additional Analytics</div></div>', unsafe_allow_html=True)

b1, b2 = st.columns([1, 1], gap="large")

with b1:
    fh = to_categorical_for_color(f, colorby_hourly_col)
    hp = (
        fh.groupby(["hour", colorby_hourly_col], as_index=False)["dv_validations"].mean()
        .rename(columns={"dv_validations": "Mean validations"})
    )

    fig_hp = px.bar(
        hp,
        x="hour",
        y="Mean validations",
        color=colorby_hourly_col,
        barmode="group",
        title=f"Average by Hour (mean) — by {colorby_hourly_label}",
        color_discrete_sequence=PALETTE6,
        labels={"hour": "Hour", "Mean validations": "Mean validations"},
    )
    fig_hp.update_layout(legend_title_text=colorby_hourly_label)
    fig_hp = apply_dark_plotly(fig_hp, height=330)
    fig_hp.update_xaxes(title_text="Hour")
    fig_hp.update_yaxes(title_text="Mean validations")

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_hp, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    hm = (
        f.groupby(["date", "hour"], as_index=False)["dv_validations"].sum()
        .pivot(index="date", columns="hour", values="dv_validations")
        .fillna(0)
        .sort_index()
    )
    fig_hm = px.imshow(
        hm,
        aspect="auto",
        title="Heatmap (day × hour) — sum of validations",
        labels={"x": "Hour", "y": "Date", "color": "Validations"},
    )
    fig_hm = apply_dark_plotly(fig_hm, height=330)
    fig_hm.update_xaxes(title_text="Hour")
    fig_hm.update_yaxes(title_text="Date")

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_hm, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Heatmap interpretation: each cell represents the **sum of validations** for a specific **day (row)** "
        "and **hour (column)**, after applying the filters."
    )

# =========================
# EXPORT + DATA QUALITY
# =========================
exp1, exp2 = st.columns([1, 1], gap="large")



with exp2:
    all_days = pd.date_range(min_dt.date(), max_dt.date(), freq="D").date
    present_days = set(df["date_hour"].dt.date.unique())
    missing_days = [d for d in all_days if d not in present_days]

    if missing_days:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Data Quality</div>
              <div class="small-muted">Missing days detected:</div>
              <div style="margin-top:6px;">{", ".join([d.isoformat() for d in missing_days])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Data Quality</div>
              <div class="small-muted">No missing days detected in the period.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
































































