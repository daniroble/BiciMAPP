import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path("data/processed")

OD_FILE = BASE_DIR / "od_clean" / "od_recurrence_filtered.csv"

STATION_FILE = BASE_DIR / "station_time_recurrence.csv"

OUTPUT_DIR = BASE_DIR / "cross_analysis"

MIN_STATION_OBSERVED_DAYS = 20
MIN_OD_ACTIVE_DAYS = 15

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# HELPERS
# ============================================================

def find_column(df, possible_names, description):
    """
    Find a column using a list of possible names.
    """

    lower_map = {
        str(col).lower(): col
        for col in df.columns
    }

    for name in possible_names:

        if name.lower() in lower_map:
            return lower_map[name.lower()]

    raise ValueError(
        f"Could not find column for: {description}\n"
        f"Available columns:\n{list(df.columns)}"
    )


def normalize_weekday(value):

    weekday_map = {
        "monday": 0,
        "mon": 0,
        "martes": 1,
        "tuesday": 1,
        "tue": 1,
        "miércoles": 2,
        "miercoles": 2,
        "wednesday": 2,
        "wed": 2,
        "jueves": 3,
        "thursday": 3,
        "thu": 3,
        "viernes": 4,
        "friday": 4,
        "fri": 4,
        "sábado": 5,
        "sabado": 5,
        "saturday": 5,
        "sat": 5,
        "domingo": 6,
        "sunday": 6,
        "sun": 6
    }

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().lower()

    if text in weekday_map:
        return weekday_map[text]

    try:
        return int(float(text))
    except ValueError:
        return None


def clean_station_id(series):

    return pd.to_numeric(
        series,
        errors="coerce"
    )


def print_columns(title, df):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print("Columns:")
    print(list(df.columns))


# ============================================================
# LOAD FILES
# ============================================================

print("=" * 60)
print("CROSS STATION AND OD ANALYSIS")
print("=" * 60)

print("\nLoading files...")

od = pd.read_csv(
    OD_FILE,
    low_memory=False
)

stations = pd.read_csv(
    STATION_FILE,
    low_memory=False
)

print_columns("OD RECURRENCE FILE", od)
print_columns("STATION RECURRENCE FILE", stations)


# ============================================================
# MAP OD COLUMNS
# ============================================================

od_weekday_col = find_column(
    od,
    ["weekday", "weekday_num", "day_of_week"],
    "OD weekday"
)

od_hour_col = find_column(
    od,
    ["hour"],
    "OD hour"
)

od_origin_id_col = find_column(
    od,
    ["origin_id", "station_unlock", "origin_station_id"],
    "OD origin ID"
)

od_origin_name_col = find_column(
    od,
    ["origin_name", "unlock_station_name", "origin_station_name"],
    "OD origin name"
)

od_destination_id_col = find_column(
    od,
    ["destination_id", "station_lock", "destination_station_id"],
    "OD destination ID"
)

od_destination_name_col = find_column(
    od,
    ["destination_name", "lock_station_name", "destination_station_name"],
    "OD destination name"
)

od_active_days_col = find_column(
    od,
    ["active_days", "observed_days"],
    "OD active days"
)

od_total_trips_col = find_column(
    od,
    ["total_trips", "trips"],
    "OD total trips"
)

od_recurrence_col = find_column(
    od,
    ["recurrence_pct"],
    "OD recurrence percentage"
)

od_daily_demand_col = find_column(
    od,
    [
        "avg_trips_per_eligible_day",
        "average_trips_per_eligible_day"
    ],
    "OD average daily demand"
)


# ============================================================
# MAP STATION COLUMNS
# ============================================================

station_id_col = find_column(
    stations,
    ["station_id", "station_unlock", "id_station", "id"],
    "station ID"
)

station_name_col = find_column(
    stations,
    ["station_name", "unlock_station_name", "name"],
    "station name"
)

station_weekday_col = find_column(
    stations,
    ["weekday_num", "weekday", "day_of_week"],
    "station weekday"
)

station_hour_col = find_column(
    stations,
    ["hour"],
    "station hour"
)

station_observed_days_col = find_column(
    stations,
    ["observed_days", "active_days", "days_observed"],
    "station observed days"
)

station_balance_col = find_column(
    stations,
    ["avg_daily_balance", "avg_balance", "average_balance", "balance"],
    "station average balance"
)

station_departures_col = find_column(
    stations,
    ["avg_daily_departures", "avg_departures", "average_departures"],
    "average departures"
)
station_arrivals_col = find_column(
    stations,
    ["avg_daily_arrivals", "avg_arrivals", "average_arrivals"],
    "average arrivals"
)

# Optional positive/negative recurrence fields
positive_pct_col = None
negative_pct_col = None

for candidate in [
    "positive_days_pct",
    "positive_pct",
    "pct_positive"
]:

    if candidate in stations.columns:
        positive_pct_col = candidate
        break

for candidate in [
    "negative_days_pct",
    "negative_pct",
    "pct_negative"
]:

    if candidate in stations.columns:
        negative_pct_col = candidate
        break


# ============================================================
# STANDARDIZE OD DATA
# ============================================================

