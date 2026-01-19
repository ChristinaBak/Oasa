# -*- coding: utf-8 -*-
"""
Created on Tue Jan 13 10:45:43 2026

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
import re

# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

LINES_SHP = DATA_DIR / "PT_Lines_Urban_FixedRoute.shp"
STOPS_SHP = DATA_DIR / "PT_Stops_2100.shp"

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="OASA Metro Insight Hub", layout="wide")

MONTH_FILES = {
    "Ιανουάριος 2024": "oasa_ridership_01_2024.csv",
    "Φεβρουάριος 2024": "oasa_ridership_02_2024.csv",
    "Μάρτιος 2024": "oasa_ridership_03_2024.csv",
    "Απρίλιος 2024": "oasa_ridership_04_2024.csv",
    "Μάιος 2024": "oasa_ridership_05_2024.csv",
    "Ιούνιος 2024": "oasa_ridership_06_2024.csv",
    "Ιούλιος 2024": "oasa_ridership_07_2024.csv",
    "Αύγουστος 2024": "oasa_ridership_08_2024.csv",
    "Σεπτέμβριος 2024": "oasa_ridership_09_2024.csv",
    "Οκτώβριος 2024": "oasa_ridership_10_2024.csv",
    "Νοέμβριος 2024": "oasa_ridership_11_2024.csv",
    "Δεκέμβριος 2024": "oasa_ridership_12_2024.csv",
}

# Link-flow periods (ONLY for link-flow network view)
PERIODS_2024 = {
    "January":   ("2024-01-01", "2024-01-31"),
    "Easter":    ("2024-04-26", "2024-05-06"),
    "Summer":    ("2024-07-01", "2024-08-31"),
    "October":   ("2024-10-01", "2024-10-31"),
    "Christmas": ("2024-12-20", "2024-12-31"),
}

LINKFLOW_FILES = {
    "January":   "LINK_FLOWS_typical_01.xlsx",
    "Easter":    "LINK_FLOWS_EASTER.xlsx",
    "Summer":    "LINK_FLOWS_SUMMER.xlsx",
    "October":   "LINK_FLOWS_typical_10.xlsx",
    "Christmas": "LINK_FLOWS_XMAS.xlsx",
}

LINKFLOW_ALLOWED_WINDOW = {
    "January":   ("2024-01-08", "2024-01-15"),
    "Easter":    ("2024-04-29", "2024-05-13"),
    "Summer":    ("2024-07-15", "2024-07-21"),
    "October":   ("2024-10-07", "2024-10-13"),
    "Christmas": ("2024-12-23", "2024-12-31"),
}

LINK_OFFSET_METERS = 45  # π.χ. 15–40m, δοκίμασε 25m για αρχή


AGENCY_LABELS = {
    "2": "2 - Metro",
    "3": "3 - Προαστιακός",
    "4": "4 - Tram",
}

def format_agency_option(code: str) -> str:
    return AGENCY_LABELS.get(str(code), str(code))

STATION_NAME_COL = "stop_descr"

STATION_NAME_MAP = {
    "ΑΓΙΟΣ ΕΛΕΥΘΕΡΙΟ": "ΑΓΙΟΣ ΕΛΕΥΘΕΡΙΟΣ",
    "ΣΥΓΓΡΟΥ-ΦΙΞ": "ΣΥΓΓΡΟΥ ΦΙΞ",
    "ΚΑΤ": "KΑT",
    "ΚΑΤΕΧΑΚΗ": "KΑTΕΧΑKΗ",
    "ΚΑΤΩ ΠΑΤΗΣΙΑ": "KΑTΩ ΠΑTΗΣΙΑ",
    "ΚΑΛΛΙΘΕΑ": "KΑΛΛΙΘΕΑ",
    "ΚΕΡΑΜΕΙΚΟΣ": "KΕΡΑΜΕΙKOΣ",
    "ΚΗΦΙΣΙΑ": "KΗΦΙΣΙΑ",
    "ΚΟΡΩΠΙ": "KΟΡΩΠΙ",
    "ΤΑΥΡΟΣ": "TΑΥΡΟΣ",
    "ΑΓΙΑ ΠΑΡΑΣΚΕΥΗ": "ΑΓΙΑ ΠΑΡΑΣKΕΥΗ",
    "ΑΓΙΟΣ ΑΝΤΩΝΙΟΣ": "ΑΓΙΟΣ ΑΝTΩΝΙΟΣ",
    "ΑΓΙΟΣ ΔΗΜΗΤΡΙΟΣ": "ΑΓΙΟΣ ΔΗΜΗTΡΙΟΣ",
    "ΑΓΙΟΣ ΝΙΚΟΛΑΟΣ": "ΑΓΙΟΣ ΝΙKOΛΑΟΣ",
    "ΑΚΡΟΠΟΛΗ": "ΑKΡOΠΟΛΗ",
    "ΑΜΠΕΛΟΚΗΠΟΙ": "ΑΜΠΕΛOKΗΠΟΙ",
    "ΑΝΩ ΠΑΤΗΣΙΑ": "ΑΝΩ ΠΑTΗΣΙΑ",
    "ΒΙΚΤΩΡΙΑ": "ΒΙKTΩΡΙΑ",
    "ΕΘΝΙΚΗ ΑΜΥΝΑ": "ΕΘΝΙKΗ ΑΜΥΝΑ",
    "ΕΛΛΗΝΙΚΟ": "ΕΛΛΗΝΙKO",
    "ΗΡΑΚΛΕΙΟ": "ΗΡΑKΛΕΙΟ",
    "ΜΕΤΑΞΟΥΡΓΕΙΟ": "ΜΕTΑΞΟΥΡΓΕΙΟ",
    "ΜΕΓΑΡΟ ΜΟΥΣΙΚΗΣ": "ΜΕΓΑΡΟ ΜΟΥΣΙKΗΣ",
    "ΜΟΝΑΣΤΗΡΑΚΙ": "ΜΟΝΑΣTΗΡΑKΙ",
    "ΜΟΣΧΑΤΟ": "ΜΟΣΧΑTΟ",
    "ΝΕΟΣ ΚΟΣΜΟΣ": "ΝΕΟΣ KOΣΜΟΣ",
    "ΝΕΡΑΝΤΖΙΩΤΙΣΣΑ": "ΝΕΡΑTΖΙΩTΙΣΣΑ",
    "ΝΟΜΙΣΜΑΤΟΚΟΠΕΙΟ": "ΝΟΜΙΣΜΑTΟKΟΠΕΙΟ",
    "ΟΜΟΝΟΙΑ": "ΟΜOΝΟΙΑ",
    "ΠΑΙΑΝΙΑ-ΚΑΝΤΖΑ": "ΠΑΙΑΝΙΑ - KΑΝTΖΑ",
    "ΠΑΝΟΡΜΟΥ": "ΠΑΝOΡΜΟΥ",
    "ΠΑΝΕΠΙΣΤΗΜΙΟ": "ΠΑΝΕΠΙΣTΗΜΙΟ",
    "ΠΕΤΡΑΛΩΝΑ": "ΠΕTΡΑΛΩΝΑ",
    "ΠΕΡΙΣΣΟΣ": "ΠΕΡΙΣΣOΣ",
    "ΠΕΡΙΣΤΕΡΙ": "ΠΕΡΙΣTΕΡΙ",
    "ΠΕΥΚΑΚΙΑ": "ΠΕΥKΑKΙΑ",
    "ΣΤ.ΛΑΡΙΣΗΣ": "ΣTΑΘΜOΣ ΛΑΡΙΣΗΣ",
    "ΣΕΠΟΛΙΑ": "ΣΕΠOΛΙΑ",
    "ΣΥΝΤΑΓΜΑ": "ΣΥΝTΑΓΜΑ",
    "ΧΟΛΑΡΓΟΣ": "ΧΟΛΑΡΓOΣ",
    "ΔΟΥΚ.ΠΛΑΚΕΝΤΙΑΣ": "ΔΟΥKΙΣΣΗΣ ΠΛΑKΕΝTΙΑΣ",
    "ΕΥΑΓΓΕΛΙΣΜΟΣ": "ΕΥΑΓΓΕΛΙΣΜOΣ"
}

PALETTE6 = ["#3b82f6", "#ef4444", "#f59e0b", "#22c55e", "#a855f7", "#06b6d4"]

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

def normalize_station_name(s: pd.Series) -> pd.Series:
    s_norm = s.astype(str).str.strip().str.upper()
    s_norm = s_norm.replace(STATION_NAME_MAP)
    return s_norm

@st.cache_data(show_spinner=False)
def load_data(path: Union[str, Path]) -> pd.DataFrame:
    path = Path(path)

    # Robust CSV read (tries to infer; if fails, tries common separators)
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.astype(str).str.strip().str.replace("\ufeff", "", regex=False)

    if "date_hour" not in df.columns:
        for sep in [";", ",", "\t", "|"]:
            try:
                d2 = pd.read_csv(path, sep=sep, engine="python", encoding="utf-8-sig")
                d2.columns = d2.columns.astype(str).str.strip().str.replace("\ufeff", "", regex=False)
                if "date_hour" in d2.columns:
                    df = d2
                    break
            except Exception:
                pass

    if "date_hour" not in df.columns:
        st.error(f"CSV χωρίς 'date_hour'. Columns: {list(df.columns)} | File: {path}")
        return pd.DataFrame()

    df["date_hour"] = pd.to_datetime(
        df["date_hour"].astype(str).str.strip(),
        dayfirst=True,
        errors="coerce",
    )
    df = df.dropna(subset=["date_hour"]).copy()

    if "dv_validations" not in df.columns:
        st.error(f"CSV χωρίς 'dv_validations'. Columns: {list(df.columns)} | File: {path}")
        return pd.DataFrame()

    df["dv_validations"] = pd.to_numeric(df["dv_validations"], errors="coerce").fillna(0)

    if "dv_platenum_station" in df.columns:
        df["dv_platenum_station"] = df["dv_platenum_station"].astype(str).str.strip()
    if "dv_agency" in df.columns:
        df["dv_agency"] = df["dv_agency"].astype(str).str.strip()

    # Filter buses (dv_agency == 1)
    if "dv_agency" in df.columns:
        df = df[pd.to_numeric(df["dv_agency"], errors="coerce") != 1]

    # Attiki duplicate fix
    if "dv_platenum_station" in df.columns:
        st_clean = df["dv_platenum_station"].astype(str).str.strip()
        mask_attiki = st_clean.isin(["ΑTTΙKΗ", "ΑΤΤΙΚΗ"])
        df.loc[mask_attiki, "dv_validations"] = df.loc[mask_attiki, "dv_validations"] / 2.0
        df.loc[mask_attiki, "dv_platenum_station"] = "ΑΤΤΙΚΗ"

    df["date"] = df["date_hour"].dt.date
    df["hour"] = df["date_hour"].dt.hour
    df["dow"] = df["date_hour"].dt.day_name()
    df["is_weekend"] = df["date_hour"].dt.weekday >= 5

    return df

@st.cache_data(show_spinner=False)
def load_network_geodata():
    gdf_lines = gpd.read_file(LINES_SHP)
    if gdf_lines.crs is not None and gdf_lines.crs.to_epsg() != 4326:
        gdf_lines = gdf_lines.to_crs("EPSG:4326")

    gdf_stops = gpd.read_file(STOPS_SHP)
    if gdf_stops.crs is not None and gdf_stops.crs.to_epsg() != 4326:
        gdf_stops = gdf_stops.to_crs("EPSG:4326")

    gdf_stops["lon"] = gdf_stops.geometry.x
    gdf_stops["lat"] = gdf_stops.geometry.y
    return gdf_lines, gdf_stops

# -------------------------
# LINK FLOW HELPERS
# -------------------------
def strip_line_suffix(name: str) -> str:
    if name is None:
        return ""
    return re.sub(r"_L\d+$", "", str(name).strip(), flags=re.IGNORECASE)

@st.cache_data(show_spinner=False)
def load_link_flows_excel(path: Union[str, Path]) -> pd.DataFrame:
    """
    Excel structure:
      sheets: L1, L2, L3, L4
      columns: from, to, flow_forward, flow_reverse (plus line optional)
    Returns directed links with Flow.
    """
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["from_stop", "to_stop", "Flow"])

    xls = pd.ExcelFile(path)
    frames = []
    for sh in xls.sheet_names:
        d = pd.read_excel(xls, sheet_name=sh)
        d.columns = d.columns.astype(str).str.strip()

        needed = {"from", "to", "flow_forward", "flow_reverse"}
        if not needed.issubset(set(d.columns)):
            continue

        fwd = d[["from", "to", "flow_forward"]].copy()
        fwd = fwd.rename(columns={"from": "from_stop", "to": "to_stop", "flow_forward": "Flow"})
        fwd["direction"] = "forward"
        fwd["offset_sign"] = 1
        fwd["sheet"] = sh

        rev = d[["from", "to", "flow_reverse"]].copy()
        rev = rev.rename(columns={"from": "to_stop", "to": "from_stop", "flow_reverse": "Flow"})
        rev["direction"] = "reverse"
        rev["offset_sign"] = -1  
        rev["sheet"] = sh

        out = pd.concat([fwd, rev], ignore_index=True)
        out["Flow"] = pd.to_numeric(out["Flow"], errors="coerce").fillna(0)

        out["from_stop"] = out["from_stop"].map(strip_line_suffix)
        out["to_stop"] = out["to_stop"].map(strip_line_suffix)

        frames.append(out)

    if not frames:
        return pd.DataFrame(columns=["from_stop", "to_stop", "Flow"])

    return pd.concat(frames, ignore_index=True)

import math

def build_links_with_geometry(lf: pd.DataFrame, gdf_stops: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Builds offset path geometry for PyDeck PathLayer so forward/reverse don’t overlap.
    Uses a canonical (undirected) orientation based on station name ordering.
    Expects lf columns at least: from_stop, to_stop, LinkFlow
    """
    if lf.empty:
        return pd.DataFrame(columns=["from_stop", "to_stop", "LinkFlow", "path"])

    stops_xy = gdf_stops.copy()
    stops_xy["name_norm"] = normalize_station_name(stops_xy[STATION_NAME_COL])
    stops_xy = stops_xy[["name_norm", "lon", "lat"]].drop_duplicates("name_norm")

    tmp = lf.copy()
    tmp["from_norm"] = normalize_station_name(tmp["from_stop"])
    tmp["to_norm"] = normalize_station_name(tmp["to_stop"])

    tmp = tmp.merge(
        stops_xy.rename(columns={"name_norm": "from_norm", "lon": "from_lon", "lat": "from_lat"}),
        on="from_norm",
        how="left",
    ).merge(
        stops_xy.rename(columns={"name_norm": "to_norm", "lon": "to_lon", "lat": "to_lat"}),
        on="to_norm",
        how="left",
    )

    tmp = tmp.dropna(subset=["from_lon", "from_lat", "to_lon", "to_lat"]).copy()

    def _compute_offset_ddeg(lonA, latA, lonB, latB, offset_m, sign):
        """
        Compute (dlon,dlat) degrees to offset a segment by offset_m meters.
        Segment direction is canonical A->B; sign chooses side (+/-).
        """
        lat0 = (latA + latB) / 2.0
        cos_lat = math.cos(math.radians(lat0))
        if cos_lat < 1e-8:
            cos_lat = 1e-8

        # degrees -> meters (approx)
        xA = lonA * 111320.0 * cos_lat
        yA = latA * 111320.0
        xB = lonB * 111320.0 * cos_lat
        yB = latB * 111320.0

        dx = xB - xA
        dy = yB - yA
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return 0.0, 0.0

        # perpendicular unit vector
        px = -dy / L
        py = dx / L

        ox = px * offset_m * float(sign)
        oy = py * offset_m * float(sign)

        dlon = ox / (111320.0 * cos_lat)
        dlat = oy / 111320.0
        return dlon, dlat

    def _make_offset_path(r):
        # canonical orientation by name order (stable for both directions)
        # if from_norm <= to_norm => treat (from->to) as canonical and offset +1
        # else canonical is (to->from) and this row is reverse => offset -1
        if str(r["from_norm"]) <= str(r["to_norm"]):
            lonA, latA, lonB, latB = r["from_lon"], r["from_lat"], r["to_lon"], r["to_lat"]
            sign = +1
        else:
            lonA, latA, lonB, latB = r["to_lon"], r["to_lat"], r["from_lon"], r["from_lat"]
            sign = -1

        dlon, dlat = _compute_offset_ddeg(lonA, latA, lonB, latB, LINK_OFFSET_METERS, sign)

        # apply the SAME offset to both endpoints of the original directed edge
        return [[r["from_lon"] + dlon, r["from_lat"] + dlat],
                [r["to_lon"] + dlon,   r["to_lat"] + dlat]]

    tmp["path"] = tmp.apply(_make_offset_path, axis=1)

