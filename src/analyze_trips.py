import pandas as pd
from pathlib import Path

FILE = Path("data/processed/trips_2022_2023.csv")
OUT = Path("data/processed")
CHUNK_SIZE = 200_000

OUT.mkdir(parents=True, exist_ok=True)

monthly = {}
weekday = {}
hourly = {}

departures = {}
arrivals = {}

duration_count = 0
duration_sum = 0.0
duration_min = float("inf")
duration_max = float("-inf")
duration_excluded = 0

weekday_names = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

total = 0

print("ANÁLISIS EXPLORATORIO DE BiciMAD")
print("Procesando por bloques para evitar cargar el archivo completo...\n")

for chunk in pd.read_csv(
    FILE,
    chunksize=CHUNK_SIZE,
    encoding="utf-8-sig",
    dtype=str
):
    total += len(chunk)

    # -----------------------
    # FECHAS
    # -----------------------
    dates = pd.to_datetime(chunk["date"], errors="coerce")

    # Demanda mensual
    months = dates.dt.to_period("M").astype(str)
    for key, value in months.value_counts().items():
        monthly[key] = monthly.get(key, 0) + int(value)

    # Demanda por día de la semana
    days = dates.dt.dayofweek.map(weekday_names)
    for key, value in days.value_counts().items():
        weekday[key] = weekday.get(key, 0) + int(value)

    # -----------------------
    # DEMANDA POR HORA
    # -----------------------
    unlock_times = pd.to_datetime(
        chunk["unlock_date"],
        errors="coerce"
    )

    hours = unlock_times.dt.hour

    for key, value in hours.value_counts().items():
        hourly[int(key)] = hourly.get(int(key), 0) + int(value)

    # -----------------------
    # ESTACIONES
    # -----------------------
    origin_id = chunk["station_unlock"].fillna("").str.strip()
    origin_name = chunk["unlock_station_name"].fillna("").str.strip()

    destination_id = chunk["station_lock"].fillna("").str.strip()
    destination_name = chunk["lock_station_name"].fillna("").str.strip()

    origin_df = pd.DataFrame({
        "station_id": origin_id,
        "station_name": origin_name
    })

    destination_df = pd.DataFrame({
        "station_id": destination_id,
        "station_name": destination_name
    })

    origin_counts = origin_df.groupby(
        ["station_id", "station_name"]
    ).size()

    destination_counts = destination_df.groupby(
        ["station_id", "station_name"]
    ).size()

    for (station_id, station_name), count in origin_counts.items():
        key = (station_id, station_name)
        departures[key] = departures.get(key, 0) + int(count)

    for (station_id, station_name), count in destination_counts.items():
        key = (station_id, station_name)
        arrivals[key] = arrivals.get(key, 0) + int(count)

    # -----------------------
    # DURACIÓN: FILTRO
    # -----------------------
    duration = pd.to_numeric(
        chunk["trip_minutes"],
        errors="coerce"
    )

    valid_duration = duration[
        (duration > 0) & (duration <= 120)
    ]

    duration_excluded += (
        duration.isna().sum()
        + (duration <= 0).sum()
        + (duration > 120).sum()
    )

    duration_count += len(valid_duration)

    if len(valid_duration) > 0:
        duration_sum += valid_duration.sum()
        duration_min = min(duration_min, valid_duration.min())
        duration_max = max(duration_max, valid_duration.max())

    print(f"Procesados: {total:,} viajes")


# =========================================================
# EXPORTAR RESULTADOS
# =========================================================

print("\nExportando resultados...")

# 1. Mensual
monthly_df = pd.DataFrame(
    sorted(monthly.items()),
    columns=["month", "trips"]
)

monthly_df.to_csv(
    OUT / "demand_monthly.csv",
    index=False,
    encoding="utf-8-sig"
)

# 2. Día de la semana
weekday_order = [
    "Lunes", "Martes", "Miércoles", "Jueves",
    "Viernes", "Sábado", "Domingo"
]

weekday_df = pd.DataFrame({
    "weekday": weekday_order,
    "trips": [weekday.get(day, 0) for day in weekday_order]
})

weekday_df.to_csv(
    OUT / "demand_weekday.csv",
    index=False,
    encoding="utf-8-sig"
)

# 3. Hora
hourly_df = pd.DataFrame({
    "hour": list(range(24)),
    "trips": [hourly.get(hour, 0) for hour in range(24)]
})

hourly_df.to_csv(
    OUT / "demand_hourly.csv",
    index=False,
    encoding="utf-8-sig"
)

# 4 y 5. Estaciones
all_station_keys = set(departures) | set(arrivals)

station_rows = []

for station_id, station_name in all_station_keys:
    dep = departures.get((station_id, station_name), 0)
    arr = arrivals.get((station_id, station_name), 0)

    station_rows.append({
        "station_id": station_id,
        "station_name": station_name,
        "departures": dep,
        "arrivals": arr,
        "total_activity": dep + arr,
        "balance_arrivals_minus_departures": arr - dep,
        "absolute_imbalance": abs(arr - dep)
    })

stations_df = pd.DataFrame(station_rows)

stations_df = stations_df.sort_values(
    "total_activity",
    ascending=False
)

stations_df.to_csv(
    OUT / "station_demand_balance.csv",
    index=False,
    encoding="utf-8-sig"
)

# Ranking de salidas
stations_df.sort_values(
    "departures",
    ascending=False
).to_csv(
    OUT / "stations_top_departures.csv",
    index=False,
    encoding="utf-8-sig"
)

# Ranking de llegadas
stations_df.sort_values(
    "arrivals",
    ascending=False
).to_csv(
    OUT / "stations_top_arrivals.csv",
    index=False,
    encoding="utf-8-sig"
)

# Ranking de desequilibrio
stations_df.sort_values(
    "absolute_imbalance",
    ascending=False
).to_csv(
    OUT / "stations_top_imbalance.csv",
    index=False,
    encoding="utf-8-sig"
)

# Estadísticas de duración
duration_summary = pd.DataFrame([{
    "valid_trips": duration_count,
    "excluded_duration_records": duration_excluded,
    "mean_duration_minutes": (
        duration_sum / duration_count
        if duration_count else None
    ),
    "min_duration_minutes": (
        duration_min if duration_count else None
    ),
    "max_duration_minutes": (
        duration_max if duration_count else None
    )
}])

duration_summary.to_csv(
    OUT / "duration_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

# =========================================================
# RESUMEN EN TERMINAL
# =========================================================

print("\n" + "=" * 60)
print("ANÁLISIS TERMINADO")
print("=" * 60)

print(f"Total viajes analizados: {total:,}")

print("\nMES CON MAYOR DEMANDA:")
print(monthly_df.sort_values(
    "trips", ascending=False
).head(3).to_string(index=False))

print("\nDÍAS DE LA SEMANA:")
print(weekday_df.to_string(index=False))

print("\nHORAS CON MAYOR DEMANDA:")
print(hourly_df.sort_values(
    "trips", ascending=False
).head(5).to_string(index=False))

print("\nTOP 10 ESTACIONES POR ACTIVIDAD:")
print(stations_df.head(10).to_string(index=False))

print("\nTOP 10 DESEQUILIBRIO:")
print(stations_df.sort_values(
    "absolute_imbalance", ascending=False
).head(10).to_string(index=False))

print("\nDURACIONES FILTRADAS:")
print(duration_summary.to_string(index=False))

print("\nArchivos generados en data/processed/")