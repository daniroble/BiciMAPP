# src/audit_station_diagnosis_coverage.py

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

STATION_DIAG_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "station_time_recurrence.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "cross_analysis"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def normalize_id(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def normalize_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def find_column(df, candidates, description):

    for col in candidates:
        if col in df.columns:
            return col

    raise ValueError(
        f"No se encontró columna para {description}.\n"
        f"Columnas disponibles: {list(df.columns)}"
    )


# ============================================================
# LOAD
# ============================================================

print("=" * 75)
print("STATION DIAGNOSIS COVERAGE AUDIT")
print("=" * 75)

if not CROSS_FILE.exists():
    raise FileNotFoundError(
        f"No existe el archivo:\n{CROSS_FILE}"
    )

if not STATION_DIAG_FILE.exists():
    raise FileNotFoundError(
        f"No existe el archivo:\n{STATION_DIAG_FILE}"
    )

cross = pd.read_csv(CROSS_FILE)

station_diag = pd.read_csv(
    STATION_DIAG_FILE
)

print("\nFiles:")
print(f"OD cross-analysis: {CROSS_FILE}")
print(f"Station diagnosis: {STATION_DIAG_FILE}")

print("\nOriginal rows:")
print(f"OD routes: {len(cross):,}")
print(f"Station diagnosis records: {len(station_diag):,}")


# ============================================================
# DETECT COLUMNS
# ============================================================

route_origin_id = find_column(
    cross,
    ["origin_id"],
    "origin station ID"
)

route_destination_id = find_column(
    cross,
    ["destination_id"],
    "destination station ID"
)

route_weekday = find_column(
    cross,
    ["weekday_num"],
    "route weekday"
)

route_hour = find_column(
    cross,
    ["hour"],
    "route hour"
)

diag_station_id = find_column(
    station_diag,
    ["station_id"],
    "diagnosis station ID"
)

diag_weekday = find_column(
    station_diag,
    ["weekday_num"],
    "diagnosis weekday"
)

diag_hour = find_column(
    station_diag,
    ["hour"],
    "diagnosis hour"
)


# ============================================================
# NORMALIZE KEYS
# ============================================================

cross["_origin_key"] = normalize_id(
    cross[route_origin_id]
)

cross["_destination_key"] = normalize_id(
    cross[route_destination_id]
)

cross["_weekday_key"] = normalize_numeric(
    cross[route_weekday]
)

cross["_hour_key"] = normalize_numeric(
    cross[route_hour]
)

station_diag["_station_key"] = normalize_id(
    station_diag[diag_station_id]
)

station_diag["_weekday_key"] = normalize_numeric(
    station_diag[diag_weekday]
)

station_diag["_hour_key"] = normalize_numeric(
    station_diag[diag_hour]
)


# ============================================================
# CLEAN DIAGNOSIS KEYS
# ============================================================

diagnosis_keys = station_diag[
    [
        "_station_key",
        "_weekday_key",
        "_hour_key"
    ]
].drop_duplicates()

diagnosis_keys = diagnosis_keys.dropna(
    subset=[
        "_station_key",
        "_weekday_key",
        "_hour_key"
    ]
)

diagnosis_keys["_diagnosis_exists"] = True

print(
    f"\nUnique diagnosis keys: "
    f"{len(diagnosis_keys):,}"
)


# ============================================================
# ORIGIN DIAGNOSIS MATCH
# ============================================================

origin_lookup = diagnosis_keys.rename(
    columns={
        "_station_key": "_origin_key",
        "_weekday_key": "_weekday_key",
        "_hour_key": "_hour_key",
        "_diagnosis_exists": "origin_diagnosis_key_exists"
    }
)

cross = cross.merge(
    origin_lookup,
    on=[
        "_origin_key",
        "_weekday_key",
        "_hour_key"
    ],
    how="left"
)

cross["origin_diagnosis_key_exists"] = (
    cross["origin_diagnosis_key_exists"]
    .fillna(False)
    .astype(bool)
)


# ============================================================
# DESTINATION DIAGNOSIS MATCH
# ============================================================

destination_lookup = diagnosis_keys.rename(
    columns={
        "_station_key": "_destination_key",
        "_weekday_key": "_weekday_key",
        "_hour_key": "_hour_key",
        "_diagnosis_exists": "destination_diagnosis_key_exists"
    }
)

cross = cross.merge(
    destination_lookup,
    on=[
        "_destination_key",
        "_weekday_key",
        "_hour_key"
    ],
    how="left"
)

cross["destination_diagnosis_key_exists"] = (
    cross["destination_diagnosis_key_exists"]
    .fillna(False)
    .astype(bool)
)


# ============================================================
# BOOLEAN LOGIC
# ============================================================

origin_match = (
    cross["origin_diagnosis_key_exists"]
    .astype(bool)
)

destination_match = (
    cross["destination_diagnosis_key_exists"]
    .astype(bool)
)

both_match = (
    origin_match
    & destination_match
)

origin_only_match = (
    origin_match
    & ~destination_match
)

destination_only_match = (
    ~origin_match
    & destination_match
)

neither_match = (
    ~origin_match
    & ~destination_match
)


# ============================================================
# COVERAGE REPORT
# ============================================================

coverage = pd.DataFrame([
    {
        "condition": "All OD routes",
        "routes": len(cross)
    },
    {
        "condition": "Origin diagnosis key exists",
        "routes": int(origin_match.sum())
    },
    {
        "condition": "Destination diagnosis key exists",
        "routes": int(destination_match.sum())
    },
    {
        "condition": "Both diagnosis keys exist",
        "routes": int(both_match.sum())
    },
    {
        "condition": "Origin only",
        "routes": int(origin_only_match.sum())
    },
    {
        "condition": "Destination only",
        "routes": int(destination_only_match.sum())
    },
    {
        "condition": "Neither",
        "routes": int(neither_match.sum())
    }
])