# NEW: for LineLayer (more reliable width variation)
    tmp["source_position"] = tmp["path"].apply(lambda p: p[0])
    tmp["target_position"] = tmp["path"].apply(lambda p: p[1])

    return tmp

# =========================
# SIDEBAR FILTERS (VALIDATIONS - unchanged)
# =========================
st.sidebar.header("Filters (Validations)")

month_label = st.sidebar.selectbox(
    "Μήνας (2024)",
    list(MONTH_FILES.keys()),
    index=0,
)
FILE_PATH = BASE_DIR / MONTH_FILES[month_label]

df = load_data(FILE_PATH)
if df.empty:
    st.error("Δεν φορτώθηκαν δεδομένα ridership. Έλεγξε το CSV path/format.")
    st.stop()

min_dt = df["date_hour"].min()
max_dt = df["date_hour"].max()

stops = sorted(df["dv_platenum_station"].dropna().unique()) if "dv_platenum_station" in df.columns else []
agencies = sorted(df["dv_agency"].dropna().unique()) if "dv_agency" in df.columns else []

sel_stops = st.sidebar.multiselect("Stop", stops, default=[])
agency_options = [format_agency_option(a) for a in agencies]
sel_agency_labels = st.sidebar.multiselect("Agency", agency_options, default=[])

