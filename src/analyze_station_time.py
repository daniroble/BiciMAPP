import pandas as pd
from pathlib import Path

INPUT = Path("data/processed/trips_2022_2023.csv")
OUTPUT = Path("data/processed/station_time_imbalance.csv")

CHUNK_SIZE = 200_000

weekday_map = {
    0: "Lunes",
    1: "Martes",
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
    6: "Domingo",
}

partials = []
total_rows = 0
valid_trips = 0

print("Analizando salidas y llegadas por estacion, dia y hora...")

for chunk in pd.read_csv(
    INPUT,
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    total_rows += len(chunk)

    # Convert station IDs to numeric
    chunk["station_unlock"] = pd.to_numeric(
        chunk["station_unlock"], errors="coerce"
    )

    chunk["station_lock"] = pd.to_numeric(
        chunk["station_lock"], errors="coerce"
    )

    # Parse timestamps
    chunk["unlock_dt"] = pd.to_datetime(
        chunk["unlock_date"], errors="coerce"
    )

    chunk["lock_dt"] = pd.to_datetime(
        chunk["lock_date"], errors="coerce"
    )

    # Count valid trips
    valid_mask = (
        chunk["unlock_dt"].notna()
        & chunk["lock_dt"].notna()
        & chunk["station_unlock"].notna()
        & chunk["station_lock"].notna()
    )

    valid_trips += valid_mask.sum()

    # =========================
    # DEPARTURES
    # =========================

    departures = chunk.dropna(
        subset=["unlock_dt", "station_unlock"]
    ).copy()

    departures = departures[
        departures["station_unlock"] >= 0
    ]

    departures["weekday"] = (
        departures["unlock_dt"]
        .dt.day_of_week
        .map(weekday_map)
    )

    departures["hour"] = (
        departures["unlock_dt"].dt.hour
    )

    departures = departures[
        [
            "station_unlock",
            "unlock_station_name",
            "weekday",
            "hour",
        ]
    ]

    departures.columns = [
        "station_id",
        "station_name",
        "weekday",
        "hour",
    ]

    departures["departures"] = 1
    departures["arrivals"] = 0

    # =========================
    # ARRIVALS
    # =========================

    arrivals = chunk.dropna(
        subset=["lock_dt", "station_lock"]
    ).copy()

    arrivals = arrivals[
        arrivals["station_lock"] >= 0
    ]

    arrivals["weekday"] = (
        arrivals["lock_dt"]
        .dt.day_of_week
        .map(weekday_map)
    )

    arrivals["hour"] = (
        arrivals["lock_dt"].dt.hour
    )

    arrivals = arrivals[
        [
            "station_lock",
            "lock_station_name",
            "weekday",
            "hour",
        ]
    ]

    arrivals.columns = [
        "station_id",
        "station_name",
        "weekday",
        "hour",
    ]

    arrivals["departures"] = 0
    arrivals["arrivals"] = 1

    # =========================
    # COMBINE EVENTS
    # =========================

    events = pd.concat(
        [departures, arrivals],
        ignore_index=True
    )

    grouped = (
        events.groupby(
            [
                "station_id",
                "station_name",
                "weekday",
                "hour",
            ],
            dropna=False
        )
        .agg(
            departures=("departures", "sum"),
            arrivals=("arrivals", "sum"),
        )
        .reset_index()
    )

    partials.append(grouped)

    print(
        f"Processed rows: {total_rows:,}",
        end="\r"
    )


# =========================
# FINAL CONSOLIDATION
# =========================

print("\nConsolidating results...")

result = pd.concat(
    partials,
    ignore_index=True
)

result = (
    result.groupby(
        [
            "station_id",
            "station_name",
            "weekday",
            "hour",
        ],
        dropna=False
    )
    .agg(
        departures=("departures", "sum"),
        arrivals=("arrivals", "sum"),
    )
    .reset_index()
)

# Net balance: arrivals - departures
result["net_balance"] = (
    result["arrivals"] - result["departures"]
)

# Absolute imbalance
result["absolute_imbalance"] = (
    result["net_balance"].abs()
)

# Total station activity
result["total_activity"] = (
    result["arrivals"] + result["departures"]
)

# Sort by largest absolute imbalance
result = result.sort_values(
    "absolute_imbalance",
    ascending=False
)

# Save output
OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)


# =========================
# REPORT
# =========================

print("\n" + "=" * 60)
print("ANALYSIS COMPLETED")
print("=" * 60)

print(f"Rows processed: {total_rows:,}")
print(f"Trips with valid timestamps and stations: {valid_trips:,}")
print(f"Station-day-hour combinations: {len(result):,}")
print(f"Output file: {OUTPUT}")

columns = [
    "station_id",
    "station_name",
    "weekday",
    "hour",
    "departures",
    "arrivals",
    "net_balance",
    "absolute_imbalance",
    "total_activity",
]

print("\nTOP 20 ABSOLUTE IMBALBANCES:")

print(
    result.head(20)[columns].to_string(index=False)
)

print("\nTOP 20 POSITIVE BALANCES:")

print(
    result.sort_values(
        "net_balance",
        ascending=False
    ).head(20)[columns].to_string(index=False)
)

print("\nTOP 20 NEGATIVE BALANCES:")

print(
    result.sort_values(
        "net_balance",
        ascending=True
    ).head(20)[columns].to_string(index=False)
)