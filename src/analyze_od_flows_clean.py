import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/processed/trips_2022_2023.csv")
OUTPUT_DIR = Path("data/processed/od_clean")

CHUNK_SIZE = 200_000

MORNING_HOURS = [7, 8, 9]

WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# ACCUMULATORS
# ============================================================

od_all = {}
od_by_hour = {}
od_by_weekday_hour = {}
od_daily = {}

station_departures = {}
station_arrivals = {}

same_station_total = 0
different_station_total = 0
morning_total = 0
weekday_morning_total = 0
records_processed = 0

# ============================================================
# HELPER
# ============================================================

def add_to_dict(dictionary, key, value):
    dictionary[key] = dictionary.get(key, 0) + int(value)


def station_name(value):
    if pd.isna(value):
        return "Unknown"
    return str(value)


print("=" * 60)
print("CLEAN OD ANALYSIS")
print("=" * 60)
print("Input:", INPUT_FILE)


# ============================================================
# READ DATA IN CHUNKS
# ============================================================

for chunk in pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    records_processed += len(chunk)

    # Parse timestamps
    chunk["unlock_date"] = pd.to_datetime(
        chunk["unlock_date"],
        errors="coerce"
    )

    # Clean station IDs
    chunk["station_unlock"] = pd.to_numeric(
        chunk["station_unlock"],
        errors="coerce"
    )

    chunk["station_lock"] = pd.to_numeric(
        chunk["station_lock"],
        errors="coerce"
    )

    # Remove records without usable information
    chunk = chunk.dropna(
        subset=[
            "unlock_date",
            "station_unlock",
            "station_lock"
        ]
    )

    # Extract temporal information
    chunk["hour"] = chunk["unlock_date"].dt.hour
    chunk["date"] = chunk["unlock_date"].dt.date
    chunk["weekday"] = chunk["unlock_date"].dt.dayofweek

    # Morning filter: 07, 08, 09
    morning = chunk[
        chunk["hour"].isin(MORNING_HOURS)
    ].copy()

    morning_total += len(morning)

    # --------------------------------------------------------
    # IDENTIFY SAME-STATION TRIPS
    # --------------------------------------------------------

    same_station = (
        morning["station_unlock"]
        == morning["station_lock"]
    )

    same_station_total += int(same_station.sum())

    # Only trips between different stations
    valid_od = morning[
        morning["station_unlock"]
        != morning["station_lock"]
    ].copy()

    different_station_total += len(valid_od)

    # --------------------------------------------------------
    # WEEKDAY FILTER
    # --------------------------------------------------------

    weekday_data = valid_od[
        valid_od["weekday"] < 5
    ].copy()

    weekday_morning_total += len(weekday_data)

    # --------------------------------------------------------
    # 1. TOTAL OD FLOWS
    # --------------------------------------------------------

    grouped = valid_od.groupby(
        [
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped.items():
        add_to_dict(od_all, key, count)

    # --------------------------------------------------------
    # 2. OD FLOWS BY HOUR
    # --------------------------------------------------------

    grouped_hour = valid_od.groupby(
        [
            "hour",
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped_hour.items():
        add_to_dict(od_by_hour, key, count)

    # --------------------------------------------------------
    # 3. OD FLOWS BY WEEKDAY AND HOUR
    # --------------------------------------------------------

    grouped_weekday_hour = weekday_data.groupby(
        [
            "weekday",
            "hour",
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped_weekday_hour.items():
        add_to_dict(
            od_by_weekday_hour,
            key,
            count
        )

    # --------------------------------------------------------
    # 4. DAILY OD FLOWS
    # Used to measure route recurrence
    # --------------------------------------------------------

    grouped_daily = valid_od.groupby(
        [
            "date",
            "weekday",
            "hour",
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped_daily.items():
        add_to_dict(od_daily, key, count)

    # --------------------------------------------------------
    # 5. STATION DEPARTURES
    # --------------------------------------------------------

    grouped_departures = valid_od.groupby(
        [
            "station_unlock",
            "unlock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped_departures.items():
        add_to_dict(
            station_departures,
            key,
            count
        )

    # --------------------------------------------------------
    # 6. STATION ARRIVALS
    # --------------------------------------------------------

    grouped_arrivals = valid_od.groupby(
        [
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped_arrivals.items():
        add_to_dict(
            station_arrivals,
            key,
            count
        )

    print(
        f"Processed {records_processed:,} records"
    )


# ============================================================
# EXPORT 1: TOTAL OD FLOWS
# ============================================================

od_total_df = pd.DataFrame(
    [
        {
            "origin_id": key[0],
            "origin_name": key[1],
            "destination_id": key[2],
            "destination_name": key[3],
            "trips": value
        }
        for key, value in od_all.items()
    ]
)

od_total_df = od_total_df.sort_values(
    "trips",
    ascending=False
)

od_total_df.to_csv(
    OUTPUT_DIR / "od_morning_different_stations.csv",
    index=False
)


# ============================================================
# EXPORT 2: OD BY HOUR
# ============================================================

od_hour_df = pd.DataFrame(
    [
        {
            "hour": key[0],
            "origin_id": key[1],
            "origin_name": key[2],
            "destination_id": key[3],
            "destination_name": key[4],
            "trips": value
        }
        for key, value in od_by_hour.items()
    ]
)

od_hour_df = od_hour_df.sort_values(
    ["hour", "trips"],
    ascending=[True, False]
)

od_hour_df.to_csv(
    OUTPUT_DIR / "od_morning_by_hour.csv",
    index=False
)


# ============================================================
# EXPORT 3: OD BY WEEKDAY AND HOUR
# ============================================================

od_weekday_hour_df = pd.DataFrame(
    [
        {
            "weekday": key[0],
            "weekday_name": WEEKDAY_NAMES[key[0]],
            "hour": key[1],
            "origin_id": key[2],
            "origin_name": key[3],
            "destination_id": key[4],
            "destination_name": key[5],
            "trips": value
        }
        for key, value in od_by_weekday_hour.items()
    ]
)

od_weekday_hour_df = od_weekday_hour_df.sort_values(
    ["weekday", "hour", "trips"],
    ascending=[True, True, False]
)

od_weekday_hour_df.to_csv(
    OUTPUT_DIR / "od_morning_weekday_hour.csv",
    index=False
)


# ============================================================
# EXPORT 4: ROUTE RECURRENCE
# ============================================================

daily_df = pd.DataFrame(
    [
        {
            "date": key[0],
            "weekday": key[1],
            "weekday_name": WEEKDAY_NAMES[key[1]],
            "hour": key[2],
            "origin_id": key[3],
            "origin_name": key[4],
            "destination_id": key[5],
            "destination_name": key[6],
            "trips": value
        }
        for key, value in od_daily.items()
    ]
)

# Only weekdays for the recurrent commuter-route analysis
daily_weekdays = daily_df[
    daily_df["weekday"] < 5
].copy()

recurrence_df = daily_weekdays.groupby(
    [
        "weekday",
        "weekday_name",
        "hour",
        "origin_id",
        "origin_name",
        "destination_id",
        "destination_name"
    ],
    dropna=False
).agg(
    active_days=("date", "nunique"),
    total_trips=("trips", "sum"),
    average_trips_per_active_day=("trips", "mean"),
    max_trips_in_one_day=("trips", "max")
).reset_index()

recurrence_df = recurrence_df.sort_values(
    [
        "active_days",
        "total_trips"
    ],
    ascending=False
)

recurrence_df.to_csv(
    OUTPUT_DIR / "od_route_recurrence_weekdays.csv",
    index=False
)


# ============================================================
# EXPORT 5: STATION DEPARTURES
# ============================================================

departure_df = pd.DataFrame(
    [
        {
            "station_id": key[0],
            "station_name": key[1],
            "morning_departures": value
        }
        for key, value in station_departures.items()
    ]
)

departure_df = departure_df.sort_values(
    "morning_departures",
    ascending=False
)

departure_df.to_csv(
    OUTPUT_DIR / "station_morning_departures_clean.csv",
    index=False
)


# ============================================================
# EXPORT 6: STATION ARRIVALS
# ============================================================

arrival_df = pd.DataFrame(
    [
        {
            "station_id": key[0],
            "station_name": key[1],
            "morning_arrivals": value
        }
        for key, value in station_arrivals.items()
    ]
)

arrival_df = arrival_df.sort_values(
    "morning_arrivals",
    ascending=False
)

arrival_df.to_csv(
    OUTPUT_DIR / "station_morning_arrivals_clean.csv",
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("ANALYSIS FINISHED")
print("=" * 60)

print(f"Records processed: {records_processed:,}")
print(f"Morning trips (07-09): {morning_total:,}")
print(f"Same-station trips: {same_station_total:,}")
print(f"Different-station trips: {different_station_total:,}")
print(f"Weekday morning different-station trips: {weekday_morning_total:,}")

if morning_total > 0:
    same_station_percentage = (
        same_station_total / morning_total * 100
    )

    print(
        f"Same-station trips percentage: "
        f"{same_station_percentage:.2f}%"
    )

print(f"Unique valid OD routes: {len(od_total_df):,}")

print("\nTOP 20 VALID MORNING ROUTES:")

print(
    od_total_df.head(20)[
        [
            "origin_name",
            "destination_name",
            "trips"
        ]
    ].to_string(index=False)
)

print("\nTOP 20 WEEKDAY ROUTES:")

weekday_top = (
    od_weekday_hour_df
    .groupby(
        [
            "origin_name",
            "destination_name"
        ]
    )["trips"]
    .sum()
    .reset_index()
    .sort_values(
        "trips",
        ascending=False
    )
)

print(
    weekday_top.head(20).to_string(index=False)
)

print("\nTOP 20 RECURRENT ROUTES:")

print(
    recurrence_df.head(20)[
        [
            "weekday_name",
            "hour",
            "origin_name",
            "destination_name",
            "active_days",
            "total_trips",
            "average_trips_per_active_day"
        ]
    ].to_string(index=False)
)

print("\nFILES GENERATED:")
print("- od_morning_different_stations.csv")
print("- od_morning_by_hour.csv")
print("- od_morning_weekday_hour.csv")
print("- od_route_recurrence_weekdays.csv")
print("- station_morning_departures_clean.csv")
print("- station_morning_arrivals_clean.csv")

print("\nOutput folder:", OUTPUT_DIR)