label_to_code = {format_agency_option(a): str(a) for a in agencies}
sel_agencies_codes = [label_to_code[l] for l in sel_agency_labels]

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
    st.sidebar.warning("Both 'Only weekend' and 'Only weekdays' selected. No day-type filter will be applied.")


# =========================
# LINK FLOWS FILTERS (separate) - per-period default date ranges
# =========================
st.sidebar.divider()
st.sidebar.subheader("Link flows")

lf_period = st.sidebar.selectbox(
    "Link flow period (2024)",
    options=list(PERIODS_2024.keys()),
    index=0,
    key="lf_period",
)

# Fixed window (only these dates exist for the user)
w0, w1 = LINKFLOW_ALLOWED_WINDOW[lf_period]
lf_window_start = pd.to_datetime(w0).date()
lf_window_end   = pd.to_datetime(w1).date()

# Build the allowed days list (ONLY these are shown)
lf_allowed_days = list(pd.date_range(lf_window_start, lf_window_end, freq="D").date)

# Reset selected days when period changes
if st.session_state.get("lf_period_prev") != lf_period:
    st.session_state["lf_selected_days"] = lf_allowed_days[:]  # default = all days
    st.session_state["lf_period_prev"] = lf_period

# Users select day(s) ONLY from the allowed list
lf_selected_days = st.sidebar.multiselect(
    "Select day(s) within the period window",
    options=lf_allowed_days,
    default=st.session_state.get("lf_selected_days", lf_allowed_days),
    key="lf_selected_days",
)