od_clean = od.copy()

od_clean["weekday_num"] = (
    od_clean[od_weekday_col]
    .apply(normalize_weekday)
)

od_clean["hour"] = pd.to_numeric(
    od_clean[od_hour_col],
    errors="coerce"
)

od_clean["origin_id"] = clean_station_id(
    od_clean[od_origin_id_col]
)

od_clean["destination_id"] = clean_station_id(
    od_clean[od_destination_id_col]
)

od_clean["origin_name"] = (
    od_clean[od_origin_name_col]
    .astype(str)
)

od_clean["destination_name"] = (
    od_clean[od_destination_name_col]
    .astype(str)
)

od_clean["active_days"] = pd.to_numeric(
    od_clean[od_active_days_col],
    errors="coerce"
)

od_clean["total_trips"] = pd.to_numeric(
    od_clean[od_total_trips_col],
    errors="coerce"
)

od_clean["route_recurrence_pct"] = pd.to_numeric(
    od_clean[od_recurrence_col],
    errors="coerce"
)

od_clean["avg_trips_per_eligible_day"] = pd.to_numeric(
    od_clean[od_daily_demand_col],
    errors="coerce"
)

od_clean = od_clean.dropna(
    subset=[
        "weekday_num",
        "hour",
        "origin_id",
        "destination_id"
    ]
)


# ============================================================
# STANDARDIZE STATION DATA
# ============================================================

station_clean = stations.copy()

station_clean["station_id_clean"] = clean_station_id(
    station_clean[station_id_col]
)

station_clean["weekday_num"] = (
    station_clean[station_weekday_col]
    .apply(normalize_weekday)
)

station_clean["hour"] = pd.to_numeric(
    station_clean[station_hour_col],
    errors="coerce"
)

station_clean["observed_days"] = pd.to_numeric(
    station_clean[station_observed_days_col],
    errors="coerce"
)

station_clean["avg_balance"] = pd.to_numeric(
    station_clean[station_balance_col],
    errors="coerce"
)

station_clean["avg_departures"] = pd.to_numeric(
    station_clean[station_departures_col],
    errors="coerce"
)

station_clean["avg_arrivals"] = pd.to_numeric(
    station_clean[station_arrivals_col],
    errors="coerce"
)

station_clean["station_name_clean"] = (
    station_clean[station_name_col]
    .astype(str)
)

if positive_pct_col is not None:

    station_clean["positive_days_pct"] = pd.to_numeric(
        station_clean[positive_pct_col],
        errors="coerce"
    )

else:

    station_clean["positive_days_pct"] = pd.NA


if negative_pct_col is not None:

    station_clean["negative_days_pct"] = pd.to_numeric(
        station_clean[negative_pct_col],
        errors="coerce"
    )

else:

    station_clean["negative_days_pct"] = pd.NA


station_clean = station_clean.dropna(
    subset=[
        "station_id_clean",
        "weekday_num",
        "hour",
        "avg_balance"
    ]
)


# ============================================================
# FILTER STATION EVIDENCE
# ============================================================

station_clean = station_clean[
    station_clean["observed_days"]
    >= MIN_STATION_OBSERVED_DAYS
].copy()


# ============================================================
# AGGREGATE DUPLICATE STATION KEYS
# ============================================================

station_agg = station_clean.groupby(
    [
        "station_id_clean",
        "weekday_num",
        "hour"
    ],
    dropna=False
).agg(
    station_name=("station_name_clean", "first"),

    observed_days=("observed_days", "max"),

    avg_balance=("avg_balance", "mean"),

    avg_departures=("avg_departures", "mean"),

    avg_arrivals=("avg_arrivals", "mean"),

    positive_days_pct=("positive_days_pct", "mean"),

    negative_days_pct=("negative_days_pct", "mean")
).reset_index()


# ============================================================
# CREATE ORIGIN STATION DATA
# ============================================================

origin_station = station_agg.rename(
    columns={
        "station_id_clean": "origin_id",
        "station_name": "origin_station_diagnosis",
        "avg_balance": "origin_avg_balance",
        "observed_days": "origin_observed_days",
        "avg_departures": "origin_avg_departures",
        "avg_arrivals": "origin_avg_arrivals",
        "positive_days_pct": "origin_positive_days_pct",
        "negative_days_pct": "origin_negative_days_pct"
    }
)


# ============================================================
# CREATE DESTINATION STATION DATA
# ============================================================

destination_station = station_agg.rename(
    columns={
        "station_id_clean": "destination_id",
        "station_name": "destination_station_diagnosis",
        "avg_balance": "destination_avg_balance",
        "observed_days": "destination_observed_days",
        "avg_departures": "destination_avg_departures",
        "avg_arrivals": "destination_avg_arrivals",
        "positive_days_pct": "destination_positive_days_pct",
        "negative_days_pct": "destination_negative_days_pct"
    }
)


# ============================================================
# CROSS OD WITH ORIGIN DIAGNOSIS
# ============================================================

cross = od_clean.merge(
    origin_station,
    on=[
        "origin_id",
        "weekday_num",
        "hour"
    ],
    how="left"
)


