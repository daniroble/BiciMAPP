import pandas as pd
from pathlib import Path

INPUT = Path("data/processed/trips_2022_2023.csv")
DAILY_OUTPUT = Path("data/processed/station_time_daily.csv")
OUTPUT = Path("data/processed/station_time_recurrence.csv")

CHUNK_SIZE = 200_000

partials = []
total_rows = 0

print("Calculating daily station flows...")

for chunk in pd.read_csv(
    INPUT,
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    total_rows += len(chunk)

    # Convert station IDs
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

    # =========================
    # DEPARTURES
    # =========================

    dep = chunk.dropna(
        subset=["unlock_dt", "station_unlock"]
    ).copy()

    dep = dep[dep["station_unlock"] >= 0]

    dep["event_date"] = dep["unlock_dt"].dt.date
    dep["weekday_num"] = dep["unlock_dt"].dt.day_of_week
    dep["hour"] = dep["unlock_dt"].dt.hour

    dep = dep[
        [
            "station_unlock",
            "unlock_station_name",
            "event_date",
            "weekday_num",
            "hour",
        ]
    ]

    dep.columns = [
        "station_id",
        "station_name",
        "event_date",
        "weekday_num",
        "hour",
    ]

    dep["departures"] = 1
    dep["arrivals"] = 0

    # =========================
    # ARRIVALS
    # =========================

    arr = chunk.dropna(
        subset=["lock_dt", "station_lock"]
    ).copy()

    arr = arr[arr["station_lock"] >= 0]

    arr["event_date"] = arr["lock_dt"].dt.date
    arr["weekday_num"] = arr["lock_dt"].dt.day_of_week
    arr["hour"] = arr["lock_dt"].dt.hour

    arr = arr[
        [
            "station_lock",
            "lock_station_name",
            "event_date",
            "weekday_num",
            "hour",
        ]
    ]

    arr.columns = [
        "station_id",
        "station_name",
        "event_date",
        "weekday_num",
        "hour",
    ]

    arr["departures"] = 0
    arr["arrivals"] = 1

    # =========================
    # COMBINE
    # =========================

    events = pd.concat(
        [dep, arr],
        ignore_index=True
    )

    daily = (
        events.groupby(
            [
                "station_id",
                "station_name",
                "event_date",
                "weekday_num",
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

    partials.append(daily)

    print(
        f"Processed {total_rows:,} rows",
        end="\r"
    )

# =========================
# CONSOLIDATE DAILY DATA
# =========================

print("\nConsolidating daily data...")

daily_result = pd.concat(
    partials,
    ignore_index=True
)

daily_result = (
    daily_result.groupby(
        [
            "station_id",
            "station_name",
            "event_date",
            "weekday_num",
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

daily_result["net_balance"] = (
    daily_result["arrivals"] - daily_result["departures"]
)

daily_result["absolute_imbalance"] = (
    daily_result["net_balance"].abs()
)

daily_result["total_activity"] = (
    daily_result["arrivals"] + daily_result["departures"]
)

DAILY_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

daily_result.to_csv(
    DAILY_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# =========================
# RECURRENCE ANALYSIS
# =========================

print("Calculating recurrence indicators...")

summary = (
    daily_result.groupby(
        [
            "station_id",
            "station_name",
            "weekday_num",
            "hour",
        ],
        dropna=False
    )
    .agg(
        observed_days=("event_date", "nunique"),
        avg_daily_departures=("departures", "mean"),
        avg_daily_arrivals=("arrivals", "mean"),
        avg_daily_balance=("net_balance", "mean"),
        avg_abs_daily_balance=("absolute_imbalance", "mean"),
        avg_daily_activity=("total_activity", "mean"),
        positive_days=("net_balance", lambda x: (x > 0).sum()),
        negative_days=("net_balance", lambda x: (x < 0).sum()),
        balanced_days=("net_balance", lambda x: (x == 0).sum()),
    )
    .reset_index()
)

summary["positive_days_pct"] = (
    summary["positive_days"]
    / summary["observed_days"]
    * 100
)

summary["negative_days_pct"] = (
    summary["negative_days"]
    / summary["observed_days"]
    * 100
)

summary["balanced_days_pct"] = (
    summary["balanced_days"]
    / summary["observed_days"]
    * 100
)

# Minimum evidence filter
reliable = summary[
    (summary["observed_days"] >= 20)
    & (summary["avg_daily_activity"] >= 10)
].copy()

# Sort by mean daily imbalance
reliable = reliable.sort_values(
    "avg_abs_daily_balance",
    ascending=False
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

reliable.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# =========================
# REPORT
# =========================

print("\n" + "=" * 60)
print("RECURRENCE ANALYSIS COMPLETED")
print("=" * 60)

print(f"Total rows processed: {total_rows:,}")
print(f"Daily station records: {len(daily_result):,}")
print(f"Station-day-hour groups: {len(summary):,}")
print(f"Groups after evidence filter: {len(reliable):,}")

print(f"\nDaily file: {DAILY_OUTPUT}")
print(f"Recurrence file: {OUTPUT}")

columns = [
    "station_id",
    "station_name",
    "weekday_num",
    "hour",
    "observed_days",
    "avg_daily_departures",
    "avg_daily_arrivals",
    "avg_daily_balance",
    "avg_abs_daily_balance",
    "avg_daily_activity",
    "positive_days_pct",
    "negative_days_pct",
]

print("\nTOP 30 RECURRING IMBALANCES:")
print(
    reliable.head(30)[columns].to_string(index=False)
)

print("\nTOP 20 CONSISTENT POSITIVE BALANCES:")
print(
    reliable[
        reliable["positive_days_pct"] >= 70
    ].sort_values(
        "avg_daily_balance",
        ascending=False
    ).head(20)[columns].to_string(index=False)
)

print("\nTOP 20 CONSISTENT NEGATIVE BALANCES:")
print(
    reliable[
        reliable["negative_days_pct"] >= 70
    ].sort_values(
        "avg_daily_balance",
        ascending=True
    ).head(20)[columns].to_string(index=False)
)