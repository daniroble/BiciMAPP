from pathlib import Path
import re, unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk


st.set_page_config(page_title="BiciMAPP | Madrid en bicicleta", page_icon="🚲", layout="wide")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOGO_PATH = HERE / "assets" / "ccd3ccb6-3485-4aab-977e-a5e4d0136b6d.png"
DATA = ROOT / "data" / "processed"
ANALYSIS = ROOT / "analysis"
VALIDATED_COORDS = (
    DATA / "crtm_integration" / "validated_integration"
    / "bicimad_crtm_validated_599.csv"
)

PRIMARY_BLUE = "#2F6FDB"
BASE_BLUE = "#2F6FDB"
LIGHT_BLUE = "#8FB4F0"
MID_BLUE = "#5489E6"
SKY_BLUE = "#BCD2F4"
CSV_BLUE = "#0B1F3A"
PALETTE = [PRIMARY_BLUE, LIGHT_BLUE, MID_BLUE, SKY_BLUE, BASE_BLUE, "#4778C4", "#DBE8FF"]
PLOT_BG = "#FBFDFF"

def norm(x):
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", x).strip("_")

WEEKDAY_LABELS_ES = {
    "monday": "Lunes", "mon": "Lunes", "lunes": "Lunes",
    "tuesday": "Martes", "tue": "Martes", "tues": "Martes", "martes": "Martes",
    "wednesday": "Miércoles", "wed": "Miércoles", "miercoles": "Miércoles",
    "thursday": "Jueves", "thu": "Jueves", "thur": "Jueves", "thurs": "Jueves", "jueves": "Jueves",
    "friday": "Viernes", "fri": "Viernes", "viernes": "Viernes",
    "saturday": "Sábado", "sat": "Sábado", "sabado": "Sábado",
    "sunday": "Domingo", "sun": "Domingo", "domingo": "Domingo",
}

def weekday_in_spanish(value):
    return WEEKDAY_LABELS_ES.get(norm(value), value)

@st.cache_data(show_spinner=False)
def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        try:
            return pd.read_csv(path, sep=";", low_memory=False)
        except Exception:
            return pd.DataFrame()

def locate(names):
    target = {norm(n) for n in names}
    for root in (DATA, ANALYSIS):
        if root.exists():
            for p in root.rglob("*.csv"):
                if norm(p.stem) in target:
                    return p
    return None

def dataset(names):
    p = locate(names)
    return (read_csv(p), p) if p else (None, None)

def findcol(df, aliases):
    if df is None or df.empty:
        return None
    cols = {norm(c): c for c in df.columns}
    for a in aliases:
        if norm(a) in cols:
            return cols[norm(a)]
    # Conservative substring matching: prefer longest aliases, avoid vague matches
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        if len(na) >= 4:
            for c in df.columns:
                if na in norm(c):
                    return c
    return None

def to_num(df, col):
    if col:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def source(p):
    try:
        return f"Fuente local: `{p.relative_to(ROOT)}`"
    except Exception:
        return f"Fuente: `{p.name}`"

def style_plot(fig, height=390):
    fig.update_layout(
        height=height, paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
        font=dict(family="Inter, Arial, sans-serif", color=BASE_BLUE, size=13),
        margin=dict(l=24, r=20, t=58, b=40),
        colorway=PALETTE,
        hoverlabel=dict(bgcolor="#EAF1FC", font=dict(color="#173F83", size=12)),
        title=dict(font=dict(size=18, color=BASE_BLUE), x=0, xanchor="left"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            font=dict(color=BASE_BLUE, size=12),
        ),
        xaxis=dict(showgrid=False, linecolor="#D8E5F0", tickfont=dict(color=BASE_BLUE)),
        yaxis=dict(gridcolor="#E4EDF5", zerolinecolor="#CEDDE9", tickfont=dict(color=BASE_BLUE)),
    )
    return fig

