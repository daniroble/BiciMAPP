import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/processed/trips_2022_2023.csv")
OUTPUT_DIR = Path("data/processed/od")

CHUNK_SIZE = 200_000

# Morning period: 07:00-09:59
MORNING_HOURS = [7, 8, 9]

# ============================================================
# PREPARATION
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

od_total = {}
od_weekday = {}
od_hour = {}
station_departures = {}
station_arrivals = {}

total_processed = 0
morning_trips = 0
weekday_morning_trips = 0


def add_counts(dictionary, key, value=1):
    dictionary[key] = dictionary.get(key, 0) + value


print("Starting OD analysis...")
print(f"Input: {INPUT_FILE}")


# ============================================================
# PROCESS DATA IN CHUNKS
# ============================================================

for chunk in pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    total_processed += len(chunk)

    # Parse departure timestamp
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

    # Remove records without usable timestamp or station IDs
    chunk = chunk.dropna(
        subset=[
            "unlock_date",
            "station_unlock",
            "station_lock"
        ]
    )

    # Extract temporal variables
    chunk["hour"] = chunk["unlock_date"].dt.hour
    chunk["weekday"] = chunk["unlock_date"].dt.dayofweek

    # Morning filter
    morning = chunk[
        chunk["hour"].isin(MORNING_HOURS)
    ].copy()

    morning_trips += len(morning)

    # --------------------------------------------------------
    # ALL MORNING OD FLOWS
    # --------------------------------------------------------

    grouped = morning.groupby(
        [
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in grouped.items():
        add_counts(od_total, key, int(count))

    # --------------------------------------------------------
    # MORNING OD BY WEEKDAY
    # --------------------------------------------------------

    weekdays = morning[
        morning["weekday"] < 5
    ].copy()

    weekday_morning_trips += len(weekdays)

    grouped_weekday = weekdays.groupby(
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

    for key, count in grouped_weekday.items():
        add_counts(od_weekday, key, int(count))

    # --------------------------------------------------------
    # MORNING OD BY HOUR
    # --------------------------------------------------------

    grouped_hour = morning.groupby(
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
        add_counts(od_hour, key, int(count))

    # --------------------------------------------------------
    # STATION DEPARTURES
    # --------------------------------------------------------

    departures = morning.groupby(
        [
            "station_unlock",
            "unlock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in departures.items():
        add_counts(station_departures, key, int(count))

    # --------------------------------------------------------
    # STATION ARRIVALS
    # --------------------------------------------------------

    arrivals = morning.groupby(
        [
            "station_lock",
            "lock_station_name"
        ],
        dropna=False
    ).size()

    for key, count in arrivals.items():
        add_counts(station_arrivals, key, int(count))

    print(f"Processed {total_processed:,} records")


# ============================================================
# EXPORT OD TOTAL
# ============================================================

od_df = pd.DataFrame(
    [
        {
            "origin_id": key[0],
            "origin_name": key[1],
            "destination_id": key[2],
            "destination_name": key[3],
            "trips": value
        }
        for key, value in od_total.items()
    ]
)

od_df = od_df.sort_values(
    "trips",
    ascending=False
)

od_df.to_csv(
    OUTPUT_DIR / "od_morning_total.csv",
    index=False
)


# ============================================================
# EXPORT OD BY WEEKDAY AND HOUR
# ============================================================

weekday_names = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

weekday_df = pd.DataFrame(
    [
        {
            "weekday": key[0],
            "weekday_name": weekday_names[key[0]],
            "hour": key[1],
            "origin_id": key[2],
            "origin_name": key[3],
            "destination_id": key[4],
            "destination_name": key[5],
            "trips": value
        }
        for key, value in od_weekday.items()
    ]
)

weekday_df = weekday_df.sort_values(
    "trips",
    ascending=False
)

weekday_df.to_csv(
    OUTPUT_DIR / "od_morning_weekday_hour.csv",
    index=False
)


# ============================================================
# EXPORT OD BY HOUR
# ============================================================

hour_df = pd.DataFrame(
    [
        {
            "hour": key[0],
            "origin_id": key[1],
            "origin_name": key[2],
            "destination_id": key[3],
            "destination_name": key[4],
            "trips": value
        }
        for key, value in od_hour.items()
    ]
)

hour_df = hour_df.sort_values(
    ["hour", "trips"],
    ascending=[True, False]
)

hour_df.to_csv(
    OUTPUT_DIR / "od_morning_hour.csv",
    index=False
)


# ============================================================
# EXPORT STATION DEPARTURES
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
    OUTPUT_DIR / "station_morning_departures.csv",
    index=False
)


# ============================================================
# EXPORT STATION ARRIVALS
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
    OUTPUT_DIR / "station_morning_arrivals.csv",
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 50)
print("OD ANALYSIS FINISHED")
print("=" * 50)

print(f"Total records processed: {total_processed:,}")
print(f"Morning trips (07-09): {morning_trips:,}")
print(f"Weekday morning trips: {weekday_morning_trips:,}")
print(f"Unique OD connections: {len(od_df):,}")

print("\nTOP 15 MORNING ROUTES:")
print(
    od_df.head(15)[
        [
            "origin_name",
            "destination_name",
            "trips"
        ]
    ].to_string(index=False)
)

print("\nFiles generated:")
print("- od_morning_total.csv")
print("- od_morning_weekday_hour.csv")
print("- od_morning_hour.csv")
print("- station_morning_departures.csv")
print("- station_morning_arrivals.csv")

print("\nOutput directory:", OUTPUT_DIR)