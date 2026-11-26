from pathlib import Path
import re, unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title='BiciMAPP | Movilidad', page_icon='🚲', layout='wide')
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
DATA=ROOT/'data'/'processed'
ANALYSIS=ROOT/'analysis'

def norm(x):
    x=unicodedata.normalize('NFKD',str(x)).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','_',x).strip('_')
@st.cache_data(show_spinner=False)
def read_csv(p):
    try: return pd.read_csv(p,low_memory=False)
    except Exception:
        try: return pd.read_csv(p,sep=';',low_memory=False)
        except Exception: return pd.DataFrame()
def locate(names):
    target={norm(n) for n in names}
    for root in (DATA,ANALYSIS):
        if root.exists():
            for p in root.rglob('*.csv'):
                if norm(p.stem) in target: return p
    return None
def dataset(names):
    p=locate(names)
    return (read_csv(p),p) if p else (None,None)
def findcol(df, aliases):
    if df is None or df.empty:return None
    columns={norm(c):c for c in df.columns}
    for a in aliases:
        if norm(a) in columns:return columns[norm(a)]
    for c in df.columns:
        nc=norm(c)
        for a in aliases:
            na=norm(a)
            if na and na in nc:return c
    return None
def missing(label,names): st.info(f'No localizo el CSV de {label}. Busqué: {", ".join(names)}')
def source_caption(p):
    try:return f'Fuente local: `{p.relative_to(ROOT)}`'
    except:return f'Fuente: `{p.name}`'

MONTH=['demand_monthly','monthly_demand','demanda_mensual']
WEEK=['demand_weekday','weekday_demand','demanda_dia_semana']
HOUR=['demand_hourly','hourly_demand','demanda_horaria']
BAL=['station_demand_balance','station_balance','balance_estaciones']
TOPD=['stations_top_departures','top_departures','estaciones_salidas']
TOPA=['stations_top_arrivals','top_arrivals','estaciones_llegadas']
TOPI=['stations_top_imbalance','top_imbalance','estaciones_desequilibrio']
ODREC=['od_recurrence_rank','od_recurrence_filtered','od_top_recurrence_audited','od_recurrence_audited']
ODVOL=['od_total_demand_rank','od_top_total_volume_audited']
CORRE=['final_corridor_evidence']
CORRS=['final_corridor_summary']

nav=st.sidebar.radio('Navegación',['Resumen','Demanda','Estaciones','Corredores','Datos y metodología'])
st.sidebar.markdown('---')
st.sidebar.caption('BiciMAPP · DATAMAD')
st.sidebar.caption('Open data · análisis reproducible')

if nav=='Resumen':
    st.title('🚲 BiciMAPP')
    st.subheader('Explora cuándo, dónde y entre qué estaciones se repite la movilidad en bicicleta.')
    st.markdown('### Pregunta del proyecto')
    st.markdown('**¿Qué patrones recurrentes de movilidad podemos identificar y dónde existe evidencia de desequilibrio de flujo?**')
    b,pb=dataset(BAL)
    m,pm=dataset(MONTH)
    stationcol=findcol(b,['station','station_name','nombre_estacion','estacion'])
    metriccol=findcol(m,['trips','viajes','total_trips','count','n_trips','demanda'])
    c1,c2,c3=st.columns(3)
    c1.metric('Estaciones en diagnóstico',f'{b[stationcol].nunique():,}' if stationcol else '—')
    c2.metric('Viajes agregados mensual',f'{pd.to_numeric(m[metriccol],errors="coerce").sum():,.0f}' if metriccol else '—')
    c3.metric('Corredor principal','Fernando el Católico → Orense 12')
    st.divider()
    st.markdown('### Hallazgo principal')
    st.markdown('**Fernando el Católico → Orense 12, martes–jueves a las 08:00:** 166 viajes observados en las tres combinaciones día-hora; las tres presentan evidencia consistente de estación emisora y receptora bajo los umbrales exploratorios definidos.')
    st.markdown('### Qué permite ver el análisis')
    st.markdown('- La demanda cambia por hora y día de la semana.\n- Hay patrones persistentes de entradas y salidas por estación.\n- Recurrencia e intensidad son métricas distintas.\n- Solo una parte de las rutas dispone de diagnóstico simultáneo de origen y destino.')
    st.warning('Balance de flujo (llegadas − salidas) no es inventario de bicicletas, ni predice que una estación se quede vacía.')