st.markdown("""
<style>
:root {
  --primary-color:#2F6FDB;
  --bic-blue:#2F6FDB;
  --bic-base-blue:#2F6FDB;
  --bic-light-blue:#8FB4F0;
  --sidebar-bg:#285FC4;
  --title-bg:#2F6FDB;
  --app-bg:#F3F7FC;
  --surface:#FBFDFF;
  --text-muted:#607787;
  --border:#D8E5F0;
  --shadow:0 8px 24px rgba(32,112,247,.06);
}
.stApp {
  background:var(--app-bg);
  color:var(--bic-base-blue);
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
section.main > div.block-container {
  max-width:1480px;
  padding:2rem 2.5rem 3rem;
}
[data-testid="stSidebar"] {
  background:var(--sidebar-bg);
  background-image:none;
  border-right:1px solid rgba(23,63,131,.12);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
  color:#F4F7FF !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
  font-size:.78rem;
  font-weight:700;
  letter-spacing:.08em;
  text-transform:uppercase;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  padding:.55rem .7rem;
  border-radius:9px;
  transition:background .18s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
  display:none !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover,
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background:rgba(255,255,255,.14);
}
[data-testid="stSidebar"] hr {
  border-color:rgba(255,255,255,.2);
}
.st-key-executive-summary-logo [data-testid="stImage"] {
  display:flex;
  justify-content:center;
  align-items:center;
  min-height:100%;
}
h1,h2,h3,h4 { color:var(--bic-base-blue) !important; letter-spacing:-.025em; }
h2 { margin-top:1.5rem; }
.block-container { padding-top:1.6rem; padding-bottom:2.2rem; }
.bici-hero {
  position:relative;
  overflow:hidden;
  background:var(--title-bg);
  color:#FFFFFF;
  padding:2rem 2.2rem;
  border:1px solid rgba(255,255,255,.16);
  border-radius:20px;
  margin-bottom:1.5rem;
  box-shadow:0 12px 30px rgba(22,65,136,.16);
}
.bici-hero:after {
  content:"";
  position:absolute;
  width:280px;
  height:280px;
  right:-85px;
  top:-145px;
  border:1px solid rgba(255,255,255,.12);
  border-radius:50%;
  box-shadow:0 0 0 34px rgba(255,255,255,.035),0 0 0 68px rgba(255,255,255,.025);
  pointer-events:none;
}
.bici-hero h1 { color:#FFFFFF !important; margin:.35rem 0 0; font-size:2.2rem; line-height:1.15; }
.bici-hero p { color:#E8F0FF; margin:.65rem 0 0; font-size:1rem; max-width:760px; }
.bici-hero .bici-kicker { color:#DCE8FF; }
.bici-card {
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:15px;
  padding:1.15rem 1.25rem;
  box-shadow:0 3px 12px rgba(32,112,247,.035);
}
.bici-kicker { color:var(--bic-blue); font-weight:750; letter-spacing:.1em; text-transform:uppercase; font-size:.72rem; }
.bici-note {
  background:#EAF1FC;
  border:1px solid #D5E1F2;
  border-left:4px solid var(--bic-blue);
  padding:.9rem 1rem;
  border-radius:10px;
  color:#173F83;
}
[data-testid="stMetric"] {
  height:100%;
  background:var(--surface);
  border:1px solid var(--border);
  padding:1.05rem 1.15rem;
  border-radius:14px;
  box-shadow:var(--shadow);
  transition:transform .18s ease,box-shadow .18s ease;
}
[data-testid="stMetric"]:hover {
  transform:translateY(-2px);
  box-shadow:0 12px 28px rgba(32,112,247,.1);
}
[data-testid="stMetricLabel"] p {
  color:var(--text-muted) !important;
  font-size:.76rem;
  font-weight:700;
  letter-spacing:.045em;
  white-space:normal !important;
  overflow-wrap:anywhere;
  line-height:1.2;
}
[data-testid="stMetricValue"] {
  color:var(--bic-base-blue) !important;
  font-weight:750;
  letter-spacing:-.035em;
}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
  white-space:normal !important;
  overflow:visible !important;
  overflow-wrap:anywhere !important;
  line-height:1.15;
}
[data-testid="stPlotlyChart"] {
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:15px;
  padding:.35rem;
  box-shadow:0 3px 12px rgba(32,112,247,.035);
}
[data-testid="stDataFrame"] {
  border:1px solid var(--border);
  border-radius:12px;
  overflow:hidden;
}
[data-testid="stTabs"] [role="tablist"] { gap:.4rem; border-bottom:1px solid var(--border); }
[data-testid="stTabs"] [role="tab"],
[data-testid="stTabs"] [role="tab"]:hover,
[data-testid="stTabs"] [role="tab"]:focus,
[data-testid="stTabs"] [role="tab"]:active,
[data-testid="stTabs"] [role="tab"][aria-selected="true"],
[data-testid="stTabs"] [role="tab"] *,
[data-testid="stTabs"] [role="tab"]:hover *,
[data-testid="stTabs"] [role="tab"]:focus *,
[data-testid="stTabs"] [role="tab"]:active *,
[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {
  color:#173F83 !important;
}
[data-testid="stTabs"] [role="tab"] {
  font-weight:650;
  padding:.65rem .9rem;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  border-bottom-color:var(--bic-blue) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  background-color:var(--bic-blue) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  border-color:var(--border);
  border-radius:9px;
}
[data-testid="stAlert"] { border-radius:12px; }
@media (max-width:900px) {
  section.main > div.block-container { padding:1.5rem 1.25rem 2rem; }
  .bici-hero { padding:1.5rem; }
}
@media (max-width:600px) {
  section.main > div.block-container { padding:1rem .75rem 1.5rem; }
  .bici-hero { padding:1.25rem; border-radius:15px; }
  .bici-hero h1 { font-size:1.7rem; }
  [data-testid="stMetric"] { padding:.85rem; }
}
</style>
""", unsafe_allow_html=True)

MONTH = ["demand_monthly","monthly_demand","demanda_mensual"]
WEEK = ["demand_weekday","weekday_demand","demanda_dia_semana"]
HOUR = ["demand_hourly","hourly_demand","demanda_horaria"]
BAL = ["station_demand_balance","station_balance","balance_estaciones"]
TOPD = ["stations_top_departures","top_departures","estaciones_salidas"]
TOPA = ["stations_top_arrivals","top_arrivals","estaciones_llegadas"]
TOPI = ["stations_top_imbalance","top_imbalance","estaciones_desequilibrio"]
ODREC = ["od_recurrence_rank","od_recurrence_filtered","od_top_recurrence_audited","od_recurrence_audited"]
ODVOL = ["od_total_demand_rank","od_top_total_volume_audited"]
CORRE = ["final_corridor_evidence"]
CORRS = ["final_corridor_summary"]