coverage["percentage"] = (
    coverage["routes"]
    / len(cross)
    * 100
)


print("\n1. DIAGNOSIS KEY MATCH")
print("-" * 75)

print(
    coverage.to_string(
        index=False
    )
)


# ============================================================
# STATION LEVEL COVERAGE
# ============================================================

origin_station_summary = (
    cross.groupby("_origin_key")
    .agg(
        route_records=("_origin_key", "size"),
        diagnosis_matches=(
            "origin_diagnosis_key_exists",
            "sum"
        )
    )
    .reset_index()
)

origin_station_summary["coverage_pct"] = (
    origin_station_summary["diagnosis_matches"]
    / origin_station_summary["route_records"]
    * 100
)

origin_station_summary = origin_station_summary.rename(
    columns={
        "_origin_key": "station_id"
    }
)


destination_station_summary = (
    cross.groupby("_destination_key")
    .agg(
        route_records=("_destination_key", "size"),
        diagnosis_matches=(
            "destination_diagnosis_key_exists",
            "sum"
        )
    )
    .reset_index()
)

destination_station_summary["coverage_pct"] = (
    destination_station_summary["diagnosis_matches"]
    / destination_station_summary["route_records"]
    * 100
)

destination_station_summary = destination_station_summary.rename(
    columns={
        "_destination_key": "station_id"
    }
)


# ============================================================
# MISSING DIAGNOSIS ROUTES
# ============================================================

missing_origin = cross[
    ~origin_match
].copy()

missing_destination = cross[
    ~destination_match
].copy()

missing_both = cross[
    neither_match
].copy()

missing_either = cross[
    ~both_match
].copy()


# ============================================================
# COVERAGE BY WEEKDAY AND HOUR
# ============================================================

cross["_both_diagnoses"] = both_match

coverage_by_time = (
    cross.groupby(
        [
            "weekday_name",
            "_weekday_key",
            "_hour_key"
        ]
    )
    .agg(
        total_routes=("origin_id", "size"),
        origin_diagnosis_matches=(
            "origin_diagnosis_key_exists",
            "sum"
        ),
        destination_diagnosis_matches=(
            "destination_diagnosis_key_exists",
            "sum"
        ),
        both_diagnoses=(
            "_both_diagnoses",
            "sum"
        )
    )
    .reset_index()
)

coverage_by_time["both_diagnoses_pct"] = (
    coverage_by_time["both_diagnoses"]
    / coverage_by_time["total_routes"]
    * 100
)


# ============================================================
# SAVE OUTPUTS
# ============================================================

coverage.to_csv(
    OUTPUT_DIR / "station_diagnosis_key_coverage.csv",
    index=False,
    encoding="utf-8-sig"
)

origin_station_summary.to_csv(
    OUTPUT_DIR / "origin_station_diagnosis_coverage.csv",
    index=False,
    encoding="utf-8-sig"
)

destination_station_summary.to_csv(
    OUTPUT_DIR / "destination_station_diagnosis_coverage.csv",
    index=False,
    encoding="utf-8-sig"
)

missing_origin.to_csv(
    OUTPUT_DIR / "routes_missing_origin_diagnosis.csv",
    index=False,
    encoding="utf-8-sig"
)

missing_destination.to_csv(
    OUTPUT_DIR / "routes_missing_destination_diagnosis.csv",
    index=False,
    encoding="utf-8-sig"
)

missing_both.to_csv(
    OUTPUT_DIR / "routes_missing_both_diagnoses.csv",
    index=False,
    encoding="utf-8-sig"
)

missing_either.to_csv(
    OUTPUT_DIR / "routes_missing_either_diagnosis.csv",
    index=False,
    encoding="utf-8-sig"
)

coverage_by_time.to_csv(
    OUTPUT_DIR / "station_diagnosis_coverage_by_time.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# REPORT
# ============================================================

print("\n2. STATION-LEVEL COVERAGE")
print("-" * 75)

print("\nOrigin stations with lowest diagnosis coverage:")

print(
    origin_station_summary.sort_values(
        "coverage_pct"
    )
    .head(15)
    .to_string(index=False)
)

print("\nDestination stations with lowest diagnosis coverage:")

print(
    destination_station_summary.sort_values(
        "coverage_pct"
    )
    .head(15)
    .to_string(index=False)
)


print("\n3. ROUTES WITH MISSING DIAGNOSIS")
print("-" * 75)

print(
    f"Missing origin diagnosis: "
    f"{len(missing_origin):,}"
)

print(
    f"Missing destination diagnosis: "
    f"{len(missing_destination):,}"
)

print(
    f"Missing both diagnoses: "
    f"{len(missing_both):,}"
)

print(
    f"Missing at least one diagnosis: "
    f"{len(missing_either):,}"
)


print("\n4. COVERAGE BY WEEKDAY AND HOUR")
print("-" * 75)

print(
    coverage_by_time.sort_values(
        "both_diagnoses_pct",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


print("\n5. FILES GENERATED")
print("-" * 75)

print(" - station_diagnosis_key_coverage.csv")
print(" - origin_station_diagnosis_coverage.csv")
print(" - destination_station_diagnosis_coverage.csv")
print(" - routes_missing_origin_diagnosis.csv")
print(" - routes_missing_destination_diagnosis.csv")
print(" - routes_missing_both_diagnoses.csv")
print(" - routes_missing_either_diagnosis.csv")
print(" - station_diagnosis_coverage_by_time.csv")


print("\nAudit completed successfully.")