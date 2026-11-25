import pandas as pd
from pathlib import Path

FILE = Path("data/processed/trips_2022_2023.csv")
CHUNK_SIZE = 200_000

total_rows = 0
missing_values = {}
invalid_dates = 0
negative_duration = 0
zero_duration = 0
duration_over_120 = 0
duration_sum = 0
duration_count = 0
duration_min = float("inf")
duration_max = float("-inf")
duplicates_in_chunks = 0

monthly_counts = {}
origin_stations = set()
destination_stations = set()

print("INICIANDO AUDITORÍA...")
print(f"Archivo: {FILE}")
print(f"Tamaño: {FILE.stat().st_size / 1024 / 1024:.2f} MB\n")

for chunk in pd.read_csv(
    FILE,
    chunksize=CHUNK_SIZE,
    encoding="utf-8-sig",
    dtype=str
):
    rows = len(chunk)
    total_rows += rows

    # Valores ausentes
    for col in chunk.columns:
        missing_values[col] = (
            missing_values.get(col, 0)
            + chunk[col].isna().sum()
            + (chunk[col].str.strip() == "").sum()
        )

    # Fechas
    dates = pd.to_datetime(chunk["date"], errors="coerce")
    invalid_dates += dates.isna().sum()

    valid_dates = dates.dropna()
    months = valid_dates.dt.to_period("M").astype(str)

    counts = months.value_counts()
    for month, count in counts.items():
        monthly_counts[month] = monthly_counts.get(month, 0) + int(count)

    # Duraciones
    durations = pd.to_numeric(chunk["trip_minutes"], errors="coerce")
    valid_duration = durations.dropna()

    duration_count += len(valid_duration)
    duration_sum += valid_duration.sum()

    if len(valid_duration):
        duration_min = min(duration_min, valid_duration.min())
        duration_max = max(duration_max, valid_duration.max())

    negative_duration += (durations < 0).sum()
    zero_duration += (durations == 0).sum()
    duration_over_120 += (durations > 120).sum()

    # Estaciones
    origin_stations.update(
        chunk["station_unlock"].dropna().unique()
    )
    destination_stations.update(
        chunk["station_lock"].dropna().unique()
    )

    # Duplicados dentro de cada chunk
    duplicates_in_chunks += chunk.duplicated().sum()

    print(f"Auditados: {total_rows:,} registros")


print("\n" + "=" * 60)
print("RESULTADOS DE AUDITORÍA")
print("=" * 60)

print(f"\nTotal de registros: {total_rows:,}")
print(f"Fechas inválidas: {invalid_dates:,}")
print(f"Duraciones negativas: {negative_duration:,}")
print(f"Duraciones iguales a cero: {zero_duration:,}")
print(f"Duraciones >120 minutos: {duration_over_120:,}")
print(f"Duplicados dentro de chunks: {duplicates_in_chunks:,}")

if duration_count:
    print(f"\nDuración mínima: {duration_min:.2f} min")
    print(f"Duración máxima: {duration_max:.2f} min")
    print(f"Duración media: {duration_sum / duration_count:.2f} min")

print(f"\nEstaciones únicas de origen: {len(origin_stations)}")
print(f"Estaciones únicas de destino: {len(destination_stations)}")

print("\nViajes por mes:")
for month in sorted(monthly_counts):
    print(f"{month}: {monthly_counts[month]:,}")

print("\nValores vacíos por columna:")
for col, count in missing_values.items():
    print(f"{col}: {count:,}")

print("\nAUDITORÍA FINALIZADA")