# Guard
if not lf_selected_days:
    st.sidebar.warning("Select at least one day to display link flows.")
    st.stop()

# Convenience values for downstream
lf_selected_days_count = len(lf_selected_days)
lf_window_days_total   = len(lf_allowed_days)

# =========================
# CHART COLOR CONTROLS (unchanged)
# =========================
st.sidebar.divider()
st.sidebar.subheader("Chart colors")

COLOR_CHOICES_COMMON = {
    "Stop": "dv_platenum_station",
    "Hour": "hour",
    "Day of week": "dow",
}

colorby_ts_label = st.sidebar.selectbox(
    "Trend line: color by",
    options=["Stop", "Hour", "Day of week"],
    index=1,
)
colorby_ts_col = COLOR_CHOICES_COMMON[colorby_ts_label]

colorby_top5_label = st.sidebar.selectbox(
    "Top 5 bars: color by",
    options=["Stop", "Hour", "Day of week"],
    index=0,
)
colorby_top5_col = COLOR_CHOICES_COMMON[colorby_top5_label]

colorby_hourly_label = st.sidebar.selectbox(
    "Avg by hour: color by",
    options=["Stop", "Day of week"],
    index=0,
)
colorby_hourly_col = {
    "Stop": "dv_platenum_station",
    "Day of week": "dow",
}[colorby_hourly_label]

