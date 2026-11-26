# src/classify_redistribution_routes.py

from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
    / "od_station_cross_all.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(df, candidates, description):
    """
    Finds the first available column from a list of alternatives.
    """

    for col in candidates:
        if col in df.columns:
            return col

    raise ValueError(
        f"No se encuentra la columna necesaria: {description}\n"
        f"Columnas disponibles:\n{list(df.columns)}"
    )


def normalize_columns(df):

    column_map = {}

    column_map["weekday"] = find_column(
        df,
        ["weekday", "weekday_name", "day_name"],
        "weekday"
    )

    column_map["hour"] = find_column(
        df,
        ["hour", "start_hour"],
        "hour"
    )

    column_map["origin_id"] = find_column(
        df,
        ["origin_id", "station_unlock", "station_origin_id"],
        "origin_id"
    )

    column_map["origin_name"] = find_column(
        df,
        ["origin_name", "unlock_station_name", "origin_station_name"],
        "origin_name"
    )

    column_map["destination_id"] = find_column(
        df,
        ["destination_id", "station_lock", "station_destination_id"],
        "destination_id"
    )

    column_map["destination_name"] = find_column(
        df,
        [
            "destination_name",
            "lock_station_name",
            "destination_station_name"
        ],
        "destination_name"
    )

    column_map["total_trips"] = find_column(
        df,
        ["total_trips", "trips", "route_trips"],
        "total_trips"
    )

    column_map["recurrence_pct"] = find_column(
        df,
        ["recurrence_pct", "recurrence_percentage"],
        "recurrence_pct"
    )

    column_map["origin_balance"] = find_column(
        df,
        [
            "origin_avg_daily_balance",
            "avg_daily_balance_origin",
            "origin_avg_balance",
            "avg_daily_balance_x",
            "avg_daily_balance_origin_station"
        ],
        "balance medio de estación de origen"
    )

    column_map["destination_balance"] = find_column(
        df,
        [
            "destination_avg_daily_balance",
            "avg_daily_balance_destination",
            "destination_avg_balance",
            "avg_daily_balance_y",
            "avg_daily_balance_destination_station"
        ],
        "balance medio de estación de destino"
    )

    rename_map = {
        original: standard
        for standard, original in column_map.items()
    }

    df = df.rename(columns=rename_map)

    return df


# ============================================================
# LOAD DATA
# ============================================================

print("Cargando datos...")

df = pd.read_csv(INPUT_FILE)

print(f"Filas originales: {len(df):,}")

df = normalize_columns(df)


# ============================================================
# DATA CLEANING
# ============================================================

numeric_columns = [
    "hour",
    "total_trips",
    "recurrence_pct",
    "origin_balance",
    "destination_balance"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=[
        "hour",
        "total_trips",
        "recurrence_pct",
        "origin_balance",
        "destination_balance"
    ]
).copy()

# Remove impossible values
df = df[
    (df["hour"] >= 0)
    & (df["hour"] <= 23)
    & (df["total_trips"] >= 0)
    & (df["recurrence_pct"] >= 0)
    & (df["recurrence_pct"] <= 100)
].copy()

print(f"Filas válidas: {len(df):,}")


# ============================================================
# DEMAND ANALYSIS
# ============================================================

# Demand is evaluated independently from redistribution.
# A route may have recurrent demand even if its stations
# do not show a strong imbalance.

df["recurrence_score"] = 0

df.loc[
    df["recurrence_pct"] >= 60,
    "recurrence_score"
] = 2

df.loc[
    (df["recurrence_pct"] >= 50)
    & (df["recurrence_pct"] < 60),
    "recurrence_score"
] = 1


df["volume_score"] = 0

df.loc[
    df["total_trips"] >= 60,
    "volume_score"
] = 2

df.loc[
    (df["total_trips"] >= 40)
    & (df["total_trips"] < 60),
    "volume_score"
] = 1


df["demand_score"] = (
    df["recurrence_score"]
    + df["volume_score"]
)


df["recurring_demand"] = (
    (df["recurrence_pct"] >= 50)
    & (df["total_trips"] >= 40)
)


