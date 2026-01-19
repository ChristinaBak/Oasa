# -*- coding: utf-8 -*-
"""
Created on Fri Jan 16 10:57:07 2026

@author: ChristinaBakatsi
"""



import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from pathlib import Path
from typing import Union
import geopandas as gpd
import pydeck as pdk
import unicodedata
import re
from functools import lru_cache
import numpy as np

# =========================
# PATHS / FILES
# =========================
BASE_DIR = Path(__file__).parent

# --- Excel data (Nov 2025) ---
DATA_XLSX_FILES = [
    BASE_DIR / "data" / "Per_Day_Per_Stop_Per_Line_November_2025_a.xlsx",
    BASE_DIR / "data" / "Per_Day_Per_Stop_Per_Line_November_2025_b.xlsx",
]


# --- Shapefiles ---
LINES_SHP = BASE_DIR / "data" / "PT_Lines_Oct2024.shp"          # change if needed
STOPS_SHP = BASE_DIR / "data" / "PT_Stops_Urban_Road.shp"      # change if needed

# Stops shapefile stop-name field (per your screenshot)
STOPS_NAME_COL = "stop_descr"

# Lines shapefile line id field (per your screenshot)
LINES_ID_COL = "line_id"

# =========================
# STREAMLIT CONFIG
# =========================
st.set_page_config(page_title="OASA Bus Insight Hub", layout="wide")

# =========================
# UI THEME
# =========================
PALETTE6 = [
    "#3b82f6",  # blue
    "#ef4444",  # red
    "#f59e0b",  # amber
    "#22c55e",  # green
    "#a855f7",  # purple
    "#06b6d4",  # cyan
]

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
        title_font=dict(color="#cbd5e1"),
    )
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.18)",
        zerolinecolor="rgba(148,163,184,0.25)",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1"),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def to_categorical_for_color(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col is None or col not in df.columns:
        return df
    d = df.copy()
    if pd.api.types.is_bool_dtype(d[col]) or pd.api.types.is_numeric_dtype(d[col]):
        d[col] = d[col].astype(str)
    return d


# Optional manual stop-name fixes (rarely needed if your Excel and stop_descr match well)
STOP_NAME_MAP = {
    # "ΣΥΓΓΡΟΥ-ΦΙΞ": "ΣΥΓΓΡΟΥ ΦΙΞ",
}

# 5-class ramp: red -> orange -> yellow -> light green -> dark green
COLOR_RAMP_5 = [
    [220, 38, 38, 180],    # red
    [249, 115, 22, 180],   # orange
    [250, 204, 21, 180],   # yellow
    [74, 222, 128, 180],   # light green
    [21, 128, 61, 200],    # dark green
]

def add_dynamic_color_bins(
    gdf: pd.DataFrame,
    value_col: str = "Validations",
    n_bins: int = 5,
    include_zeros: bool = True,
) -> tuple[pd.DataFrame, list[float]]:
    """
    Adds a 'fill_color' column (RGBA list) based on dynamic bins between min/max.
    Bins are recomputed for the current filtered dataset.
    Returns (gdf_with_colors, bin_edges).
    """
    d = gdf.copy()

    v = pd.to_numeric(d[value_col], errors="coerce").fillna(0)

    # Decide what range to use for min/max (usually include zeros so 0 is "really low")
    if include_zeros:
        v_for_range = v
    else:
        v_for_range = v[v > 0]  # if you ever want to ignore zeros for binning

    if v_for_range.empty:
        # everything is 0 -> all red
        d["fill_color"] = [COLOR_RAMP_5[0]] * len(d)
        return d, [0, 0]

    vmin = float(v_for_range.min())
    vmax = float(v_for_range.max())

    # Edge case: constant values
    if np.isclose(vmin, vmax):
        d["fill_color"] = [COLOR_RAMP_5[-1]] * len(d)  # all "high"
        return d, [vmin, vmax]

    # Equal-width bins between vmin..vmax
    edges = np.linspace(vmin, vmax, n_bins + 1).tolist()

    # pd.cut -> 0..n_bins-1
    cats = pd.cut(v, bins=edges, include_lowest=True, labels=False)
    cats = cats.fillna(0).astype(int).clip(0, n_bins - 1)

    ramp = COLOR_RAMP_5[:n_bins]

# NEW: store class index (0..n_bins-1)
    d["bin_idx"] = cats

# NEW: store color from class index
    d["fill_color"] = d["bin_idx"].map(lambda i: ramp[int(i)]).tolist()

    return d, edges

