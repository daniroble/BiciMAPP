# src/audit_cross_analysis_coverage.py

from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

CROSS_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
    / "od_station_cross_all.csv"
)

CLASSIFIED_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
    / "route_classification_final.csv"
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

def find_column(df, candidates):

    for col in candidates:
        if col in df.columns:
            return col

    return None


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("CROSS-ANALYSIS COVERAGE AUDIT")
print("=" * 70)

cross = pd.read_csv(CROSS_FILE)

print("\n1. ORIGINAL CROSS-ANALYSIS FILE")
print("-" * 70)

print(f"Rows: {len(cross):,}")
print(f"Columns: {len(cross.columns)}")

print("\nColumn names:")
for col in cross.columns:
    print(f"  - {col}")


# ============================================================
# FIND RELEVANT COLUMNS
# ============================================================

origin_balance_col = find_column(
    cross,
    [
        "origin_avg_daily_balance",
        "avg_daily_balance_origin",
        "origin_avg_balance",
        "avg_daily_balance_x",
        "avg_daily_balance_origin_station",
        "origin_balance"
    ]
)

destination_balance_col = find_column(
    cross,
    [
        "destination_avg_daily_balance",
        "avg_daily_balance_destination",
        "destination_avg_balance",
        "avg_daily_balance_y",
        "avg_daily_balance_destination_station",
        "destination_balance"
    ]
)

trips_col = find_column(
    cross,
    [
        "total_trips",
        "trips",
        "route_trips"
    ]
)

recurrence_col = find_column(
    cross,
    [
        "recurrence_pct",
        "recurrence_percentage"
    ]
)

print("\n2. DETECTED COLUMNS")
print("-" * 70)

print(f"Origin balance:      {origin_balance_col}")
print(f"Destination balance: {destination_balance_col}")
print(f"Total trips:         {trips_col}")
print(f"Recurrence:          {recurrence_col}")


# ============================================================
# NULL AUDIT
# ============================================================

print("\n3. MISSING VALUES")
print("-" * 70)

null_summary = pd.DataFrame({
    "column": cross.columns,
    "missing_count": cross.isna().sum().values,
    "missing_pct": (
        cross.isna().mean().values * 100
    )
})

null_summary = null_summary.sort_values(
    by="missing_count",
    ascending=False
)

print(null_summary.to_string(index=False))

null_summary.to_csv(
    OUTPUT_DIR / "coverage_null_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# COVERAGE COMBINATIONS
# ============================================================

if origin_balance_col is None or destination_balance_col is None:

    print("\nERROR:")
    print(
        "No se han podido identificar automáticamente "
        "las columnas de balance."
    )

    print(
        "\nRevisa las columnas impresas arriba y "
        "añade los nombres reales a las listas de detección."
    )

    raise SystemExit(1)


origin_valid = cross[origin_balance_col].notna()
destination_valid = cross[destination_balance_col].notna()

both_valid = (
    origin_valid
    & destination_valid
)

neither_valid = (
    ~origin_valid
    & ~destination_valid
)

origin_only = (
    origin_valid
    & ~destination_valid
)

destination_only = (
    ~origin_valid
    & destination_valid
)


print("\n4. BALANCE COVERAGE")
print("-" * 70)

coverage = pd.DataFrame([
    {
        "condition": "All original routes",
        "routes": len(cross)
    },
    {
        "condition": "Origin balance available",
        "routes": origin_valid.sum()
    },
    {
        "condition": "Destination balance available",
        "routes": destination_valid.sum()
    },
    {
        "condition": "Both balances available",
        "routes": both_valid.sum()
    },
    {
        "condition": "Origin only",
        "routes": origin_only.sum()
    },
    {
        "condition": "Destination only",
        "routes": destination_only.sum()
    },
    {
        "condition": "Neither balance available",
        "routes": neither_valid.sum()
    }
])

coverage["percentage_of_original"] = (
    coverage["routes"]
    / len(cross)
    * 100
)

print(coverage.to_string(index=False))

coverage.to_csv(
    OUTPUT_DIR / "coverage_balance_combinations.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# ANALYSE FILTER LOSSES
# ============================================================

print("\n5. FILTER-RELATED COVERAGE")
print("-" * 70)

valid_numeric = pd.Series(
    True,
    index=cross.index
)

numeric_cols = []

if trips_col is not None:
    numeric_cols.append(trips_col)

if recurrence_col is not None:
    numeric_cols.append(recurrence_col)

numeric_cols.extend([
    origin_balance_col,
    destination_balance_col
])

for col in numeric_cols:

    numeric_values = pd.to_numeric(
        cross[col],
        errors="coerce"
    )

    valid_numeric &= numeric_values.notna()


print(
    f"Routes with all required numeric fields: "
    f"{valid_numeric.sum():,}"
)

print(
    f"Routes removed by missing/non-numeric values: "
    f"{(~valid_numeric).sum():,}"
)

print(
    f"Percentage retained: "
    f"{valid_numeric.mean() * 100:.2f}%"
)


# ============================================================
# MISSINGNESS PATTERN
# ============================================================

print("\n6. MISSINGNESS PATTERNS")
print("-" * 70)

pattern_df = cross.copy()

pattern_df["origin_balance_missing"] = (
    cross[origin_balance_col].isna()
)

pattern_df["destination_balance_missing"] = (
    cross[destination_balance_col].isna()
)

patterns = (
    pattern_df.groupby(
        [
            "origin_balance_missing",
            "destination_balance_missing"
        ]
    )
    .size()
    .reset_index(name="routes")
)

patterns["percentage"] = (
    patterns["routes"]
    / len(cross)
    * 100
)

print(patterns.to_string(index=False))

patterns.to_csv(
    OUTPUT_DIR / "coverage_missingness_patterns.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# COMPARE WITH CLASSIFIED DATA
# ============================================================

print("\n7. COMPARE WITH CLASSIFIER OUTPUT")
print("-" * 70)

if CLASSIFIED_FILE.exists():

    classified = pd.read_csv(CLASSIFIED_FILE)

    print(f"Classified routes: {len(classified):,}")
    print(f"Original routes:   {len(cross):,}")
    print(
        f"Difference:        "
        f"{len(cross) - len(classified):,}"
    )

    print(
        f"Classifier retention: "
        f"{len(classified) / len(cross) * 100:.2f}%"
    )

else:

    print(
        "No existe todavía route_classification_final.csv"
    )


# ============================================================
# SAVE ROUTES WITH MISSING BALANCE DATA
# ============================================================

missing_balance = cross[
    ~both_valid
].copy()

missing_balance["missing_origin_balance"] = (
    missing_balance[origin_balance_col].isna()
)

missing_balance["missing_destination_balance"] = (
    missing_balance[destination_balance_col].isna()
)

missing_balance.to_csv(
    OUTPUT_DIR / "routes_missing_station_balances.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n8. FINAL REPORT")
print("-" * 70)

print(
    f"Original route count: "
    f"{len(cross):,}"
)

print(
    f"Routes with both station balances: "
    f"{both_valid.sum():,}"
)

print(
    f"Coverage with both balances: "
    f"{both_valid.mean() * 100:.2f}%"
)

print(
    f"Routes missing at least one balance: "
    f"{(~both_valid).sum():,}"
)

print("\nFiles generated:")

print(" - coverage_null_summary.csv")
print(" - coverage_balance_combinations.csv")
print(" - coverage_missingness_patterns.csv")
print(" - routes_missing_station_balances.csv")

print("\nAudit completed.")