def hero(title, subtitle, kicker="BiciMAPP · DATAMAD"):
    st.markdown(f'<div class="bici-hero"><div class="bici-kicker">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

CSV_COLUMN_LABELS = {
    "hour": "Hora",
    "weekday": "Día de la semana",
    "day": "Día",
    "month": "Mes",
    "year": "Año",
    "trips": "Viajes",
    "station": "Estación",
    "stations": "Estaciones",
    "route": "Ruta",
    "balance": "Balance",
    "date": "Fecha",
    "id": "ID",
    "year_month": "Mes",
    "weekday_num": "Día de la semana",
    "weekday_name": "Día de la semana",
    "hour_of_day": "Hora",
    "total_trips": "Viajes totales",
    "total_activity": "Actividad total",
    "departures": "Salidas",
    "arrivals": "Llegadas",
    "station_id": "ID de estación",
    "station_name": "Estación",
    "origin_id": "ID de origen",
    "origin_name": "Estación de origen",
    "destination_id": "ID de destino",
    "destination_name": "Estación de destino",
    "bicimad_station_id": "ID de estación BiciMAD",
    "bicimad_station_name": "Estación BiciMAD",
    "bicimad_lat": "Latitud BiciMAD",
    "bicimad_lon": "Longitud BiciMAD",
    "bicimad_state": "Estado BiciMAD",
    "bicimad_bases": "Bases BiciMAD",
    "crtm_station_name": "Estación CRTM",
    "crtm_system": "Sistema CRTM",
    "match_confidence": "Confianza de coincidencia",
    "event_date": "Fecha",
    "net_balance": "Balance neto",
    "absolute_imbalance": "Desequilibrio absoluto",
    "recurrence_pct": "Recurrencia (%)",
    "active_days": "Días activos",
    "eligible_days": "Días elegibles",
}

CSV_COLUMN_WORDS = {
    "active": "activos",
    "activity": "actividad",
    "arrival": "llegada",
    "arrivals": "llegadas",
    "average": "media",
    "avg": "media",
    "balance": "balance",
    "bases": "bases",
    "bicimad": "BiciMAD",
    "candidate": "candidato",
    "class": "clasificación",
    "confidence": "confianza",
    "count": "recuento",
    "crtm": "CRTM",
    "day": "día",
    "days": "días",
    "demand": "demanda",
    "departure": "salida",
    "departures": "salidas",
    "destination": "destino",
    "eligible": "elegible",
    "emitter": "emisor",
    "evidence": "evidencia",
    "flow": "flujo",
    "hour": "hora",
    "id": "ID",
    "imbalance": "desequilibrio",
    "latitude": "latitud",
    "lat": "latitud",
    "longitude": "longitud",
    "lon": "longitud",
    "match": "coincidencia",
    "mean": "media",
    "month": "mes",
    "name": "nombre",
    "net": "neto",
    "num": "n.º",
    "only": "solo",
    "origin": "origen",
    "partial": "parcial",
    "pct": "%",
    "percent": "porcentaje",
    "positive": "positivo",
    "negative": "negativo",
    "receiver": "receptor",
    "recurrence": "recurrencia",
    "route": "ruta",
    "routes": "rutas",
    "size": "tamaño",
    "source": "fuente",
    "station": "estación",
    "stations": "estaciones",
    "state": "estado",
    "strong": "fuerte",
    "system": "sistema",
    "total": "total",
    "trip": "viaje",
    "trips": "viajes",
    "type": "tipo",
    "weekday": "día",
    "week": "semana",
    "year": "año",
}

def clean_csv_column(column):
    name = str(column).strip()
    has_camel_case = re.search(r"(?<=[a-z0-9])(?=[A-Z])", name)
    if "_" not in name and not has_camel_case and not (
        name.isalnum() and name.islower()
    ):
        return name

    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    key = re.sub(r"[^\w]+", "_", normalized.casefold()).strip("_")
    if key in CSV_COLUMN_LABELS:
        return CSV_COLUMN_LABELS[key]

    words = [
        CSV_COLUMN_WORDS.get(word, word)
        for word in key.split("_")
    ]
    if words and words[0].casefold() not in {"id", "bicimad", "crtm"}:
        words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words)

def style_csv_dataframe(data, clean_columns=True):
    if clean_columns:
        data = data.rename(columns=clean_csv_column)
    return (
        data.style
        .set_properties(**{"background-color": CSV_BLUE, "color": "#F4F7FF"})
        .set_table_styles([{
            "selector": "th",
            "props": [("background-color", CSV_BLUE), ("color", "#FFFFFF")],
        }])
    )

def styled_dataframe(data, labels, formats, value_mappings=None):
    display_data = data.copy()
    for column, mapper in (value_mappings or {}).items():
        if column in display_data:
            display_data[column] = display_data[column].map(mapper)
    display_data = display_data.rename(columns=labels).reset_index(drop=True)
    return style_csv_dataframe(display_data, clean_columns=False).format(
        formats, na_rep="—"
    )

def missing(label, names):
    st.warning(f"No localizo el dataset de **{label}**. Busqué nombres: {', '.join(names)}")