# =========================
# APPLY FILTERS (VALIDATIONS - unchanged logic)
# =========================
f = df.copy()

if sel_stops and "dv_platenum_station" in f.columns:
    f = f[f["dv_platenum_station"].isin(sel_stops)]
if sel_agencies_codes and "dv_agency" in f.columns:
    f = f[f["dv_agency"].isin(sel_agencies_codes)]

start_date, end_date = date_range
f = f[(f["date_hour"].dt.date >= start_date) & (f["date_hour"].dt.date <= end_date)]
f = f[(f["hour"] >= hour_range[0]) & (f["hour"] <= hour_range[1])]

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
    Data coverage (month file): {min_dt:%Y-%m-%d %H:00} to {max_dt:%Y-%m-%d %H:00}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# KPIs (VALIDATIONS - unchanged)
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
    peak_txt = (
        f'{peak_row.iloc[0]["date_hour"]:%Y-%m-%d %H:00} '
        f'({int(peak_row.iloc[0]["dv_validations"]):,})'
    )

# =========================
# MAIN LAYOUT
# =========================
left, right = st.columns([2.25, 1.0], gap="large")

gdf_lines, gdf_stops = load_network_geodata()

# =========================
# VALIDATIONS: aggregate validations per stop for circle sizes (unchanged)
# =========================
agg = (
    f.groupby("dv_platenum_station", as_index=False)["dv_validations"]
    .sum()
    .rename(columns={"dv_validations": "Validations"})
)

