import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/processed/trips_2022_2023.csv")
OUTPUT_DIR = Path("data/processed/od_clean")

CHUNK_SIZE = 200_000

MORNING_HOURS = [7, 8, 9]
MIN_ACTIVE_DAYS = 15

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

# Route key:
# weekday, hour, origin_id, origin_name, destination_id, destination_name
#
# Values:
# total_trips
# active_dates

route_data = {}

# Calendar denominator:
# key = weekday, hour
# value = dates when data exists for that weekday/hour

eligible_dates = {}

records_processed = 0
morning_trips = 0
valid_different_station_trips = 0

# ============================================================
# PROCESS DATA IN CHUNKS
# ============================================================

print("=" * 60)
print("NORMALIZED OD RECURRENCE ANALYSIS")
print("=" * 60)

for chunk in pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    records_processed += len(chunk)

    # --------------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------------

    chunk["unlock_date"] = pd.to_datetime(
        chunk["unlock_date"],
        errors="coerce"
    )

    chunk["station_unlock"] = pd.to_numeric(
        chunk["station_unlock"],
        errors="coerce"
    )

    chunk["station_lock"] = pd.to_numeric(
        chunk["station_lock"],
        errors="coerce"
    )

    chunk = chunk.dropna(
        subset=[
            "unlock_date",
            "station_unlock",
            "station_lock"
        ]
    )

    # --------------------------------------------------------
    # TEMPORAL VARIABLES
    # --------------------------------------------------------

    chunk["date"] = chunk["unlock_date"].dt.date
    chunk["hour"] = chunk["unlock_date"].dt.hour
    chunk["weekday"] = chunk["unlock_date"].dt.dayofweek

    # --------------------------------------------------------
    # MORNING FILTER
    # --------------------------------------------------------

    morning = chunk[
        chunk["hour"].isin(MORNING_HOURS)
    ].copy()

    morning_trips += len(morning)

    # --------------------------------------------------------
    # CALENDAR DENOMINATOR
    #
    # Count dates with data for each weekday/hour.
    # This is done BEFORE removing same-station trips.
    # --------------------------------------------------------

    calendar_groups = morning.groupby(
        [
            "weekday",
            "hour",
            "date"
        ],
        dropna=False
    ).size()

    for key in calendar_groups.index:

        weekday = key[0]
        hour = key[1]
        date = key[2]

        calendar_key = (
            weekday,
            hour
        )

        if calendar_key not in eligible_dates:
            eligible_dates[calendar_key] = set()

        eligible_dates[calendar_key].add(date)

    # --------------------------------------------------------
    # REMOVE SAME-STATION TRIPS
    # --------------------------------------------------------

    morning = morning[
        morning["station_unlock"]
        != morning["station_lock"]
    ].copy()

    valid_different_station_trips += len(morning)

    # --------------------------------------------------------
    # WEEKDAYS ONLY
    # --------------------------------------------------------

    weekdays = morning[
        morning["weekday"] < 5
    ].copy()

    # --------------------------------------------------------
    # GROUP BY ROUTE + WEEKDAY + HOUR + DATE
    # --------------------------------------------------------

    grouped = weekdays.groupby(
        [
            "weekday",
            "hour",
            "station_unlock",
            "unlock_station_name",
            "station_lock",
            "lock_station_name",
            "date"
        ],
        dropna=False
    ).size()

    # --------------------------------------------------------
    # ACCUMULATE ROUTE DATA
    # --------------------------------------------------------

    for key, count in grouped.items():

        weekday = key[0]
        hour = key[1]

        origin_id = key[2]
        origin_name = key[3]

        destination_id = key[4]
        destination_name = key[5]

        date = key[6]

        route_key = (
            weekday,
            hour,
            origin_id,
            origin_name,
            destination_id,
            destination_name
        )

        if route_key not in route_data:

            route_data[route_key] = {
                "total_trips": 0,
                "active_dates": set()
            }

        route_data[route_key]["total_trips"] += int(count)

        route_data[route_key]["active_dates"].add(date)

    print(
        f"Processed {records_processed:,} records"
    )


# ============================================================
# BUILD RECURRENCE METRICS
# ============================================================

rows = []

for key, values in route_data.items():

    weekday = key[0]
    hour = key[1]

    origin_id = key[2]
    origin_name = key[3]

    destination_id = key[4]
    destination_name = key[5]

    total_trips = values["total_trips"]

    active_days = len(
        values["active_dates"]
    )

    calendar_key = (
        weekday,
        hour
    )

    eligible_days = len(
        eligible_dates.get(
            calendar_key,
            set()
        )
    )

    if eligible_days == 0:
        continue

    recurrence_pct = (
        active_days
        / eligible_days
        * 100
    )

    avg_trips_per_eligible_day = (
        total_trips
        / eligible_days
    )

    avg_trips_per_active_day = (
        total_trips
        / active_days
        if active_days > 0
        else 0
    )

    rows.append(
        {
            "weekday": weekday,
            "weekday_name": WEEKDAY_NAMES[weekday],
            "hour": hour,

            "origin_id": origin_id,
            "origin_name": origin_name,

            "destination_id": destination_id,
            "destination_name": destination_name,

            "total_trips": total_trips,

            "active_days": active_days,
            "eligible_days": eligible_days,

            "recurrence_pct": recurrence_pct,

            "avg_trips_per_eligible_day":
                avg_trips_per_eligible_day,

            "avg_trips_per_active_day":
                avg_trips_per_active_day
        }
    )