nav = st.sidebar.radio("BiciMAPP", ["Resumen ejecutivo", "Demanda temporal", "Estaciones", "Mapa de movilidad", "Corredores", "Datos y metodología"])
st.sidebar.markdown("---")
st.sidebar.markdown("**DATAMAD 2026**")
st.sidebar.caption("Open data · Análisis reproducible")
st.sidebar.caption("Creado por Blanca Belinchón Andrades y Daniel Robledillo Manotas")

if nav == "Resumen ejecutivo":
    hero("Madrid en bicicleta", "Identificamos cuándo, dónde y entre qué estaciones se repiten los patrones de movilidad.", "BiciMAPP · Open data")
    m, pm = dataset(MONTH)
    hourly_data, hourly_path = dataset(HOUR)
    b, pb = dataset(BAL)
    month_col = findcol(
        m, ["month", "mes", "year_month", "fecha", "period"]
    ) if m is not None else None
    station_col = findcol(b, ["station","station_name","nombre_estacion","estacion"]) if b is not None else None
    trips_col = findcol(m, ["trips","viajes","total_trips","count","n_trips","demanda"]) if m is not None else None
    total = pd.to_numeric(m[trips_col], errors="coerce").sum() if trips_col else None
    n_stations = b[station_col].nunique() if station_col else None

    summary_kpis, summary_logo = st.columns(2, gap="large")
    with summary_kpis:
        primary_kpis, secondary_kpis = st.columns(2, gap="medium")
        with primary_kpis:
            st.metric(
                "Viajes agregados",
                f"{total:,.0f}" if total is not None else "—",
                help="Suma del dataset mensual disponible",
            )
            st.metric(
                "Franja de análisis",
                "Mañana · 07–09 h",
                help="Análisis de recurrencia de corredores",
            )
        with secondary_kpis:
            st.metric(
                "Estaciones en diagnóstico",
                f"{n_stations:,}" if n_stations is not None else "—",
                help="Estaciones presentes en el diagnóstico",
            )
            st.metric(
                "Corredor con evidencia",
                "Fernando → Orense 12",
                help="Corredor principal seleccionado por evidencia conjunta",
            )
    with summary_logo.container(key="executive-summary-logo"):
        st.image(LOGO_PATH, width="stretch")
    st.markdown("### El hallazgo")
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown('<div class="bici-card"><h3>Fernando el Católico → Orense 12</h3><p>Martes, miércoles y jueves a las 08:00. Se observan <b>166 viajes</b> en las tres combinaciones de día-hora seleccionadas.</p><p>La selección se basa en recurrencia y evidencia de balance en ambas estaciones, no en ser el corredor de mayor volumen.</p></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="bici-card"><h3>Qué aporta BiciMAPP</h3><ul><li>Patrones temporales de demanda</li><li>Estaciones con flujo persistentemente positivo o negativo</li><li>Rutas recurrentes e intensidad por separado</li><li>Transparencia sobre cobertura y límites</li></ul></div>', unsafe_allow_html=True)
    st.markdown("### Evolución de demanda")
    if m is not None and trips_col:
        x = month_col
        if x:
            m2=m.copy(); m2[trips_col]=pd.to_numeric(m2[trips_col],errors="coerce")
            fig=px.area(m2,x=x,y=trips_col,markers=True,color_discrete_sequence=[PRIMARY_BLUE],title="Viajes por mes · cobertura disponible")
            fig.update_traces(line=dict(width=3),fillcolor="rgba(22,123,165,.12)")
            st.plotly_chart(style_plot(fig,360),width='stretch')
            st.caption(source(pm))
    st.markdown("---")
    st.markdown("### 24h en BiciMAD")
    if hourly_data is None:
        missing("demanda horaria", HOUR)
    else:
        hour_col = findcol(hourly_data, ["hour", "hora", "hour_of_day"])
        hourly_trips_col = findcol(
            hourly_data,
            ["trips", "viajes", "total_trips", "count", "n_trips", "demanda"],
        )
        if hour_col and hourly_trips_col:
            hourly_chart = hourly_data.copy()
            hourly_chart[hour_col] = pd.to_numeric(
                hourly_chart[hour_col], errors="coerce"
            )
            hourly_chart[hourly_trips_col] = pd.to_numeric(
                hourly_chart[hourly_trips_col], errors="coerce"
            )
            hourly_chart = hourly_chart.dropna(
                subset=[hour_col, hourly_trips_col]
            ).sort_values(hour_col)
            if not hourly_chart.empty:
                fig = px.area(
                    hourly_chart,
                    x=hour_col,
                    y=hourly_trips_col,
                    markers=True,
                    color_discrete_sequence=[PRIMARY_BLUE],
                    title="Viajes por hora del día · cobertura disponible",
                )
                fig.update_traces(
                    line=dict(width=3), fillcolor="rgba(22,123,165,.12)"
                )
                fig.update_xaxes(
                    title_text="Hora del día",
                    range=[6, 23],
                    tickmode="array",
                    tickvals=list(range(24)),
                    ticktext=[f"{hour:02d}:00" for hour in range(24)],
                    tickangle=-45,
                    rangeslider=dict(visible=True, thickness=0.12),
                )
                fig.update_yaxes(title_text="Viajes")
                st.plotly_chart(
                    style_plot(fig, 420),
                    width="stretch",
                    config={"scrollZoom": True, "displaylogo": False},
                )
                st.caption(source(hourly_path))
            else:
                st.info("El dataset horario no contiene registros numéricos válidos.")
        else:
            st.warning("No reconozco las columnas de hora y viajes en el dataset horario.")
    st.markdown('<div class="bici-note"><b>El ocio sobre el trabajo:</b> Se observan picos de actividad en las horas punta de comienzo y fin de la jornada laboral, pero los valores máximos se alcanzan entre las 18:000 y 19:00.</div>', unsafe_allow_html=True)
    st.markdown('<div class="bici-note"><b>Interpretación responsable:</b> balance de flujo (llegadas − salidas) no es inventario de bicicletas. Los patrones son evidencia exploratoria; no predicen estaciones vacías ni recomiendan redistribución operativa.</div>', unsafe_allow_html=True)