elif nav=='Demanda':
    st.title('Demanda')
    st.caption('Explora las distribuciones temporales. No compares periodos incompletos como si tuvieran la misma cobertura.')
    t1,t2,t3=st.tabs(['Mensual','Día de semana','Hora'])
    with t1:
        df,p=dataset(MONTH)
        if df is None:missing('demanda mensual',MONTH)
        else:
            x=findcol(df,['month','mes','year_month','fecha','period']); y=findcol(df,['trips','viajes','total_trips','count','n_trips','demanda'])
            if x and y:
                df[y]=pd.to_numeric(df[y],errors='coerce'); st.plotly_chart(px.line(df,x=x,y=y,markers=True,title='Demanda mensual'),use_container_width=True); st.caption(source_caption(p))
            else: st.warning('No reconozco las columnas automáticamente. Revisa la muestra.'); st.dataframe(df.head(30),use_container_width=True)
    with t2:
        df,p=dataset(WEEK)
        if df is None:missing('demanda por día de semana',WEEK)
        else:
            x=findcol(df,['weekday','day_name','dia_semana','day','dow']); y=findcol(df,['trips','viajes','total_trips','count','n_trips','demanda'])
            if x and y:
                df[y]=pd.to_numeric(df[y],errors='coerce'); st.plotly_chart(px.bar(df,x=x,y=y,title='Viajes por día de semana'),use_container_width=True); st.dataframe(df.sort_values(y,ascending=False),use_container_width=True)
            else: st.warning('No reconozco las columnas automáticamente.'); st.dataframe(df.head(30),use_container_width=True)
    with t3:
        df,p=dataset(HOUR)
        if df is None:missing('demanda por hora',HOUR)
        else:
            x=findcol(df,['hour','hora','hour_of_day']); y=findcol(df,['trips','viajes','total_trips','count','n_trips','demanda'])
            if x and y:
                df[y]=pd.to_numeric(df[y],errors='coerce'); st.plotly_chart(px.bar(df,x=x,y=y,title='Viajes por hora'),use_container_width=True); st.dataframe(df.sort_values(y,ascending=False),use_container_width=True)
            else: st.warning('No reconozco las columnas automáticamente.'); st.dataframe(df.head(30),use_container_width=True)

elif nav=='Estaciones':
    st.title('Estaciones')
    st.caption('Balance = llegadas − salidas. Es una medida de flujo agregado, no de bicicletas disponibles.')
    df,p=dataset(BAL)
    if df is None:missing('balance de estaciones',BAL)
    else:
        s=findcol(df,['station','station_name','nombre_estacion','estacion','station_id']); d=findcol(df,['departures','departure','salidas','origin_trips','outgoing']); a=findcol(df,['arrivals','arrival','llegadas','destination_trips','incoming']); b=findcol(df,['balance','net_flow','arrivals_minus_departures','diferencia'])
        if s and b:
            df[b]=pd.to_numeric(df[b],errors='coerce')
            order=st.selectbox('Ranking',['Balance positivo','Balance negativo','Actividad total'])
            if d and a:
                df[d]=pd.to_numeric(df[d],errors='coerce'); df[a]=pd.to_numeric(df[a],errors='coerce')
                if order=='Actividad total':df['_activity']=df[d]+df[a]; view=df.sort_values('_activity',ascending=False).head(20)
                elif order=='Balance positivo':view=df.sort_values(b,ascending=False).head(20)
                else:view=df.sort_values(b).head(20)
                melt=view.melt(id_vars=[s],value_vars=[d,a],var_name='Flujo',value_name='Viajes')
                st.plotly_chart(px.bar(melt,x=s,y='Viajes',color='Flujo',barmode='group',title='Salidas y llegadas — top 20'),use_container_width=True)
            else:view=df.sort_values(b,ascending=order=='Balance positivo').head(20)
            st.plotly_chart(px.bar(view,x=s,y=b,title='Balance de flujo'),use_container_width=True)
            st.dataframe(view,use_container_width=True)
        else:st.warning('No identifico columnas de estación y balance.');st.dataframe(df.head(30),use_container_width=True)
    st.info('Un balance negativo indica más salidas que llegadas en el periodo; positivo, más llegadas. No mide stock ni disponibilidad.')