@lru_cache(maxsize=200000)
def strip_accents_upper_cached(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.strip().upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # remove diacritics
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_stop_series_fast(sr: pd.Series) -> pd.Series:
    """
    Fast normalization using unique mapping (much faster than per-row map/apply on huge data).
    """
    s = sr.astype(str)
    uniq = pd.Index(s.dropna().unique())
    norm_map = {u: strip_accents_upper_cached(u) for u in uniq}
    out = s.map(norm_map)

    if STOP_NAME_MAP:
        map_norm = {strip_accents_upper_cached(k): strip_accents_upper_cached(v) for k, v in STOP_NAME_MAP.items()}
        out = out.replace(map_norm)

    return out


def parse_line_id_from_excel_vectorized(line_route_series: pd.Series) -> pd.Series:
    """
    Vectorized extraction of line id from LINE_ROUTE like:
    '040 - ...' -> '040' and numeric padding (21 -> 021).
    """
    s = line_route_series.astype(str).str.strip()

    line_id = (
        s.str.extract(r"^\s*([A-Z0-9Α-Ω]+)\s*-\s*", expand=False)
        .fillna(s.str.split("-", n=1).str[0].str.strip())
        .str.upper()
    )

    mask_num = line_id.str.fullmatch(r"\d+")
    line_id.loc[mask_num] = line_id.loc[mask_num].str.zfill(3)
    return line_id


def norm_line_id_shp(series: pd.Series) -> pd.Series:
    """
    Normalize shapefile line_id: uppercase + pad numeric ids to 3 digits.
    """
    s = series.astype(str).str.strip().str.upper()
    mask_num = s.str.fullmatch(r"\d+")
    s.loc[mask_num] = s.loc[mask_num].str.zfill(3)
    return s


# =========================
# LOADERS
# =========================
@st.cache_data(show_spinner=False)
def load_excel_data(path: Union[str, Path]) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Clean column names
    df.columns = df.columns.astype(str).str.strip().str.replace("\ufeff", "", regex=False)

    required = {"DAY", "HOUR", "LINE_ROUTE", "STOP_DESCR", "VALIDATIONS"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Excel is missing required columns: {missing}")

    # Parse DAY (dd/mm/YYYY)
    df["DAY"] = pd.to_datetime(df["DAY"].astype(str).str.strip(), dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DAY"]).copy()

    # Parse HOUR to hour integer
    hour_str = df["HOUR"].astype(str).str.strip()
    parsed_hour = pd.to_datetime(hour_str, format="%H:%M", errors="coerce")
    if parsed_hour.notna().any():
        df["hour"] = parsed_hour.dt.hour
    else:
        df["hour"] = pd.to_numeric(hour_str, errors="coerce").fillna(0).astype(int).clip(0, 23)

    # Build date_hour timestamp
    df["date_hour"] = df["DAY"] + pd.to_timedelta(df["hour"], unit="h")

    # Numeric validations
    df["VALIDATIONS"] = pd.to_numeric(df["VALIDATIONS"], errors="coerce").fillna(0)

    # Derived columns
    df["date"] = df["date_hour"].dt.date
    df["dow"] = df["date_hour"].dt.day_name()
    df["is_weekend"] = df["date_hour"].dt.weekday >= 5

    # Normalize stop names (fast)
    df["stop_norm"] = normalize_stop_series_fast(df["STOP_DESCR"])

    # Line fields
    df["line_route"] = df["LINE_ROUTE"].astype(str).str.strip()
    df["line_id_norm"] = parse_line_id_from_excel_vectorized(df["line_route"])

    return df

@st.cache_data(show_spinner=False)
def load_excel_many(paths: list[Union[str, Path]]) -> pd.DataFrame:
    dfs = []
    for p in paths:
        d = load_excel_data(p)  # reuse your single-file parser
        d["source_file"] = Path(p).name
        dfs.append(d)

    df_all = pd.concat(dfs, ignore_index=True)

    # (Προαιρετικό) αφαίρεση διπλοεγγραφών, αν υπάρχει overlap μεταξύ αρχείων
    # Κλειδί: ίδια ώρα/ημέρα + ίδια γραμμή + ίδια στάση
    df_all = df_all.drop_duplicates(subset=["date_hour", "line_route", "stop_norm"], keep="last")

    return df_all


@st.cache_resource(show_spinner=False)
def load_network_geodata(lines_path: Union[str, Path], stops_path: Union[str, Path]):
    gdf_lines = gpd.read_file(lines_path)
    gdf_stops = gpd.read_file(stops_path)

    # Reproject to WGS84 for web maps
    if gdf_lines.crs is not None and gdf_lines.crs.to_epsg() != 4326:
        gdf_lines = gdf_lines.to_crs("EPSG:4326")
    if gdf_stops.crs is not None and gdf_stops.crs.to_epsg() != 4326:
        gdf_stops = gdf_stops.to_crs("EPSG:4326")

    # Stops lon/lat
    gdf_stops["lon"] = gdf_stops.geometry.x
    gdf_stops["lat"] = gdf_stops.geometry.y

    # Stops name normalization key
    if STOPS_NAME_COL not in gdf_stops.columns:
        raise ValueError(
            f"Stops shapefile does not contain '{STOPS_NAME_COL}'. "
            f"Available columns: {list(gdf_stops.columns)}"
        )
    gdf_stops["stop_norm"] = normalize_stop_series_fast(gdf_stops[STOPS_NAME_COL])

    # Lines id normalization (optional for later filtering/highlight)
    if LINES_ID_COL is not None:
        if LINES_ID_COL not in gdf_lines.columns:
            raise ValueError(
                f"Lines shapefile does not contain '{LINES_ID_COL}'. "
                f"Available columns: {list(gdf_lines.columns)}"
            )
        gdf_lines["line_id_norm"] = norm_line_id_shp(gdf_lines[LINES_ID_COL])

    return gdf_lines, gdf_stops


# =========================
# LOAD DATA
# =========================
df = load_excel_many(DATA_XLSX_FILES)

gdf_lines, gdf_stops = load_network_geodata(LINES_SHP, STOPS_SHP)

min_dt = df["date_hour"].min()
max_dt = df["date_hour"].max()

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.header("Filters")

all_stops = sorted(df["STOP_DESCR"].dropna().unique().tolist())
all_lines = sorted(df["line_route"].dropna().unique().tolist())

sel_stops = st.sidebar.multiselect("Stop (STOP_DESCR)", all_stops, default=[])
sel_lines = st.sidebar.multiselect("Line (LINE_ROUTE)", all_lines, default=[])

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_dt.date(), max_dt.date()),
    min_value=min_dt.date(),
    max_value=max_dt.date(),
    key="date_range",
)

hour_range = st.sidebar.slider("Hour range", 0, 23, (0, 23))

only_weekend = st.sidebar.checkbox("Only weekend", value=False)
only_weekdays = st.sidebar.checkbox("Only weekdays", value=False)
if only_weekend and only_weekdays:
    st.sidebar.warning("Both selected → no day-type filter applied (All days).")

st.sidebar.divider()
st.sidebar.subheader("Chart colors")

COLOR_CHOICES = {
    "Stop": "STOP_DESCR",
    "Line": "line_id_norm",  # show code-like id
    "Hour": "hour",
    "Day of week": "dow",
}

colorby_ts_label = st.sidebar.selectbox(
    "Trend line: color by",
    options=list(COLOR_CHOICES.keys()),
    index=2,  # Hour
)
colorby_ts_col = COLOR_CHOICES[colorby_ts_label]

colorby_top_label = st.sidebar.selectbox(
    "Top bars: color by",
    options=["Stop", "Line", "Day of week", "Hour"],
    index=0,
)
colorby_top_col = COLOR_CHOICES[colorby_top_label]

colorby_hourly_label = st.sidebar.selectbox(
    "Avg by hour: color by",
    options=["Stop", "Line", "Day of week"],
    index=1,
)
colorby_hourly_col = COLOR_CHOICES[colorby_hourly_label]

# =========================
# APPLY FILTERS (for analytics/Validations)
# =========================
f = df.copy()

if sel_stops:
    f = f[f["STOP_DESCR"].isin(sel_stops)]
if sel_lines:
    f = f[f["line_route"].isin(sel_lines)]

start_date, end_date = date_range
f = f[(f["date_hour"].dt.date >= start_date) & (f["date_hour"].dt.date <= end_date)]
f = f[(f["hour"] >= hour_range[0]) & (f["hour"] <= hour_range[1])]

if only_weekend and not only_weekdays:
    f = f[f["is_weekend"]]
elif only_weekdays and not only_weekend:
    f = f[~f["is_weekend"]]

# If empty after filters: stop early
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
# MEMBERSHIP SET FOR MAP
# IMPORTANT: membership ignores hour/date/weekend filters
# - If line selected: show all stops that appear for that line during full month
# - Validations still come from f (filtered), so can be 0 and still visible
# =========================
if sel_lines:
    base_for_membership = df[df["line_route"].isin(sel_lines)]
else:
    base_for_membership = df

# If user also selected specific stops, constrain membership accordingly
if sel_stops:
    base_for_membership = base_for_membership[base_for_membership["STOP_DESCR"].isin(sel_stops)]

stops_belong_set = set(base_for_membership["stop_norm"].dropna().unique())

# =========================
# HEADER
# =========================
now = datetime.now().strftime("%A, %b %d, %Y, %H:%M")
st.markdown(
    f"""
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="font-weight:900; letter-spacing:0.3px;">OASA BUS INSIGHT HUB</div>
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
# KPIs (filtered)
# =========================
total_val = int(f["VALIDATIONS"].sum())
active_hours = int(f["date_hour"].nunique())
mean_val_per_hour = (total_val / active_hours) if active_hours else 0

active_stops = int(f["STOP_DESCR"].nunique())
active_lines = int(f["line_id_norm"].nunique())
active_days = int(pd.Series(f["date"]).nunique())

peak_row = (
    f.groupby("date_hour", as_index=False)["VALIDATIONS"].sum()
    .sort_values("VALIDATIONS", ascending=False)
    .head(1)
)
peak_txt = "—"
if not peak_row.empty:
    peak_txt = (
        f'{peak_row.iloc[0]["date_hour"]:%Y-%m-%d %H:00} '
        f'({int(peak_row.iloc[0]["VALIDATIONS"]):,})'
    )

# =========================
# MAIN LAYOUT
# =========================
left, right = st.columns([2.25, 1.0], gap="large")

# =========================
# MAP AGGREGATION
# - Validations from FILTERED f
# - Stop membership from full-month df (stops_belong_set)
# - Fixed circle size; dynamic colors based on min/max of current map set
# =========================

# 1) Aggregate validations per stop (filtered dataset)
agg_stops = (
    f.groupby("stop_norm", as_index=False)["VALIDATIONS"]
    .sum()
    .rename(columns={"VALIDATIONS": "Validations"})
)

# 2) Join to stops shapefile (keep all stops in shapefile, then filter by membership)
gdf_stops_agg = gdf_stops.merge(agg_stops, on="stop_norm", how="left")
gdf_stops_agg["Validations"] = gdf_stops_agg["Validations"].fillna(0)

# 3) Apply membership filter: show only stops that belong to selected line(s) (full-month basis)
#    stops_belong_set is computed earlier from df (NOT f) so stops with Validations=0 still appear
gdf_stops_map = gdf_stops_agg[gdf_stops_agg["stop_norm"].isin(stops_belong_set)].copy()

# 4) Dynamic color categories based on current filtered results (min/max over gdf_stops_map)
gdf_stops_map, color_edges = add_dynamic_color_bins(
    gdf_stops_map,
    value_col="Validations",
    n_bins=5,
    include_zeros=True,   # keep zeros in lowest class (red)
)

# Subtle, stable size per color class (pixels)
# low -> high : small -> slightly bigger
RADIUS_BY_CLASS = [5, 6, 7, 8, 9]  # for 5 bins

# if you ever switch to 4 bins, use [5, 6, 7, 8]
gdf_stops_map["radius_px"] = gdf_stops_map["bin_idx"].map(
    lambda i: RADIUS_BY_CLASS[int(i)] if int(i) < len(RADIUS_BY_CLASS) else RADIUS_BY_CLASS[-1]
)


# ---- Dynamic legend in the sidebar (based on current filters) ----
st.sidebar.markdown("### Map color legend (dynamic)")

labels = []
for i in range(len(color_edges) - 1):
    a, b = color_edges[i], color_edges[i + 1]
    labels.append(f"{a:,.0f} – {b:,.0f}")

ramp = COLOR_RAMP_5[: len(labels)]
for col, lab in zip(ramp, labels):
    st.sidebar.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
          <div style="width:14px;height:14px;border-radius:50%;
                      background:rgba({col[0]},{col[1]},{col[2]},{col[3]/255});
                      border:1px solid #111827;"></div>
          <div style="font-size:12px;color:#e5e7eb;">{lab}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# 5) Lines: show only selected lines if any are selected (optional)
if sel_lines:
    selected_line_ids = set(
        df.loc[df["line_route"].isin(sel_lines), "line_id_norm"].dropna().unique()
    )
    gdf_lines_show = gdf_lines[gdf_lines["line_id_norm"].isin(selected_line_ids)].copy()
    if gdf_lines_show.empty:
        gdf_lines_show = gdf_lines
else:
    gdf_lines_show = gdf_lines



# =========================
# LEFT: MAP + TOP STOPS
# =========================
with left:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">Network View</div>
            <div class="small-muted">
                When a line is selected, the map shows all stops that belong to the line (based on full-month Excel presence),
                while validations reflect the current filters and can be zero.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    line_layer = pdk.Layer(
        "GeoJsonLayer",
        data=gdf_lines_show.__geo_interface__,
        stroked=True,
        filled=False,
        get_line_color=[80, 180, 255],
        get_line_width=6,
        line_width_min_pixels=2,
        pickable=False,
    )

    stop_layer = pdk.Layer(
    "ScatterplotLayer",
    data=gdf_stops_map,
    get_position=["lon", "lat"],
    get_radius="radius_px",
    radius_units="pixels",
    get_fill_color="fill_color",
    get_line_color=[15, 23, 42, 220],
    line_width_min_pixels=1,
    pickable=True,
)



    center_lat = float(gdf_stops_map["lat"].mean()) if not gdf_stops_map.empty else float(gdf_stops["lat"].mean())
    center_lon = float(gdf_stops_map["lon"].mean()) if not gdf_stops_map.empty else float(gdf_stops["lon"].mean())

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=0,
        bearing=0,
    )

    deck = pdk.Deck(
        layers=[line_layer, stop_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
        tooltip={"text": f"{{{STOPS_NAME_COL}}}\nValidations: {{Validations}}"},
    )

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.pydeck_chart(deck)
    st.markdown("</div>", unsafe_allow_html=True)

    # Top Stops (filtered)
    topN_left = 12
    top_stops = (
        f.groupby("STOP_DESCR", as_index=False)["VALIDATIONS"].sum()
        .sort_values("VALIDATIONS", ascending=False)
        .head(topN_left)
        .rename(columns={"STOP_DESCR": "Stop", "VALIDATIONS": "Validations"})
    )
    top_stops = to_categorical_for_color(top_stops, "Stop")

    fig_left = px.bar(
        top_stops,
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

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_left, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RIGHT: KPI + 2 CHARTS
# =========================
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
                    <div class="metric-label">Active Lines</div>
                    <div class="big-number">{active_lines:,}</div>
                </div>
                <div style="flex:1;">
                    <div class="metric-label">Total Validations</div>
                    <div class="big-number">{total_val/1000:,.1f}K</div>
                </div>
            </div>
            <div style="display:flex; gap:14px; margin-top:10px;">
                <div style="flex:1;">
                    <div class="metric-label">Active Days</div>
                    <div class="big-number" style="font-size:22px;">{active_days:,}</div>
                </div>
                <div style="flex:1;">
                    <div class="metric-label">Mean validations/hour</div>
                    <div class="big-number" style="font-size:22px;">{mean_val_per_hour:,.1f}</div>
                </div>
            </div>
            <div class="small-muted" style="margin-top:10px;">Peak hour: {peak_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Trend (hourly sum)
    f_ts = to_categorical_for_color(f, colorby_ts_col)
    ts = (
        f_ts.groupby(["date_hour", colorby_ts_col], as_index=False)["VALIDATIONS"]
        .sum()
        .rename(columns={"VALIDATIONS": "Validations"})
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

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_ts, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# BOTTOM ROW: AVG BY HOUR + HEATMAP
# =========================
st.markdown(
    '<div class="card"><div class="card-title">Additional Analytics</div></div>',
    unsafe_allow_html=True,
)

b1, b2 = st.columns([1, 1], gap="large")

with b1:
    fh = to_categorical_for_color(f, colorby_hourly_col)
    hp = (
        fh.groupby(["hour", colorby_hourly_col], as_index=False)["VALIDATIONS"]
        .mean()
        .rename(columns={"VALIDATIONS": "Mean validations"})
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

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_hp, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    hm = (
        f.groupby(["date", "hour"], as_index=False)["VALIDATIONS"].sum()
        .pivot(index="date", columns="hour", values="VALIDATIONS")
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

    st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
    st.plotly_chart(fig_hm, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Heatmap: each cell is the **sum of validations** for a given **day (row)** and **hour (column)**, "
        "after applying filters."
    )

# =========================
# DATA QUALITY: MISSING DAYS
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