# ============================================================
# REDISTRIBUTION ANALYSIS
# ============================================================

# Negative origin balance = station tends to lose bikes.
# Positive destination balance = station tends to gain bikes.

df["origin_emitter_strong"] = (
    df["origin_balance"] <= -5
)

df["destination_receiver_strong"] = (
    df["destination_balance"] >= 5
)

df["origin_emitter_moderate"] = (
    df["origin_balance"] <= -3
)

df["destination_receiver_moderate"] = (
    df["destination_balance"] >= 3
)


# Strong redistribution opportunity:
# - Strong emitter
# - Strong receiver
# - At least 50% recurrence
# - At least 40 trips

df["strong_redistribution"] = (
    df["origin_emitter_strong"]
    & df["destination_receiver_strong"]
    & (df["recurrence_pct"] >= 50)
    & (df["total_trips"] >= 40)
)


# Potential redistribution opportunity:
# - Moderate emitter
# - Moderate receiver
# - At least 40% recurrence
# - At least 25 trips
# - Not already classified as strong

df["potential_redistribution"] = (
    df["origin_emitter_moderate"]
    & df["destination_receiver_moderate"]
    & (df["recurrence_pct"] >= 40)
    & (df["total_trips"] >= 25)
    & (~df["strong_redistribution"])
)


# ============================================================
# AUXILIARY REDISTRIBUTION SCORE
# ============================================================

# This score is only supplementary.
# It is NOT used to replace the strict classification rules.

df["redistribution_score"] = 0

df.loc[
    df["recurrence_pct"] >= 60,
    "redistribution_score"
] += 2

df.loc[
    (df["recurrence_pct"] >= 50)
    & (df["recurrence_pct"] < 60),
    "redistribution_score"
] += 1

df.loc[
    df["total_trips"] >= 60,
    "redistribution_score"
] += 2

df.loc[
    (df["total_trips"] >= 40)
    & (df["total_trips"] < 60),
    "redistribution_score"
] += 1

df.loc[
    df["origin_balance"] <= -5,
    "redistribution_score"
] += 2

df.loc[
    (df["origin_balance"] <= -3)
    & (df["origin_balance"] > -5),
    "redistribution_score"
] += 1

df.loc[
    df["destination_balance"] >= 5,
    "redistribution_score"
] += 2

df.loc[
    (df["destination_balance"] >= 3)
    & (df["destination_balance"] < 5),
    "redistribution_score"
] += 1


# ============================================================
# FINAL CLASSIFICATION
# ============================================================

def classify_route(row):

    if row["strong_redistribution"]:
        return "Strong redistribution"

    elif row["potential_redistribution"]:
        return "Potential redistribution"

    elif row["recurring_demand"]:
        return "Recurring demand"

    else:
        return "Other"


df["route_classification"] = df.apply(
    classify_route,
    axis=1
)


# ============================================================
# ADD INTERPRETATION
# ============================================================

def interpret_route(row):

    if row["strong_redistribution"]:
        return (
            "Strong directional imbalance: "
            "origin emitter and destination receiver"
        )

    elif row["potential_redistribution"]:
        return (
            "Moderate directional imbalance: "
            "possible redistribution opportunity"
        )

    elif row["recurring_demand"]:
        return (
            "Recurring demand detected, "
            "but redistribution evidence is insufficient"
        )

    else:
        return (
            "No strong evidence under current thresholds"
        )


df["interpretation"] = df.apply(
    interpret_route,
    axis=1
)


# ============================================================
# SORTING
# ============================================================

df = df.sort_values(
    by=[
        "strong_redistribution",
        "potential_redistribution",
        "recurring_demand",
        "demand_score",
        "redistribution_score",
        "recurrence_pct",
        "total_trips"
    ],
    ascending=[
        False,
        False,
        False,
        False,
        False,
        False,
        False
    ]
)


# ============================================================
# OUTPUT 1: COMPLETE CLASSIFICATION
# ============================================================