# ============================================================
# CREATE DATAFRAME
# ============================================================

recurrence_df = pd.DataFrame(rows)


# ============================================================
# FILTER ROUTES WITH MINIMUM EVIDENCE
# ============================================================

recurrence_filtered = recurrence_df[
    recurrence_df["active_days"] >= MIN_ACTIVE_DAYS
].copy()


# ============================================================
# CREATE RANKINGS
# ============================================================

# Ranking A: recurrence percentage
rank_recurrence = recurrence_filtered.sort_values(
    [
        "recurrence_pct",
        "total_trips"
    ],
    ascending=False
)

# Ranking B: average demand per eligible calendar day
rank_daily_demand = recurrence_filtered.sort_values(
    [
        "avg_trips_per_eligible_day",
        "total_trips"
    ],
    ascending=False
)

# Ranking C: total number of trips
rank_total = recurrence_filtered.sort_values(
    "total_trips",
    ascending=False
)


# ============================================================
# EXPORT FILES
# ============================================================

recurrence_df.to_csv(
    OUTPUT_DIR / "od_recurrence_all.csv",
    index=False
)

recurrence_filtered.to_csv(
    OUTPUT_DIR / "od_recurrence_filtered.csv",
    index=False
)

rank_recurrence.to_csv(
    OUTPUT_DIR / "od_recurrence_rank.csv",
    index=False
)

rank_daily_demand.to_csv(
    OUTPUT_DIR / "od_daily_demand_rank.csv",
    index=False
)

rank_total.to_csv(
    OUTPUT_DIR / "od_total_demand_rank.csv",
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("RECURRENCE ANALYSIS FINISHED")
print("=" * 60)

print(f"Records processed: {records_processed:,}")
print(f"Morning trips: {morning_trips:,}")

print(
    "Morning trips between different stations: "
    f"{valid_different_station_trips:,}"
)

print(
    "Route-weekday-hour combinations: "
    f"{len(recurrence_df):,}"
)

print(
    "Combinations after minimum active-days filter: "
    f"{len(recurrence_filtered):,}"
)


# ------------------------------------------------------------
# AVAILABLE DAYS BY WEEKDAY AND HOUR
# ------------------------------------------------------------

print("\nAVAILABLE DAYS BY WEEKDAY AND HOUR:")

for key, dates in sorted(
    eligible_dates.items()
):

    weekday = key[0]
    hour = key[1]

    print(
        f"{WEEKDAY_NAMES[weekday]} "
        f"{hour}:00 - "
        f"{len(dates)} days"
    )


# ------------------------------------------------------------
# TOP 20 RECURRENT ROUTES
# ------------------------------------------------------------

print("\n")
print("=" * 60)
print("TOP 20 ROUTES BY RECURRENCE")
print("=" * 60)

print(
    rank_recurrence.head(20)[
        [
            "weekday_name",
            "hour",
            "origin_name",
            "destination_name",
            "active_days",
            "eligible_days",
            "recurrence_pct",
            "total_trips",
            "avg_trips_per_eligible_day"
        ]
    ].to_string(index=False)
)


# ------------------------------------------------------------
# TOP 20 BY DAILY DEMAND
# ------------------------------------------------------------

print("\n")
print("=" * 60)
print("TOP 20 ROUTES BY DAILY DEMAND")
print("=" * 60)

print(
    rank_daily_demand.head(20)[
        [
            "weekday_name",
            "hour",
            "origin_name",
            "destination_name",
            "active_days",
            "eligible_days",
            "recurrence_pct",
            "total_trips",
            "avg_trips_per_eligible_day"
        ]
    ].to_string(index=False)
)


# ------------------------------------------------------------
# TOP 20 BY TOTAL TRIPS
# ------------------------------------------------------------

print("\n")
print("=" * 60)
print("TOP 20 ROUTES BY TOTAL TRIPS")
print("=" * 60)

print(
    rank_total.head(20)[
        [
            "weekday_name",
            "hour",
            "origin_name",
            "destination_name",
            "active_days",
            "eligible_days",
            "recurrence_pct",
            "total_trips"
        ]
    ].to_string(index=False)
)


# ============================================================
# FILES GENERATED
# ============================================================

print("\nFILES GENERATED:")

print("- od_recurrence_all.csv")
print("- od_recurrence_filtered.csv")
print("- od_recurrence_rank.csv")
print("- od_daily_demand_rank.csv")
print("- od_total_demand_rank.csv")

print("\nOutput folder:")
print(OUTPUT_DIR)