# ============================================================
# CROSS OD WITH DESTINATION DIAGNOSIS
# ============================================================

cross = cross.merge(
    destination_station,
    on=[
        "destination_id",
        "weekday_num",
        "hour"
    ],
    how="left"
)


# ============================================================
# DEFINE MATCHING DIAGNOSIS
# ============================================================

cross["origin_station_diagnosed"] = (
    cross["origin_avg_balance"].notna()
)

cross["destination_station_diagnosed"] = (
    cross["destination_avg_balance"].notna()
)


# Origin: net departures if balance is negative
cross["origin_is_net_emitter"] = (
    cross["origin_avg_balance"] < 0
)

# Destination: net arrivals if balance is positive
cross["destination_is_net_receiver"] = (
    cross["destination_avg_balance"] > 0
)


# ============================================================
# IDENTIFY CANDIDATE CONNECTIONS
# ============================================================

cross["matches_emitter_to_receiver"] = (
    cross["origin_is_net_emitter"]
    & cross["destination_is_net_receiver"]
)


cross["origin_balance_magnitude"] = (
    cross["origin_avg_balance"].abs()
)

cross["destination_balance_magnitude"] = (
    cross["destination_avg_balance"].abs()
)


# ============================================================
# EXPORT FULL CROSS
# ============================================================

cross.to_csv(
    OUTPUT_DIR / "od_station_cross_all.csv",
    index=False
)


# ============================================================
# CANDIDATE ROUTES
# ============================================================

candidates = cross[
    cross["matches_emitter_to_receiver"]
].copy()


# ============================================================
# TRANSPARENT RANKING
# ============================================================

# No artificial weighted score.
# Ranking is based on:
# 1. Route recurrence
# 2. Route trips
# 3. Origin imbalance magnitude
# 4. Destination imbalance magnitude

candidates = candidates.sort_values(
    [
        "route_recurrence_pct",
        "total_trips",
        "origin_balance_magnitude",
        "destination_balance_magnitude"
    ],
    ascending=False
)


# ============================================================
# EXPORT CANDIDATES
# ============================================================

candidates.to_csv(
    OUTPUT_DIR / "od_emitter_receiver_candidates.csv",
    index=False
)


# ============================================================
# EXPORT RANKING BY ROUTE VOLUME
# ============================================================

candidates_by_volume = candidates.sort_values(
    [
        "total_trips",
        "route_recurrence_pct"
    ],
    ascending=False
)

candidates_by_volume.to_csv(
    OUTPUT_DIR / "od_emitter_receiver_by_volume.csv",
    index=False
)


# ============================================================
# EXPORT SUMMARY
# ============================================================

summary = cross.groupby(
    [
        "weekday_num",
        "hour"
    ]
).agg(
    total_routes=("total_trips", "count"),

    routes_with_origin_diagnosis=(
        "origin_station_diagnosed",
        "sum"
    ),

    routes_with_destination_diagnosis=(
        "destination_station_diagnosed",
        "sum"
    ),

    emitter_receiver_candidates=(
        "matches_emitter_to_receiver",
        "sum"
    ),

    total_trips=("total_trips", "sum")
).reset_index()


summary.to_csv(
    OUTPUT_DIR / "od_station_cross_summary.csv",
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 60)
print("CROSS ANALYSIS FINISHED")
print("=" * 60)

print(f"OD rows: {len(od_clean):,}")
print(f"Station diagnosis rows: {len(station_agg):,}")
print(f"Crossed rows: {len(cross):,}")

print(
    "Routes with origin diagnosis: "
    f"{cross['origin_station_diagnosed'].sum():,}"
)

print(
    "Routes with destination diagnosis: "
    f"{cross['destination_station_diagnosed'].sum():,}"
)

print(
    "Emitter-to-receiver candidate routes: "
    f"{len(candidates):,}"
)


print("\n")
print("=" * 60)
print("TOP 20 EMITTER-TO-RECEIVER CANDIDATES")
print("=" * 60)

columns_to_show = [
    "weekday_name",
    "hour",
    "origin_name",
    "destination_name",
    "total_trips",
    "route_recurrence_pct",
    "active_days",
    "origin_avg_balance",
    "destination_avg_balance",
    "origin_avg_departures",
    "origin_avg_arrivals",
    "destination_avg_departures",
    "destination_avg_arrivals"
]

columns_to_show = [
    col
    for col in columns_to_show
    if col in candidates.columns
]

print(
    candidates.head(20)[
        columns_to_show
    ].to_string(index=False)
)


print("\n")
print("=" * 60)
print("TOP 20 BY ROUTE VOLUME")
print("=" * 60)

print(
    candidates_by_volume.head(20)[
        columns_to_show
    ].to_string(index=False)
)


print("\n")
print("=" * 60)
print("CROSS SUMMARY")
print("=" * 60)

print(
    summary.to_string(index=False)
)


print("\nFILES GENERATED:")

print("- od_station_cross_all.csv")
print("- od_emitter_receiver_candidates.csv")
print("- od_emitter_receiver_by_volume.csv")
print("- od_station_cross_summary.csv")

print("\nOutput folder:")
print(OUTPUT_DIR)