df.to_csv(
    OUTPUT_DIR / "route_classification_final.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# OUTPUT 2: RECURRING DEMAND
# ============================================================

recurring = df[
    df["recurring_demand"]
].copy()

recurring = recurring.sort_values(
    by=[
        "recurrence_pct",
        "total_trips",
        "demand_score"
    ],
    ascending=False
)

recurring.to_csv(
    OUTPUT_DIR / "recurring_demand_ranking.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# OUTPUT 3: ALL REDISTRIBUTION OPPORTUNITIES
# ============================================================

redistribution = df[
    df["strong_redistribution"]
    | df["potential_redistribution"]
].copy()

redistribution = redistribution.sort_values(
    by=[
        "strong_redistribution",
        "potential_redistribution",
        "recurrence_pct",
        "total_trips"
    ],
    ascending=False
)

redistribution.to_csv(
    OUTPUT_DIR / "redistribution_opportunities_final.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# OUTPUT 4: STRONG OPPORTUNITIES
# ============================================================

strong = df[
    df["strong_redistribution"]
].copy()

strong = strong.sort_values(
    by=[
        "recurrence_pct",
        "total_trips",
        "origin_balance",
        "destination_balance"
    ],
    ascending=[
        False,
        False,
        True,
        False
    ]
)

strong.to_csv(
    OUTPUT_DIR / "strong_redistribution_opportunities.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# OUTPUT 5: POTENTIAL OPPORTUNITIES
# ============================================================

potential = df[
    df["potential_redistribution"]
].copy()

potential = potential.sort_values(
    by=[
        "recurrence_pct",
        "total_trips",
        "origin_balance",
        "destination_balance"
    ],
    ascending=[
        False,
        False,
        True,
        False
    ]
)

potential.to_csv(
    OUTPUT_DIR / "potential_redistribution_opportunities.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# OUTPUT 6: SUMMARY
# ============================================================

summary = (
    df.groupby("route_classification")
    .agg(
        routes=("total_trips", "count"),
        total_trips=("total_trips", "sum"),
        mean_recurrence_pct=("recurrence_pct", "mean"),
        mean_trips_per_route=("total_trips", "mean"),
        mean_origin_balance=("origin_balance", "mean"),
        mean_destination_balance=("destination_balance", "mean")
    )
    .reset_index()
)

summary = summary.sort_values(
    by="routes",
    ascending=False
)

summary.to_csv(
    OUTPUT_DIR / "route_classification_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# CONSOLE REPORT
# ============================================================

print("\n" + "=" * 60)
print("FINAL ROUTE CLASSIFICATION")
print("=" * 60)

print(f"Total routes analysed: {len(df):,}")
print(
    f"Recurring demand routes: "
    f"{df['recurring_demand'].sum():,}"
)
print(
    f"Strong redistribution opportunities: "
    f"{df['strong_redistribution'].sum():,}"
)
print(
    f"Potential redistribution opportunities: "
    f"{df['potential_redistribution'].sum():,}"
)

print("\nClassification summary:")
print(summary.to_string(index=False))

print("\nTop recurring demand routes:")
print(
    recurring[
        [
            "weekday",
            "hour",
            "origin_name",
            "destination_name",
            "total_trips",
            "recurrence_pct",
            "origin_balance",
            "destination_balance"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\nTop strong redistribution opportunities:")
print(
    strong[
        [
            "weekday",
            "hour",
            "origin_name",
            "destination_name",
            "total_trips",
            "recurrence_pct",
            "origin_balance",
            "destination_balance"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\nTop potential redistribution opportunities:")
print(
    potential[
        [
            "weekday",
            "hour",
            "origin_name",
            "destination_name",
            "total_trips",
            "recurrence_pct",
            "origin_balance",
            "destination_balance"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\nFiles generated:")
print(" - route_classification_final.csv")
print(" - recurring_demand_ranking.csv")
print(" - redistribution_opportunities_final.csv")
print(" - strong_redistribution_opportunities.csv")
print(" - potential_redistribution_opportunities.csv")
print(" - route_classification_summary.csv")

print("\nAnalysis completed successfully.")