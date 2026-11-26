# src/build_crtm_match_review.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "processed" / "crtm_integration"
OUTPUT = BASE / "match_review"

MUNICIPAL_FILE = BASE / "municipal_stations_clean.csv"
CRTM_FILE = BASE / "crtm_stations_clean.csv"
EXACT_PAIRS_FILE = BASE / "quality_audit" / "exact_name_unique_pairs.csv"
NEAREST_FILE = BASE / "quality_audit" / "nearest_crtm_candidate_per_municipal.csv"
GEOGRAPHIC_FILE = BASE / "geographic_matching_candidates.csv"


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {path}")

    return pd.read_csv(path, low_memory=False)


def haversine_meters(lon1, lat1, lon2, lat2):

    from math import radians, sin, cos, sqrt, atan2

    earth_radius = 6371000

    lon1, lat1, lon2, lat2 = map(
        radians,
        [lon1, lat1, lon2, lat2]
    )

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


def main():

    print("\n" + "=" * 75)
    print("CONSTRUCCIÓN DE TABLA DE REVISIÓN DE MATCHING CRTM")
    print("=" * 75)

    municipal = load_csv(MUNICIPAL_FILE)
    crtm = load_csv(CRTM_FILE)
    exact_pairs = load_csv(EXACT_PAIRS_FILE)
    nearest = load_csv(NEAREST_FILE)
    geographic = load_csv(GEOGRAPHIC_FILE)

    # --------------------------------------------------------
    # 1. CONTAR MATCHES POR ESTACIÓN
    # --------------------------------------------------------

    municipal_match_counts = (
        exact_pairs.groupby("municipal_id")["crtm_id"]
        .nunique()
        .rename("exact_crtm_matches")
        .reset_index()
    )

    crtm_match_counts = (
        exact_pairs.groupby("crtm_id")["municipal_id"]
        .nunique()
        .rename("municipal_matches_for_crtm")
        .reset_index()
    )

    exact_pairs = exact_pairs.merge(
        municipal_match_counts,
        on="municipal_id",
        how="left"
    )

    exact_pairs = exact_pairs.merge(
        crtm_match_counts,
        on="crtm_id",
        how="left"
    )

    # --------------------------------------------------------
    # 2. DISTANCIA EXACTA ENTRE PARES DE NOMBRE
    # --------------------------------------------------------

    municipal_coords = municipal[
        [
            "municipal_id",
            "municipal_name",
            "municipal_lon",
            "municipal_lat",
            "municipal_bases",
            "municipal_state"
        ]
    ].copy()

    crtm_coords = crtm[
        [
            "crtm_id",
            "crtm_name",
            "crtm_system_name",
            "crtm_lon",
            "crtm_lat",
            "crtm_bikes"
        ]
    ].copy()

    exact_review = exact_pairs.merge(
        municipal_coords,
        on="municipal_id",
        how="left"
    )

    exact_review = exact_review.merge(
        crtm_coords,
        on="crtm_id",
        how="left"
    )

    exact_review["exact_name_distance_m"] = exact_review.apply(
        lambda row: haversine_meters(
            row["municipal_lon"],
            row["municipal_lat"],
            row["crtm_lon"],
            row["crtm_lat"]
        )
        if pd.notna(row["municipal_lon"])
        and pd.notna(row["municipal_lat"])
        and pd.notna(row["crtm_lon"])
        and pd.notna(row["crtm_lat"])
        else None,
        axis=1
    )

    # --------------------------------------------------------
    # 3. AÑADIR CANDIDATO GEOGRÁFICO MÁS CERCANO
    # --------------------------------------------------------

    nearest_columns = [
        "municipal_id",
        "crtm_id",
        "crtm_name",
        "crtm_system_name",
        "distance_m"
    ]

    nearest_small = nearest[
        nearest_columns
    ].copy()

    nearest_small = nearest_small.rename(
        columns={
            "crtm_id": "nearest_crtm_id",
            "crtm_name": "nearest_crtm_name",
            "crtm_system_name": "nearest_crtm_system_name",
            "distance_m": "nearest_distance_m"
        }
    )

    exact_review = exact_review.merge(
        nearest_small,
        on="municipal_id",
        how="left"
    )

    exact_review["exact_match_is_nearest"] = (
        exact_review["crtm_id"]
        == exact_review["nearest_crtm_id"]
    )

    # --------------------------------------------------------
    # 4. CLASIFICACIÓN PROVISIONAL
    # --------------------------------------------------------

    def classify_exact_match(row):

        exact_distance = row["exact_name_distance_m"]
        exact_count = row["exact_crtm_matches"]
        reverse_count = row["municipal_matches_for_crtm"]

        if pd.isna(exact_distance):
            return "REVIEW_COORDINATES_MISSING"

        if exact_count > 1:
            return "REVIEW_MULTIPLE_CRTM_NAME_MATCHES"

        if reverse_count > 1:
            return "REVIEW_CRTM_SHARED_BY_MULTIPLE_MUNICIPAL"

        if exact_distance <= 25:
            return "HIGH_CONFIDENCE_EXACT_NAME_AND_25M"

        if exact_distance <= 100:
            return "REVIEW_EXACT_NAME_25_TO_100M"

        return "REVIEW_EXACT_NAME_OVER_100M"

    exact_review["provisional_status"] = (
        exact_review.apply(
            classify_exact_match,
            axis=1
        )
    )

    # --------------------------------------------------------
    # 5. ESTACIONES SIN MATCH EXACTO
    # --------------------------------------------------------

    municipal_ids_with_exact = set(
        exact_pairs["municipal_id"]
    )

    municipal_without_exact = municipal[
        ~municipal["municipal_id"].isin(
            municipal_ids_with_exact
        )
    ].copy()

    municipal_without_exact = municipal_without_exact.merge(
        nearest_small,
        on="municipal_id",
        how="left"
    )

    # --------------------------------------------------------
    # 6. CLASIFICAR CANDIDATOS GEOGRÁFICOS SIN MATCH EXACTO
    # --------------------------------------------------------

    geographic = geographic.copy()

    geographic["nearest_rank"] = pd.to_numeric(
        geographic["nearest_rank"],
        errors="coerce"
    )

    geographic["distance_m"] = pd.to_numeric(
        geographic["distance_m"],
        errors="coerce"
    )

    second_candidates = geographic[
        geographic["nearest_rank"] == 2
    ][
        ["municipal_id", "distance_m"]
    ].rename(
        columns={
            "distance_m": "second_distance_m"
        }
    )

    municipal_without_exact = municipal_without_exact.merge(
        second_candidates,
        on="municipal_id",
        how="left"
    )

    municipal_without_exact["distance_gap_m"] = (
        municipal_without_exact["second_distance_m"]
        - municipal_without_exact["nearest_distance_m"]
    )

    def classify_geographic_only(row):

        nearest_distance = row["nearest_distance_m"]
        gap = row["distance_gap_m"]

        if pd.isna(nearest_distance):
            return "NO_GEOGRAPHIC_CANDIDATE"

        if nearest_distance <= 10 and (
            pd.isna(gap) or gap > 25
        ):
            return "HIGH_SPATIAL_CONFIDENCE_REVIEW_NAME"

        if nearest_distance <= 25:
            return "POTENTIAL_SPATIAL_MATCH_REVIEW"

        if nearest_distance <= 100:
            return "WEAK_SPATIAL_MATCH_REVIEW"

        return "NO_RELIABLE_MATCH"

    municipal_without_exact[
        "provisional_status"
    ] = municipal_without_exact.apply(
        classify_geographic_only,
        axis=1
    )

    # --------------------------------------------------------
    # 7. ESTACIONES CRTM SIN ASOCIACIÓN EXACTA
    # --------------------------------------------------------

    crtm_ids_with_exact = set(
        exact_pairs["crtm_id"]
    )

    crtm_without_exact = crtm[
        ~crtm["crtm_id"].isin(
            crtm_ids_with_exact
        )
    ].copy()

    # --------------------------------------------------------
    # 8. RESUMEN
    # --------------------------------------------------------

    print("\nRESUMEN DE MATCHES EXACTOS")
    print("-" * 75)

    print(f"Pairs exactos: {len(exact_pairs):,}")
    print(
        "Municipales con match exacto:",
        exact_pairs["municipal_id"].nunique()
    )
    print(
        "CRTM asociados por nombre:",
        exact_pairs["crtm_id"].nunique()
    )

    print("\nCLASIFICACIÓN PROVISIONAL")
    print("-" * 75)

    print(
        exact_review["provisional_status"]
        .value_counts()
        .to_string()
    )

    print("\nMUNICIPALES SIN MATCH EXACTO")
    print("-" * 75)

    print(
        municipal_without_exact[
            "provisional_status"
        ].value_counts().to_string()
    )

    print("\nCRTM SIN MATCH EXACTO")
    print("-" * 75)

    print(
        f"CRTM sin match exacto: "
        f"{len(crtm_without_exact):,}"
    )

    # --------------------------------------------------------
    # 9. EXPORTAR
    # --------------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    exact_review.to_csv(
        OUTPUT / "exact_match_review.csv",
        index=False,
        encoding="utf-8-sig"
    )

    municipal_without_exact.to_csv(
        OUTPUT / "municipal_without_exact_match_review.csv",
        index=False,
        encoding="utf-8-sig"
    )

    crtm_without_exact.to_csv(
        OUTPUT / "crtm_without_exact_match.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nARCHIVOS GENERADOS")
    print("-" * 75)

    for file in OUTPUT.glob("*.csv"):

        print(
            f"{file.name} | "
            f"{file.stat().st_size / 1024:.2f} KB"
        )

    print("\nAUDITORÍA DE REVISIÓN TERMINADA")
    print(
        "Las clasificaciones son provisionales. "
        "No constituyen una integración automática definitiva."
    )


if __name__ == "__main__":
    main()