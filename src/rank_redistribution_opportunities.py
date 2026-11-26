from pathlib import Path
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
    / "od_emitter_receiver_candidates.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD
# ============================================================

print("=" * 65)
print("REDISTRIBUTION OPPORTUNITY RANKING")
print("=" * 65)

df = pd.read_csv(INPUT_FILE)

print(f"\nLoaded candidate routes: {len(df):,}")
print("Columns:")
print(df.columns.tolist())

# ============================================================
# VALIDATION
# ============================================================

required_columns = [
    "weekday_name",
    "hour",
    "origin_name",
    "destination_name",
    "total_trips",
    "route_recurrence_pct",
    "active_days",
    "origin_avg_balance",
    "destination_avg_balance",
]

missing = [col for col in required_columns if col not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

numeric_columns = [
    "total_trips",
    "route_recurrence_pct",
    "active_days",
    "origin_avg_balance",
    "destination_avg_balance",
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=numeric_columns).copy()

# ============================================================
# TRANSPARENT CRITERIA
# ============================================================

# Route recurrence
df["recurrence_points"] = 0

df.loc[
    df["route_recurrence_pct"] >= 60,
    "recurrence_points"
] = 2

df.loc[
    (df["route_recurrence_pct"] >= 50)
    & (df["route_recurrence_pct"] < 60),
    "recurrence_points"
] = 1

# Route volume
df["volume_points"] = 0

df.loc[
    df["total_trips"] >= 60,
    "volume_points"
] = 2

df.loc[
    (df["total_trips"] >= 40)
    & (df["total_trips"] < 60),
    "volume_points"
] = 1

# Origin imbalance
df["origin_points"] = 0

df.loc[
    df["origin_avg_balance"] <= -5,
    "origin_points"
] = 2

df.loc[
    (df["origin_avg_balance"] <= -3)
    & (df["origin_avg_balance"] > -5),
    "origin_points"
] = 1

# Destination imbalance
df["destination_points"] = 0

df.loc[
    df["destination_avg_balance"] >= 5,
    "destination_points"
] = 2

df.loc[
    (df["destination_avg_balance"] >= 3)
    & (df["destination_avg_balance"] < 5),
    "destination_points"
] = 1

# ============================================================
# TOTAL SCORE
# ============================================================

df["evidence_score"] = (
    df["recurrence_points"]
    + df["volume_points"]
    + df["origin_points"]
    + df["destination_points"]
)

df["evidence_level"] = "Low"

df.loc[
    df["evidence_score"] >= 4,
    "evidence_level"
] = "Medium"

df.loc[
    df["evidence_score"] >= 6,
    "evidence_level"
] = "High"

# ============================================================
# EXPLANATORY FLAGS
# ============================================================

df["high_recurrence"] = (
    df["route_recurrence_pct"] >= 60
)

df["high_volume"] = (
    df["total_trips"] >= 60
)

df["strong_origin_emitter"] = (
    df["origin_avg_balance"] <= -5
)

df["strong_destination_receiver"] = (
    df["destination_avg_balance"] >= 5
)

df["strong_directional_match"] = (
    df["strong_origin_emitter"]
    & df["strong_destination_receiver"]
)

# ============================================================
# RANK
# ============================================================

df = df.sort_values(
    by=[
        "evidence_score",
        "route_recurrence_pct",
        "total_trips",
        "active_days",
    ],
    ascending=[False, False, False, False],
).reset_index(drop=True)

df["opportunity_rank"] = range(1, len(df) + 1)

# ============================================================
# INTERPRETATION
# ============================================================

def explain_route(row):

    signals = []

    if row["high_recurrence"]:
        signals.append("High route recurrence")

    elif row["route_recurrence_pct"] >= 50:
        signals.append("Moderate route recurrence")

    if row["high_volume"]:
        signals.append("High trip volume")

    elif row["total_trips"] >= 40:
        signals.append("Moderate trip volume")

    if row["strong_origin_emitter"]:
        signals.append("Strong origin imbalance")

    elif row["origin_avg_balance"] <= -3:
        signals.append("Moderate origin imbalance")

    if row["strong_destination_receiver"]:
        signals.append("Strong destination imbalance")

    elif row["destination_avg_balance"] >= 3:
        signals.append("Moderate destination imbalance")

    if not signals:
        return "Limited evidence across criteria"

    return "; ".join(signals)


df["evidence_explanation"] = df.apply(
    explain_route,
    axis=1
)

# ============================================================
# OUTPUT 1: FULL RANKING
# ============================================================

output_columns = [
    "opportunity_rank",
    "evidence_level",
    "evidence_score",
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
    "destination_avg_arrivals",
    "recurrence_points",
    "volume_points",
    "origin_points",
    "destination_points",
    "high_recurrence",
    "high_volume",
    "strong_origin_emitter",
    "strong_destination_receiver",
    "strong_directional_match",
    "evidence_explanation",
]

output_columns = [
    col for col in output_columns
    if col in df.columns
]

ranking_file = OUTPUT_DIR / "redistribution_opportunity_ranking.csv"

df[output_columns].to_csv(
    ranking_file,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# OUTPUT 2: HIGH EVIDENCE
# ============================================================

high_evidence = df[
    df["evidence_level"] == "High"
].copy()

high_file = OUTPUT_DIR / "redistribution_high_evidence.csv"

high_evidence[output_columns].to_csv(
    high_file,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# OUTPUT 3: SUMMARY BY WEEKDAY AND HOUR
# ============================================================

summary = (
    df.groupby(
        ["weekday_name", "hour"],
        as_index=False
    )
    .agg(
        candidate_routes=("origin_name", "count"),
        high_evidence_routes=(
            "evidence_level",
            lambda x: (x == "High").sum()
        ),
        medium_evidence_routes=(
            "evidence_level",
            lambda x: (x == "Medium").sum()
        ),
        total_trips=("total_trips", "sum"),
        mean_recurrence=("route_recurrence_pct", "mean"),
        max_score=("evidence_score", "max"),
    )
)

summary_file = OUTPUT_DIR / "redistribution_ranking_summary.csv"

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n" + "=" * 65)
print("RANKING FINISHED")
print("=" * 65)

print(f"\nTotal candidate routes: {len(df):,}")
print(f"High evidence: {len(high_evidence):,}")
print(
    "Medium evidence:",
    (df["evidence_level"] == "Medium").sum()
)
print(
    "Low evidence:",
    (df["evidence_level"] == "Low").sum()
)

print("\nTOP 20 OPPORTUNITIES")
print("-" * 65)

display_columns = [
    "opportunity_rank",
    "evidence_level",
    "evidence_score",
    "weekday_name",
    "hour",
    "origin_name",
    "destination_name",
    "total_trips",
    "route_recurrence_pct",
    "origin_avg_balance",
    "destination_avg_balance",
]

display_columns = [
    col for col in display_columns
    if col in df.columns
]

print(
    df[display_columns]
    .head(20)
    .to_string(index=False)
)

print("\n" + "=" * 65)
print("FILES GENERATED")
print("=" * 65)

print(f"- {ranking_file}")
print(f"- {high_file}")
print(f"- {summary_file}")

print("\nAnalysis completed.")