elif nav == "Demanda temporal":
    hero("Demanda temporal", "Compara ritmos de movilidad y detecta las franjas de mayor actividad.")
    monthly, pm = dataset(MONTH)
    weekday, pw = dataset(WEEK)
    hourly, ph = dataset(HOUR)
    tabs = st.tabs(["Evolución mensual", "Días de semana", "Horas", "Vista conjunta"])
    with tabs[0]:
        if monthly is None: missing("demanda mensual", MONTH)
        else:
            x=findcol(monthly,["month","mes","year_month","fecha","period"])
            y=findcol(monthly,["trips","viajes","total_trips","count","n_trips","demanda"])
            if x and y:
                df=monthly.copy(); df[y]=pd.to_numeric(df[y],errors="coerce")
                fig=px.bar(df,x=x,y=y,color_discrete_sequence=[PRIMARY_BLUE],title="Volumen mensual")
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(style_plot(fig),width='stretch')
                st.caption(source(pm))
                st.dataframe(style_csv_dataframe(df.sort_values(y,ascending=False)),width='stretch')
            else: st.dataframe(style_csv_dataframe(monthly),width='stretch')
    with tabs[1]:
        if weekday is None: missing("demanda por día de semana", WEEK)
        else:
            x=findcol(weekday,["weekday","day_name","dia_semana","day","dow"])
            y=findcol(weekday,["trips","viajes","total_trips","count","n_trips","demanda"])
            if x and y:
                df=weekday.copy(); df[y]=pd.to_numeric(df[y],errors="coerce"); df[x]=df[x].map(weekday_in_spanish); df=df.sort_values(y)
                fig=px.bar(df,x=y,y=x,orientation="h",color=y,color_continuous_scale=["#E7F2F9",PRIMARY_BLUE],title="Ranking de demanda semanal")
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(style_plot(fig),width='stretch')
                st.dataframe(style_csv_dataframe(df.sort_values(y,ascending=False)),width='stretch')
                st.caption(source(pw))
            else: st.dataframe(style_csv_dataframe(weekday),width='stretch')
    with tabs[2]:
        if hourly is None: missing("demanda por hora", HOUR)
        else:
            x=findcol(hourly,["hour","hora","hour_of_day"])
            y=findcol(hourly,["trips","viajes","total_trips","count","n_trips","demanda"])
            if x and y:
                df=hourly.copy(); df[y]=pd.to_numeric(df[y],errors="coerce")
                fig=px.area(df,x=x,y=y,markers=True,color_discrete_sequence=[SKY_BLUE],title="Actividad a lo largo del día")
                fig.update_traces(line=dict(width=3),fillcolor="rgba(147,197,253,.12)")
                st.plotly_chart(style_plot(fig),width='stretch')
                top=df.nlargest(5,y)
                st.markdown("**Horas de mayor actividad**")
                st.dataframe(style_csv_dataframe(top[[x,y]]),width='stretch',hide_index=True)
                st.caption(source(ph))
            else: st.dataframe(style_csv_dataframe(hourly),width='stretch')
    with tabs[3]:
        st.caption(
            "El mapa de calor muestra la intensidad de los viajes "
            "por día de la semana y hora."
        )
        heatmap_path = DATA / "cross_analysis" / "station_time_daily.csv"
        if not heatmap_path.exists():
            heatmap_path = DATA / "station_time_daily.csv"

        if heatmap_path.exists():
            heatmap_data = pd.read_csv(heatmap_path)
            required = ["weekday_num", "hour", "departures"]
            if all(column in heatmap_data.columns for column in required):
                for column in required:
                    heatmap_data[column] = pd.to_numeric(
                        heatmap_data[column], errors="coerce"
                    )
                heatmap_data = heatmap_data.dropna(subset=required)
                if heatmap_data.empty:
                    st.info("El CSV no contiene datos válidos para crear el mapa de calor.")
                else:
                    # Agregamos las salidas de todas las estaciones por día y hora.
                    pivot = heatmap_data.pivot_table(
                        index="weekday_num",
                        columns="hour",
                        values="departures",
                        aggfunc="sum",
                        fill_value=0,
                    )
                    pivot = pivot.reindex(
                        index=range(7),
                        columns=range(24),
                        fill_value=0,
                    )
                    weekday_labels = {
                        0: "Lunes",
                        1: "Martes",
                        2: "Miércoles",
                        3: "Jueves",
                        4: "Viernes",
                        5: "Sábado",
                        6: "Domingo",
                    }
                    pivot.index = [
                        weekday_labels.get(day, str(day)) for day in pivot.index
                    ]
                    pivot.columns = [
                        f"{int(hour):02d}:00" for hour in pivot.columns
                    ]
                    fig = px.imshow(
                        pivot,
                        aspect="equal",
                        color_continuous_scale=["#EAF1FF", SKY_BLUE, BASE_BLUE],
                        labels={
                            "x": "Hora",
                            "y": "Día de la semana",
                            "color": "Salidas",
                        },
                        title="Salidas por día y hora",
                    )
                    fig.update_traces(
                        hovertemplate=(
                            "Día: %{y}<br>Hora: %{x}"
                            "<br>Salidas: %{z:,.0f}<extra></extra>"
                        )
                    )
                    fig = style_plot(fig, 650)
                    fig.update_xaxes(
                        tickmode="array",
                        tickvals=list(pivot.columns),
                        ticktext=list(pivot.columns),
                        tickangle=-45,
                    )
                    fig.update_layout(
                        margin=dict(l=80, r=35, t=70, b=115),
                    )
                    st.plotly_chart(fig, width="stretch")
            else:
                st.error(
                    "El CSV del mapa de calor debe incluir las columnas "
                    "`weekday_num`, `hour` y `departures`."
                )
        else:
            st.error(
                f"No se encuentra el CSV del mapa de calor: "
                f"{heatmap_path.relative_to(ROOT)}"
            )

