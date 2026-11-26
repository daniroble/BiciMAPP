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
DATA = ROOT / "data" / "processed"
ANALYSIS = ROOT / "analysis"

# Palette: BiciMAPP green, deep navy, aqua, orange
GREEN = "#16A085"
DARK = "#12343B"
AQUA = "#47C7B5"
ORANGE = "#F39C45"
RED = "#E76F51"
BLUE = "#4776E6"
PALETTE = [GREEN, AQUA, ORANGE, BLUE, RED, "#8E6CBA", "#E5B94D"]
PLOT_BG = "#FFFFFF"

def norm(x):
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", x).strip("_")

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
        font=dict(family="Inter, Arial, sans-serif", color=DARK, size=13),
        margin=dict(l=24, r=20, t=58, b=40),
        title=dict(font=dict(size=18, color=DARK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(showgrid=False, linecolor="#E5ECEB"),
        yaxis=dict(gridcolor="#E8EFEE", zerolinecolor="#D5E2E0"),
    )
    return fig

st.markdown("""
<style>
:root { --bic-green:#16A085; --bic-dark:#12343B; }
.stApp { background: #F4F7F6; color: var(--bic-dark); }
[data-testid="stSidebar"] { background: #12343B; }
[data-testid="stSidebar"] * { color: #F4FAF9 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: 5px 0; }
h1,h2,h3 { color: #12343B !important; }
div[data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E3ECEA; padding:18px 20px; border-radius:14px; box-shadow:0 3px 12px rgba(18,52,59,.04); }
div[data-testid="stMetric"] label { color:#55716F !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color:#12343B !important; }
.block-container { padding-top: 1.6rem; padding-bottom: 2.2rem; }
.bici-hero { background:linear-gradient(120deg,#12343B 0%,#176E64 58%,#16A085 100%); color:white; padding:26px 30px; border-radius:18px; margin-bottom:20px; }
.bici-hero h1 { color:white !important; margin:0; }
.bici-hero p { color:#E7F5F2; margin:8px 0 0 0; font-size:1.03rem; }
.bici-card { background:white; border:1px solid #E3ECEA; border-radius:15px; padding:18px 20px; }
.bici-kicker { color:#16A085; font-weight:700; letter-spacing:.08em; text-transform:uppercase; font-size:.75rem; }
.bici-note { background:#EAF5F2; border-left:4px solid #16A085; padding:12px 15px; border-radius:8px; }
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

def metric_row(items):
    cols = st.columns(len(items))
    for c, (label, value, helptext) in zip(cols, items):
        c.metric(label, value, help=helptext)

def missing(label, names):
    st.warning(f"No localizo el dataset de **{label}**. Busqué nombres: {', '.join(names)}")

nav = st.sidebar.radio("BiciMAPP", ["Resumen ejecutivo", "Demanda temporal", "Estaciones", "Mapa de movilidad", "Corredores", "Datos y metodología"])
st.sidebar.markdown("---")
st.sidebar.markdown("**DATAMAD · Madrid**")
st.sidebar.caption("Open data · análisis reproducible")
st.sidebar.caption("Prototipo exploratorio. No representa inventario en tiempo real.")

if nav == "Resumen ejecutivo":
    hero("Madrid en bicicleta", "Identificamos cuándo, dónde y entre qué estaciones se repiten los patrones de movilidad.", "BiciMAPP · Open data")
    m, pm = dataset(MONTH)
    b, pb = dataset(BAL)
    station_col = findcol(b, ["station","station_name","nombre_estacion","estacion"]) if b is not None else None
    trips_col = findcol(m, ["trips","viajes","total_trips","count","n_trips","demanda"]) if m is not None else None
    total = pd.to_numeric(m[trips_col], errors="coerce").sum() if trips_col else None
    n_stations = b[station_col].nunique() if station_col else None
    metric_row([
        ("Viajes agregados", f"{total:,.0f}" if total is not None else "—", "Suma del dataset mensual disponible"),
        ("Estaciones en diagnóstico", f"{n_stations:,}" if n_stations is not None else "—", "Estaciones presentes en el diagnóstico"),
        ("Corredor con evidencia", "Fernando → Orense 12", "Corredor principal seleccionado por evidencia conjunta"),
        ("Franja de análisis", "Mañana · 07–09 h", "Análisis de recurrencia de corredores")
    ])
    st.markdown("### El hallazgo")
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown('<div class="bici-card"><h3>Fernando el Católico → Orense 12</h3><p>Martes, miércoles y jueves a las 08:00. Se observan <b>166 viajes</b> en las tres combinaciones de día-hora seleccionadas.</p><p>La selección se basa en recurrencia y evidencia de balance en ambas estaciones, no en ser el corredor de mayor volumen.</p></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="bici-card"><h3>Qué aporta BiciMAPP</h3><ul><li>Patrones temporales de demanda</li><li>Estaciones con flujo persistentemente positivo o negativo</li><li>Rutas recurrentes e intensidad por separado</li><li>Transparencia sobre cobertura y límites</li></ul></div>', unsafe_allow_html=True)
    st.markdown("### Evolución de demanda")
    if m is not None and trips_col:
        x = findcol(m, ["month","mes","year_month","fecha","period"])
        if x:
            m2=m.copy(); m2[trips_col]=pd.to_numeric(m2[trips_col],errors="coerce")
            fig=px.area(m2,x=x,y=trips_col,markers=True,color_discrete_sequence=[GREEN],title="Viajes por mes · cobertura disponible")
            fig.update_traces(line=dict(width=3),fillcolor="rgba(22,160,133,.12)")
            st.plotly_chart(style_plot(fig,360),width='stretch')
            st.caption(source(pm))
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
                fig=px.bar(df,x=x,y=y,color_discrete_sequence=[GREEN],title="Volumen mensual")
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(style_plot(fig),width='stretch')
                st.caption(source(pm))
                st.dataframe(df.sort_values(y,ascending=False),width='stretch')
            else: st.dataframe(monthly,width='stretch')
    with tabs[1]:
        if weekday is None: missing("demanda por día de semana", WEEK)
        else:
            x=findcol(weekday,["weekday","day_name","dia_semana","day","dow"])
            y=findcol(weekday,["trips","viajes","total_trips","count","n_trips","demanda"])
            if x and y:
                df=weekday.copy(); df[y]=pd.to_numeric(df[y],errors="coerce"); df=df.sort_values(y)
                fig=px.bar(df,x=y,y=x,orientation="h",color=y,color_continuous_scale=["#B8E4DB",GREEN],title="Ranking de demanda semanal")
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(style_plot(fig),width='stretch')
                st.dataframe(df.sort_values(y,ascending=False),width='stretch')
                st.caption(source(pw))
            else: st.dataframe(weekday,width='stretch')
    with tabs[2]:
        if hourly is None: missing("demanda por hora", HOUR)
        else:
            x=findcol(hourly,["hour","hora","hour_of_day"])
            y=findcol(hourly,["trips","viajes","total_trips","count","n_trips","demanda"])
            if x and y:
                df=hourly.copy(); df[y]=pd.to_numeric(df[y],errors="coerce")
                fig=px.area(df,x=x,y=y,markers=True,color_discrete_sequence=[BLUE],title="Actividad a lo largo del día")
                fig.update_traces(line=dict(width=3),fillcolor="rgba(71,118,230,.12)")
                st.plotly_chart(style_plot(fig),width='stretch')
                top=df.nlargest(5,y)
                st.markdown("**Horas de mayor actividad**")
                st.dataframe(top[[x,y]],width='stretch',hide_index=True)
                st.caption(source(ph))
            else: st.dataframe(hourly,width='stretch')
    with tabs[3]:
        st.markdown("Esta vista combina los agregados disponibles. No se construye un heatmap si el dataset no contiene simultáneamente día y hora.")
        candidate = hourly
        if candidate is not None:
            day=findcol(candidate,["weekday","day_name","dia_semana","day","dow"])
            hour=findcol(candidate,["hour","hora","hour_of_day"])
            val=findcol(candidate,["trips","viajes","total_trips","count","n_trips","demanda"])
            if day and hour and val:
                c=candidate.copy(); c[val]=pd.to_numeric(c[val],errors="coerce")
                pivot=c.pivot_table(index=day,columns=hour,values=val,aggfunc="sum")
                fig=px.imshow(pivot,aspect="auto",color_continuous_scale=["#F1F8F6","#82D3C2",GREEN],labels={"color":"Viajes"},title="Heatmap · día × hora")
                st.plotly_chart(style_plot(fig,440),width='stretch')
            else:
                st.info("El agregado horario disponible no incluye día de semana y hora en una misma tabla; por tanto, no es posible construir esta matriz sin datos adicionales.")
        else:
            missing("demanda horaria", HOUR)

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
                    fig=px.bar(melt,x=s,y="Viajes",color="Tipo de flujo",barmode="group",color_discrete_sequence=[GREEN,ORANGE],title="Top 20 · entradas y salidas")
                    st.plotly_chart(style_plot(fig,430),width='stretch')
            elif mode=="Más llegadas que salidas":
                view=df.nlargest(20,bal)
            else:
                view=df.nsmallest(20,bal)
            view=view.copy()
            fig=px.bar(view.sort_values(bal),x=bal,y=s,orientation="h",color=bal,color_continuous_scale=["#E76F51","#F4F7F6",GREEN],title="Balance de flujo · top 20")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(style_plot(fig,430),width='stretch')
            st.dataframe(view,width='stretch')
            st.caption(source(pb))
        else:
            st.warning("No reconozco las columnas necesarias de estación y balance.")
            st.dataframe(b.head(30),width='stretch')
    st.markdown('<div class="bici-note"><b>Balance = llegadas − salidas.</b> Describe flujo agregado durante el periodo, no bicicletas disponibles ni stock real.</div>',unsafe_allow_html=True)

elif nav == "Corredores":
    hero("Corredores recurrentes", "Separamos volumen, recurrencia y evidencia de desequilibrio.")
    summary,ps=dataset(CORRS)
    evidence,pe=dataset(CORRE)
    st.markdown("### Corredor principal")
    c1,c2,c3=st.columns(3)
    c1.metric("Ruta", "Fernando → Orense 12")
    c2.metric("Viajes", "166", "Mar–Jue · 08:00")
    c3.metric("Evidencia", "3/3 franjas", "Cumplen criterios exploratorios")
    st.markdown('<div class="bici-card"><b>Fernando el Católico → Orense 12</b><br>Martes 08:00: 50 viajes · recurrencia 55,93%<br>Miércoles 08:00: 51 viajes · recurrencia 52,54%<br>Jueves 08:00: 65 viajes · recurrencia 59,32%<br><br>La selección se basa en evidencia de balance en ambas estaciones y persistencia; no en el mayor volumen.</div>',unsafe_allow_html=True)
    st.markdown("### Corredor secundario")
    st.markdown('<div class="bici-card"><b>Puente Praga → Paseo Esperanza</b><br>272 viajes en cuatro combinaciones día-hora. Demanda recurrente, pero el diagnóstico de balance del destino es incompleto.</div>',unsafe_allow_html=True)
    if summary is not None:
        st.subheader("Otros corredores · resumen")
        st.dataframe(summary,width='stretch')
        st.caption(source(ps))
    if evidence is not None:
        st.subheader("Evidencia por día y hora")
        st.dataframe(evidence,width='stretch')
        st.caption(source(pe))
    st.warning("Clasificación exploratoria: no afirma falta de bicicletas, predicción de agotamiento ni necesidad operativa de redistribución.")


elif nav == "Mapa de movilidad":
    hero("Mapa de movilidad", "Explora estaciones georreferenciadas y su actividad. El mapa usa coordenadas reales disponibles en los CSV locales.")
    st.markdown("### Capas del mapa")
    st.caption("El mapa se construye con coordenadas del archivo de integración CRTM/BiciMAD cuando está disponible. Métricas de estación se enlazan por nombre normalizado exacto; no se inventan coordenadas.")

    # Find candidate coordinate files by filename and columns
    coord_candidates = []
    roots = [DATA, ANALYSIS]
    for root in roots:
        if root.exists():
            for p in root.rglob("*.csv"):
                stem = norm(p.stem)
                if any(k in stem for k in ["crtm", "integration", "integracion", "validated", "municipal", "station", "estacion"]):
                    d = read_csv(p)
                    latc = findcol(d, ["latitude", "lat", "latitud", "coord_y", "y"])
                    lonc = findcol(d, ["longitude", "lon", "lng", "longitud", "coord_x", "x"])
                    if latc and lonc:
                        coord_candidates.append((p,d,latc,lonc))
    if not coord_candidates:
        st.warning("No he encontrado automáticamente un CSV local con columnas de latitud y longitud reconocibles. Revisa Datos y metodología o añade el CSV validado de coordenadas a data/processed.")
    else:
        # Prefer validated integration files
        coord_candidates.sort(key=lambda x: (("validated" in norm(x[0].stem) or "validado" in norm(x[0].stem)), ("crtm" in norm(x[0].stem))), reverse=True)
        cp, coords, latc, lonc = coord_candidates[0]
        stationc = findcol(coords, ["station_name", "station", "nombre_estacion", "estacion", "name", "municipality_station", "bicimad_station"])
        if stationc is None:
            st.warning(f"Encontré coordenadas en `{cp.name}`, pero no identifico la columna de nombre de estación. Columnas disponibles:")
            st.write(list(coords.columns))
        else:
            coords = coords.copy()
            coords[latc] = pd.to_numeric(coords[latc], errors="coerce")
            coords[lonc] = pd.to_numeric(coords[lonc], errors="coerce")
            coords = coords.dropna(subset=[latc,lonc])
            coords = coords[(coords[latc].between(35, 45)) & (coords[lonc].between(-10, 5))]
            coords = coords.drop_duplicates(subset=[stationc])
            # station diagnostic dataset
            bal, bp = dataset(BAL)
            bs = findcol(bal, ["station", "station_name", "nombre_estacion", "estacion", "station_id"]) if bal is not None else None
            departures = findcol(bal, ["departures", "departure", "salidas", "origin_trips", "outgoing"]) if bal is not None else None
            arrivals = findcol(bal, ["arrivals", "arrival", "llegadas", "destination_trips", "incoming"]) if bal is not None else None
            balance = findcol(bal, ["balance", "net_flow", "arrivals_minus_departures", "diferencia"]) if bal is not None else None

            def keyname(v):
                return norm(v)
            coords["_join"] = coords[stationc].map(keyname)
            if bal is not None and bs:
                bal = bal.copy()
                bal["_join"] = bal[bs].map(keyname)
                # Aggregate if station file contains multiple records
                agg = {"_join": "first"}
                for c in [departures, arrivals, balance]:
                    if c and c not in agg:
                        agg[c] = "sum"
                bal = bal.groupby("_join", as_index=False).agg({c: fn for c,fn in agg.items() if c != "_join"})
                coords = coords.merge(bal, on="_join", how="left")
            else:
                departures=arrivals=balance=None

            map_metric = st.selectbox("Colorear y dimensionar estaciones según", ["Actividad total", "Salidas", "Llegadas", "Balance"])
            if departures and arrivals:
                coords["_activity"] = pd.to_numeric(coords[departures],errors="coerce").fillna(0) + pd.to_numeric(coords[arrivals],errors="coerce").fillna(0)
            else:
                coords["_activity"] = 1
            metric_col = {"Actividad total":"_activity","Salidas":departures,"Llegadas":arrivals,"Balance":balance}.get(map_metric)
            if metric_col and metric_col in coords.columns:
                coords["_metric"] = pd.to_numeric(coords[metric_col],errors="coerce").fillna(0)
            else:
                coords["_metric"] = 0
                if map_metric != "Actividad total":
                    st.info("Esta métrica no está disponible en el CSV de diagnóstico enlazado. Se muestra la ubicación sin esa métrica.")
            if map_metric == "Balance":
                coords["_color_group"] = coords["_metric"].apply(lambda v: "Positivo" if v>0 else ("Negativo" if v<0 else "Neutro"))
                color_map = {"Positivo":[22,160,133,180],"Negativo":[231,111,81,180],"Neutro":[120,140,140,160]}
                coords["_rgba"] = coords["_color_group"].map(color_map)
            else:
                coords["_rgba"] = coords["_metric"].apply(lambda v: [22,160,133,190] if v >= 0 else [231,111,81,190])
            coords["_radius"] = coords["_metric"].abs()
            if coords["_radius"].max() > 0:
                coords["_radius"] = 180 + 900 * coords["_radius"] / coords["_radius"].max()
            else:
                coords["_radius"] = 280

            # Madrid centered view, adjust to actual coordinates if available
            center_lat = float(coords[latc].median())
            center_lon = float(coords[lonc].median())
            tooltip_fields = [stationc, "_metric"]
            tooltip = {"html": f"<b>{{{stationc}}}</b><br>{map_metric}: {{{{_metric}}}}", "style":{"backgroundColor":"#12343B","color":"white"}}
            layer = pdk.Layer(
                "ScatterplotLayer", data=coords,
                get_position=f"[{lonc}, {latc}]",
                get_radius="_radius",
                get_fill_color="_rgba",
                get_line_color=[255,255,255,200],
                line_width_min_pixels=1,
                stroked=True, filled=True, pickable=True, auto_highlight=True,
            )
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11.3, pitch=0),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style",
                tooltip={"html": f"<b>{{{stationc}}}</b><br>{map_metric}: {{{{_metric}}}}", "style":{"backgroundColor":"#12343B","color":"white"}},
            )
            st.pydeck_chart(deck, width='stretch')
            metric_row([
                ("Estaciones geolocalizadas", f"{len(coords):,}", "Registros con coordenadas válidas"),
                ("Con diagnóstico enlazado", f"{coords['_metric'].notna().sum():,}", "Métricas enlazadas por nombre normalizado exacto"),
                ("Archivo de coordenadas", cp.name, "Fuente de coordenadas seleccionada"),
                ("Métrica de mapa", map_metric, "Selector de visualización")
            ])
            st.caption(source(cp))
            st.markdown("### Estaciones visibles en los datos")
            display_cols = [stationc,latc,lonc]
            for c in [departures,arrivals,balance,"_metric"]:
                if c and c in coords.columns and c not in display_cols:
                    display_cols.append(c)
            st.dataframe(coords[display_cols].sort_values("_metric",ascending=False).head(50),width='stretch',hide_index=True)
            st.info("Este primer mapa es de estaciones. La capa de corredores origen–destino se incorporará después, usando geometrías derivadas de las coordenadas validadas de ambos extremos.")

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
        st.dataframe(pd.DataFrame(files).sort_values("Ruta"),width='stretch',hide_index=True)
    else:
        st.error("No encuentro data/processed ni analysis junto al dashboard. Comprueba la ubicación de esta carpeta.")