elif nav=='Corredores':
    st.title('Corredores recurrentes')
    st.caption('Recurrencia, intensidad y desequilibrio son conceptos distintos. Se muestran separados.')
    summary,ps=dataset(CORRS); evidence,pe=dataset(CORRE)
    if summary is not None:st.subheader('Resumen de corredores');st.dataframe(summary,use_container_width=True);st.caption(source_caption(ps))
    if evidence is not None:st.subheader('Evidencia por día y hora');st.dataframe(evidence,use_container_width=True);st.caption(source_caption(pe))
    st.subheader('Corredor principal')
    st.markdown('**Fernando el Católico → Orense 12**')
    st.table(pd.DataFrame({'Día':['Martes 08:00','Miércoles 08:00','Jueves 08:00'],'Viajes':[50,51,65],'Recurrencia':[ '55,93%','52,54%','59,32%']}))
    st.markdown('Total de las tres combinaciones: **166 viajes**. La selección se basa en evidencia de balance de ambas estaciones y persistencia, no en ser el corredor de mayor volumen.')
    st.subheader('Corredor secundario')
    st.markdown('**Puente Praga → Paseo Esperanza** — 272 viajes en cuatro combinaciones día-hora; recurrencia media aproximada 64,83%. Tiene demanda recurrente, pero la diagnosis de balance de destino es incompleta.')
    st.warning('Clasificación exploratoria: no afirma falta de bicicletas, predicción de agotamiento ni necesidad operativa de redistribución.')

else:
    st.title('Datos y metodología')
    st.markdown('### Fuentes y capas')
    st.markdown('- Datos históricos y agregados de demanda de BiciMAD.\n- Diagnóstico estación × día × hora.\n- Flujos origen–destino.\n- Capa contextual de sistemas de bicicleta pública del catálogo CRTM, integrada mediante matching validado.')
    st.markdown('### Definiciones')
    st.markdown('- **Recurrencia:** porcentaje de días elegibles en los que aparece una ruta.\n- **Intensidad:** volumen observado en una combinación de día y hora.\n- **Balance:** llegadas − salidas.\n- **Persistencia:** proporción de días observados con el signo del balance definido.')
    st.markdown('### Limitaciones')
    st.markdown('- Periodos y coberturas diferentes entre datasets.\n- Recurrencia no equivale a intensidad.\n- Balance de flujo no es inventario.\n- La cobertura de diagnosis simultánea de origen y destino es limitada.\n- Redistribución es una hipótesis exploratoria, no recomendación operativa.')
    st.subheader('CSV locales detectados')
    files=[]
    for r in (DATA,ANALYSIS):
        if r.exists():
            files += [{'Ruta':str(p.relative_to(ROOT)),'Tamaño MB':round(p.stat().st_size/1024**2,3)} for p in r.rglob('*.csv')]
    if files:st.dataframe(pd.DataFrame(files).sort_values('Ruta'),use_container_width=True)
    else:st.error('No encuentro data/processed ni analysis junto al dashboard.')