elif nav == "Estaciones":
    hero("Estaciones", "Compara actividad, entradas, salidas y balance de flujo.")
    b,pb=dataset(BAL)
    if b is None: missing("balance de estaciones", BAL)
    else:
        s=findcol(b,["station","station_name","nombre_estacion","estacion","station_id"])
        d=findcol(b,["departures","departure","salidas","origin_trips","outgoing"])
        a=findcol(b,["arrivals","arrival","llegadas","destination_trips","incoming"])
        bal=findcol(b,["balance","net_flow","arrivals_minus_departures","diferencia"])
        if s and bal:
            df=b.copy()
            df[bal]=pd.to_numeric(df[bal],errors="coerce")
            if d: df[d]=pd.to_numeric(df[d],errors="coerce")
            if a: df[a]=pd.to_numeric(df[a],errors="coerce")
            activity=(df[d]+df[a]) if d and a else None
            metric_row([
                ("Estaciones",f"{df[s].nunique():,}","Estaciones incluidas en este CSV"),
                ("Balance más positivo",f"{df[bal].max():,.1f}","Llegadas − salidas"),
                ("Balance más negativo",f"{df[bal].min():,.1f}","Llegadas − salidas"),
                ("Balance medio",f"{df[bal].mean():,.2f}","Media del balance del conjunto")
            ])
            mode=st.selectbox("Ordenar estaciones",["Mayor actividad","Más llegadas que salidas","Más salidas que llegadas"])
            if mode=="Mayor actividad" and activity is not None:
                view=df.assign(_activity=activity).nlargest(20,"_activity")
                if d and a:
                    melt=view.melt(id_vars=[s],value_vars=[d,a],var_name="Tipo de flujo",value_name="Viajes")
                    fig=px.bar(melt,x=s,y="Viajes",color="Tipo de flujo",barmode="group",color_discrete_sequence=[PRIMARY_BLUE,MID_BLUE],title="Top 20 · entradas y salidas")
                    st.plotly_chart(style_plot(fig,430),width='stretch')
            elif mode=="Más llegadas que salidas":
                view=df.nlargest(20,bal)
            else:
                view=df.nsmallest(20,bal)
            view=view.copy()
            fig=px.bar(view.sort_values(bal),x=bal,y=s,orientation="h",color=bal,color_continuous_scale=[BASE_BLUE,"#EFF6FF",PRIMARY_BLUE],title="Balance de flujo · top 20")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(style_plot(fig,430),width='stretch')
            st.dataframe(style_csv_dataframe(view),width='stretch')
            st.caption(source(pb))
        else:
            st.warning("No reconozco las columnas necesarias de estación y balance.")
            st.dataframe(style_csv_dataframe(b.head(30)),width='stretch')
    st.markdown('<div class="bici-note"><b>Balance = llegadas − salidas.</b> Describe flujo agregado durante el periodo, no bicicletas disponibles ni stock real.</div>',unsafe_allow_html=True)