agg["name_norm"] = agg["dv_platenum_station"].astype(str).str.strip().str.upper()
gdf_stops["name_norm"] = normalize_station_name(gdf_stops[STATION_NAME_COL])

gdf_stops_agg = gdf_stops.merge(
    agg[["name_norm", "Validations"]],
    on="name_norm",
    how="left",
)
gdf_stops_agg["Validations"] = gdf_stops_agg["Validations"].fillna(0)

max_val2 = gdf_stops_agg["Validations"].max()
if max_val2 > 0:
    gdf_stops_agg["radius"] = 80 + 420 * gdf_stops_agg["Validations"] / max_val2
else:
    gdf_stops_agg["radius"] = 80

# =========================
# LINK FLOWS: load and scale (independent)
# =========================
lf_fp = DATA_DIR / LINKFLOW_FILES[lf_period]
lf_raw = load_link_flows_excel(lf_fp)

lf_agg = (
    lf_raw.groupby(["from_stop", "to_stop", "offset_sign"], as_index=False)["Flow"]
    .sum()
    .rename(columns={"Flow": "LinkFlow_period_total"})
)


# Always scale window totals by selected days (uniform assumption)
if not lf_agg.empty:
    scale = lf_selected_days_count / float(lf_window_days_total) if lf_window_days_total > 0 else 0.0
    lf_agg["LinkFlow"] = (lf_agg["LinkFlow_period_total"] * scale).round().astype(int)
else:
    lf_agg["LinkFlow"] = 0.0


links_df = build_links_with_geometry(lf_agg[["from_stop", "to_stop", "LinkFlow", "offset_sign"]], gdf_stops)


# =========================
# PYDECK LAYERS
# =========================
line_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_lines.__geo_interface__,
    stroked=True,
    filled=False,
    get_line_color=[80, 180, 255],
    get_line_width=8,
    line_width_min_pixels=3,
    pickable=False,
)

stop_layer_validations = pdk.Layer(
    "ScatterplotLayer",
    data=gdf_stops_agg,
    get_position=["lon", "lat"],
    get_radius="radius",
    radius_min_pixels=2,
    radius_max_pixels=40,
    get_fill_color=[255, 140, 0, 160],
    pickable=True,
)

stop_layer_flow = pdk.Layer(
    "ScatterplotLayer",
    data=gdf_stops,                 # <-- όχι gdf_stops_flow
    get_position=["lon", "lat"],
    get_radius=70,                  # σταθερό μέγεθος (ρύθμισέ το)
    radius_units="pixels",          # σταθερό σε pixels
    radius_min_pixels=5,
    radius_max_pixels=5,
    get_fill_color=[255, 140, 0, 180],  # ουδέτερο γκρι
    pickable=False,
)


import pandas as pd

link_layer_fwd = None
link_layer_rev = None