elif nav == "Corredores":
    hero("Corredores recurrentes", "Separamos volumen, recurrencia y evidencia de desequilibrio.")
    summary,ps=dataset(CORRS)
    evidence,pe=dataset(CORRE)
    st.markdown("### Corredor principal")
    c1,c2,c3=st.columns(3)
    c1.metric("Ruta", "Fernando el Católico → Orense 12")
    c2.metric("Viajes", "166", "Mar–Jue · 08:00", delta_color="off")
    c3.metric("Evidencia", "3/3 franjas", "Cumplen criterios exploratorios", delta_color="off")
    st.markdown('<div class="bici-card"><b>Fernando el Católico → Orense 12</b><br>Martes 08:00: 50 viajes · recurrencia 55,93%<br>Miércoles 08:00: 51 viajes · recurrencia 52,54%<br>Jueves 08:00: 65 viajes · recurrencia 59,32%<br><br>La selección se basa en evidencia de balance en ambas estaciones y persistencia; no en el mayor volumen.</div>',unsafe_allow_html=True)
    st.markdown("### Corredor secundario")
    st.markdown('<div class="bici-card"><b>Puente Praga → Paseo Esperanza</b><br>272 viajes en cuatro combinaciones día-hora. Demanda recurrente, pero el diagnóstico de balance del destino es incompleto.</div>',unsafe_allow_html=True)

    if summary is not None:
        st.subheader("Otros corredores · resumen")
        summary_labels = {
            "route": "Corredor",
            "combinations": "Franjas analizadas",
            "total_trips": "Viajes totales",
            "mean_recurrence": "Recurrencia media (%)",
            "mean_trips_per_eligible_day": "Viajes por día elegible",
            "strong_evidence": "Evidencia fuerte",
            "partial_evidence": "Evidencia parcial",
            "demand_only": "Solo demanda",
        }
        summary_formats = {
            "Franjas analizadas": "{:,.0f}",
            "Viajes totales": "{:,.0f}",
            "Recurrencia media (%)": lambda value: f"{value:.1f}%",
            "Viajes por día elegible": "{:.2f}",
            "Evidencia fuerte": "{:,.0f}",
            "Evidencia parcial": "{:,.0f}",
            "Solo demanda": "{:,.0f}",
        }
        st.dataframe(
            styled_dataframe(summary, summary_labels, summary_formats),
            width="stretch",
            height=280,
            hide_index=True,
        )
        st.caption(source(ps))
    if evidence is not None:
        st.subheader("Evidencia por día y hora")
        evidence_labels = {
            "route": "Corredor",
            "weekday": "Día",
            "weekday_num": "N.º de día",
            "hour": "Hora",
            "origin_id": "ID origen",
            "origin_name": "Estación origen",
            "destination_id": "ID destino",
            "destination_name": "Estación destino",
            "total_trips": "Viajes",
            "active_days": "Días activos",
            "eligible_days": "Días elegibles",
            "recurrence_pct": "Recurrencia (%)",
            "avg_trips_per_eligible_day": "Viajes/día elegible",
            "avg_trips_per_active_day": "Viajes/día activo",
            "origin_balance": "Balance origen",
            "origin_negative_days_pct": "Días negativos · origen (%)",
            "origin_positive_days_pct": "Días positivos · origen (%)",
            "destination_balance": "Balance destino",
            "destination_positive_days_pct": "Días positivos · destino (%)",
            "destination_negative_days_pct": "Días negativos · destino (%)",
            "evidence_class": "Clasificación de evidencia",
        }
        evidence_formats = {
            "N.º de día": "{:,.0f}",
            "Hora": "{:02.0f}:00",
            "ID origen": "{:,.0f}",
            "ID destino": "{:,.0f}",
            "Viajes": "{:,.0f}",
            "Días activos": "{:,.0f}",
            "Días elegibles": "{:,.0f}",
            "Recurrencia (%)": lambda value: f"{value:.1f}%",
            "Viajes/día elegible": "{:.2f}",
            "Viajes/día activo": "{:.2f}",
            "Balance origen": "{:,.2f}",
            "Días negativos · origen (%)": lambda value: f"{value:.1f}%",
            "Días positivos · origen (%)": lambda value: f"{value:.1f}%",
            "Balance destino": "{:,.2f}",
            "Días positivos · destino (%)": lambda value: f"{value:.1f}%",
            "Días negativos · destino (%)": lambda value: f"{value:.1f}%",
        }
        st.dataframe(
            styled_dataframe(
                evidence,
                evidence_labels,
                evidence_formats,
                {"weekday": weekday_in_spanish},
            ),
            width="stretch",
            height=420,
            hide_index=True,
        )
        st.caption(source(pe))
    st.markdown(
        '<div class="bici-note"><b>Clasificación exploratoria:</b> '
        "no afirma falta de bicicletas, predicción de agotamiento ni "
        'necesidad operativa de redistribución.</div>',
        unsafe_allow_html=True,
    )


elif nav == "Mapa de movilidad":
    hero(
        "Mapa de movilidad",
        "Explora la distribución geográfica de las estaciones BiciMAD con coordenadas validadas."
    )

    st.markdown("### Estaciones de BiciMAD")
    st.caption(
        "Mapa basado exclusivamente en el fichero de integración geográfica validada. "
        "No se atribuyen métricas de demanda a estaciones sin una correspondencia fiable."
    )

    coord_path = VALIDATED_COORDS

    if not coord_path.exists():
        st.error(f"No se encuentra el archivo geográfico esperado: {coord_path.relative_to(ROOT)}")
    else:
        coords = read_csv(coord_path)

        required_coord = [
            "bicimad_station_id",
            "bicimad_station_name",
            "bicimad_lon",
            "bicimad_lat",
        ]

        missing_coord = [c for c in required_coord if c not in coords.columns]

        if missing_coord:
            st.error(f"Faltan columnas en el CSV geográfico: {missing_coord}")
            st.write("Columnas detectadas:", list(coords.columns))
        else:
            coords["bicimad_lon"] = pd.to_numeric(
                coords["bicimad_lon"], errors="coerce"
            )
            coords["bicimad_lat"] = pd.to_numeric(
                coords["bicimad_lat"], errors="coerce"
            )

            coords = coords.dropna(
                subset=["bicimad_lon", "bicimad_lat"]
            )

            coords = coords[
                coords["bicimad_lat"].between(35, 45)
                & coords["bicimad_lon"].between(-10, 5)
            ].copy()

            # Color por estado, si existe la columna
            if "bicimad_state" in coords.columns:
                coords["_color"] = coords["bicimad_state"].apply(
                    lambda s: (
                        [47, 111, 219, 200]
                        if str(s).upper() == "IN_SERVICE"
                        else [147, 197, 253, 190]
                    )
                )
            else:
                coords["_color"] = [[47, 111, 219, 200]] * len(coords)

            coords["_radius"] = 100

            view = pdk.ViewState(
                latitude=float(coords["bicimad_lat"].median()),
                longitude=float(coords["bicimad_lon"].median()),
                zoom=11.5,
                pitch=0,
                bearing=0,
            )

            scatter = pdk.Layer(
                "ScatterplotLayer",
                data=coords,
                get_position="[bicimad_lon, bicimad_lat]",
                get_radius="_radius",
                get_fill_color="_color",
                get_line_color=[255, 255, 255, 220],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
            )

            tooltip_fields = "<b>{bicimad_station_name}</b><br>ID: {bicimad_station_id}"

            if "bicimad_state" in coords.columns:
                tooltip_fields += "<br>Estado: {bicimad_state}"

            if "bicimad_bases" in coords.columns:
                tooltip_fields += "<br>Bases: {bicimad_bases}"

            deck = pdk.Deck(
                layers=[scatter],
                initial_view_state=view,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={
                    "html": tooltip_fields,
                    "style": {
                        "backgroundColor": "#EAF1FC",
                        "color": "#173F83",
                    },
                },
            )

            st.pydeck_chart(deck, width="stretch")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Estaciones geolocalizadas",
                    f"{len(coords):,}",
                )

            with col2:
                if "bicimad_state" in coords.columns:
                    active = (
                        coords["bicimad_state"].astype(str).str.upper()
                        == "IN_SERVICE"
                    ).sum()
                    st.metric("En servicio", f"{active:,}")
                else:
                    st.metric("Coordenadas válidas", f"{len(coords):,}")

            with col3:
                st.metric(
                    "Fuente",
                    "Integración validada",
                )

            if "bicimad_state" in coords.columns:
                st.caption(
                    "Azul: estaciones en servicio. "
                    "Azul claro: otros estados."
                )

            st.caption(source(coord_path))

            st.markdown("### Tabla de estaciones")

            display_columns = [
                "bicimad_station_id",
                "bicimad_station_name",
                "bicimad_lat",
                "bicimad_lon",
            ]

            optional_columns = [
                "bicimad_state",
                "bicimad_bases",
                "crtm_station_name",
                "crtm_system",
                "match_confidence",
            ]

            display_columns += [
                c for c in optional_columns if c in coords.columns
            ]

            st.dataframe(
                style_csv_dataframe(
                    coords[display_columns].sort_values("bicimad_station_name")
                ),
                width="stretch",
                hide_index=True,
            )

            st.markdown(
                '<div class="bici-note">'
                "Este mapa muestra la localización y atributos de las estaciones. "
                "La demanda histórica se presenta en las otras vistas del dashboard; "
                "no se vincula aquí porque la correspondencia entre identificadores "
                "de los datasets no está suficientemente validada."
                "</div>",
                unsafe_allow_html=True,
            )
else:
    hero("Datos y metodología", "Transparencia sobre fuentes, definiciones, cobertura y límites.")
    st.markdown("### Qué analizamos")
    st.markdown("""
    - Demanda temporal agregada.
    - Diagnóstico de estaciones por día y hora.
    - Flujos origen–destino y recurrencia.
    - Integración contextual con sistemas de bicicleta pública CRTM mediante matching validado.
    """)
    st.markdown("### Definiciones")
    col1,col2=st.columns(2)
    with col1:
        st.markdown('<div class="bici-card"><b>Recurrencia</b><br>Porcentaje de días elegibles en los que aparece una ruta.</div>',unsafe_allow_html=True)
        st.markdown('<div class="bici-card"><b>Intensidad</b><br>Volumen observado en una combinación de día y hora.</div>',unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="bici-card"><b>Balance</b><br>Llegadas − salidas.</div>',unsafe_allow_html=True)
        st.markdown('<div class="bici-card"><b>Persistencia</b><br>Proporción de días observados con el signo del balance definido.</div>',unsafe_allow_html=True)
    st.markdown("### Limitaciones")
    st.markdown("""
    - Periodos y coberturas diferentes entre datasets.
    - Recurrencia no equivale a intensidad.
    - Balance de flujo no es inventario de bicicletas.
    - La cobertura de diagnóstico simultáneo de origen y destino es limitada.
    - La redistribución es una hipótesis exploratoria, no una recomendación operativa.
    """)
    st.subheader("CSV locales detectados")
    files=[]
    for r in (DATA,ANALYSIS):
        if r.exists():
            files += [{"Ruta":str(p.relative_to(ROOT)),"Tamaño MB":round(p.stat().st_size/1024**2,3)} for p in r.rglob("*.csv")]
    if files:
        st.dataframe(
            style_csv_dataframe(pd.DataFrame(files).sort_values("Ruta")),
            width="stretch",
            hide_index=True,
        )
    else:
        st.error("No encuentro data/processed ni analysis junto al dashboard. Comprueba la ubicación de esta carpeta.")
    st.markdown('<div class="bici-note"><b>Procedencia de los datos:</b> https://datos.madrid.es/dataset/208327-0-transporte-bicicletas-bicimad/downloads</div>', unsafe_allow_html=True)
        