if not links_df.empty:

    # --- GUARANTEED visible differentiation: 6 classes of thickness (pixels) ---
    if links_df["LinkFlow"].nunique() <= 1:
        links_df["width_px"] = 8.0
    else:
        widths = [1, 2, 3, 5, 7, 10] # px
        q = pd.qcut(links_df["LinkFlow"], q=6, labels=False, duplicates="drop")
        widths_use = widths[: int(q.max()) + 1]
        links_df["width_px"] = q.map(lambda i: float(widths_use[int(i)]))

    # split by offset_sign (1 = one side, -1 = other side)
    fwd_df = links_df[links_df["offset_sign"] == 1].copy()
    rev_df = links_df[links_df["offset_sign"] == -1].copy()

    if not fwd_df.empty:
        link_layer_fwd = pdk.Layer(
            "PathLayer",
            data=fwd_df,
            get_path="path",
            get_width="width_px",
            width_units="pixels",     # <-- CRITICAL
            width_scale=1,
            width_min_pixels=1,
            width_max_pixels=10,
            pickable=True,
            get_color=[34, 197, 94, 200],   # green
        )

    if not rev_df.empty:
        link_layer_rev = pdk.Layer(
            "PathLayer",
            data=rev_df,
            get_path="path",
            get_width="width_px",
            width_units="pixels",     # <-- CRITICAL
            width_scale=1,
            width_min_pixels=1,
            width_max_pixels=10,
            pickable=True,
            get_color=[255, 140, 0, 200],   # orange
        )


center_lat = float(gdf_stops["lat"].mean())
center_lon = float(gdf_stops["lon"].mean())
view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11, pitch=0, bearing=0)

# =========================
# LEFT: NETWORK VIEW (two tabs, separate dropdowns)
# =========================
with left:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">Network View</div>
            <div class="small-muted">
                Spatial view of the Metro / ISAP network.<br>
                Tab 1: Validations (month-based). Circle size encodes total validations
                for the current filters.<br>
                Tab 2: Link flows (period-based, uses separate link-flow controls).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["Validations (Month-based)", "Link flows (Period-based)"])

    with tab1:
        deck_valid = pdk.Deck(
            layers=[line_layer, stop_layer_validations],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/dark-v11",
            tooltip={"text": f"{{{STATION_NAME_COL}}}\nValidations: {{Validations}}"},
        )
        st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
        st.pydeck_chart(deck_valid)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
       no_links = (link_layer_fwd is None) and (link_layer_rev is None)

       if no_links:
        st.markdown(
            """
            <div class="card">
                <div class="card-title">No link flows to display</div>
                <div class="small-muted">
                    Το link-flow Excel δεν βρέθηκε ή δεν έγινε match στα ονόματα σταθμών.
                    Έλεγξε ότι τα Excel είναι στο /data και ότι τα stop names ταιριάζουν (με αφαίρεση _Lx).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
          )
       else:
           layers_links = [line_layer]
           if link_layer_fwd is not None:
              layers_links.append(link_layer_fwd)
           if link_layer_rev is not None:
              layers_links.append(link_layer_rev)
           layers_links.append(stop_layer_flow)

           deck_links = pdk.Deck(
              layers=layers_links,
              initial_view_state=view_state,
              map_style="mapbox://styles/mapbox/dark-v11",
              tooltip={"text": "Link: {from_stop} → {to_stop}\nFlow: {LinkFlow}\nWidth(px): {width_px}"}
           )

           st.markdown('<div class="card plot-card">', unsafe_allow_html=True)
           st.pydeck_chart(deck_links)
           st.markdown("</div>", unsafe_allow_html=True)

           st.caption("Forward links: green | Reverse links: orange | Thickness ∝ link flow")


    # (unchanged) Top 12 stops
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

# =========================
# RIGHT: KPI + 2 charts stacked (unchanged)
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

    # Trend (hourly sum)
    f_ts = to_categorical_for_color(f, colorby_ts_col)
    ts = (
        f_ts.groupby(["date_hour", colorby_ts_col], as_index=False)["dv_validations"]
        .sum()
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

    # Top 5 bars
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
# BOTTOM ROW: Avg by hour + Heatmap (unchanged)
# =========================
st.markdown(
    '<div class="card"><div class="card-title">Additional Analytics</div></div>',
    unsafe_allow_html=True,
)

b1, b2 = st.columns([1, 1], gap="large")

with b1:
    fh = to_categorical_for_color(f, colorby_hourly_col)
    hp = (
        fh.groupby(["hour", colorby_hourly_col], as_index=False)["dv_validations"]
        .mean()
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
# EXPORT + DATA QUALITY (unchanged from your original end section)
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
