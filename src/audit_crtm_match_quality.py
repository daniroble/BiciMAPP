# src/audit_crtm_match_quality.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "processed" / "crtm_integration"
OUTPUT_DIR = INPUT_DIR / "quality_audit"

GEOGRAPHIC_FILE = INPUT_DIR / "geographic_matching_candidates.csv"
EXACT_FILE = INPUT_DIR / "exact_name_matches.csv"
FUZZY_FILE = INPUT_DIR / "fuzzy_name_candidates.csv"


def load_file(path):

    if not path.exists():
        raise FileNotFoundError(f"No se encuentra:\n{path}")

    return pd.read_csv(path, low_memory=False)


def main():

    print("\n" + "=" * 75)
    print("AUDITORÍA DE CALIDAD DEL MATCHING MUNICIPAL - CRTM")
    print("=" * 75)

    geographic = load_file(GEOGRAPHIC_FILE)
    exact = load_file(EXACT_FILE)
    fuzzy = load_file(FUZZY_FILE)

    # --------------------------------------------------------
    # 1. CANDIDATO GEOGRÁFICO MÁS CERCANO
    # --------------------------------------------------------

    geographic["distance_m"] = pd.to_numeric(
        geographic["distance_m"],
        errors="coerce"
    )

    geographic["nearest_rank"] = pd.to_numeric(
        geographic["nearest_rank"],
        errors="coerce"
    )

    nearest = geographic[
        geographic["nearest_rank"] == 1
    ].copy()

    nearest = nearest.sort_values(
        "distance_m"
    )

    total_municipal = nearest["municipal_id"].nunique()

    print("\n1. COBERTURA DEL CANDIDATO MÁS CERCANO")
    print("-" * 75)

    print(f"Estaciones municipales únicas: {total_municipal:,}")

    for threshold in [10, 25, 50, 100, 250]:

        count = (
            nearest["distance_m"] <= threshold
        ).sum()

        pct = (
            count / total_municipal * 100
            if total_municipal
            else 0
        )

        print(
            f"<= {threshold:>3} m: "
            f"{count:>4} ({pct:.2f}%)"
        )

    # --------------------------------------------------------
    # 2. DISTANCIA ENTRE PRIMER Y SEGUNDO CANDIDATO
    # --------------------------------------------------------

    candidate_distances = geographic[
        geographic["nearest_rank"].isin([1, 2])
    ].pivot_table(
        index="municipal_id",
        columns="nearest_rank",
        values="distance_m",
        aggfunc="min"
    )

    candidate_distances = candidate_distances.reset_index()

    candidate_distances = candidate_distances.rename(
        columns={
            1: "nearest_distance_m",
            2: "second_nearest_distance_m"
        }
    )

    if "second_nearest_distance_m" in candidate_distances.columns:

        candidate_distances["distance_difference_m"] = (
            candidate_distances["second_nearest_distance_m"]
            - candidate_distances["nearest_distance_m"]
        )

    else:

        candidate_distances["second_nearest_distance_m"] = pd.NA
        candidate_distances["distance_difference_m"] = pd.NA

    print("\n2. AMBIGÜEDAD GEOGRÁFICA")
    print("-" * 75)

    if "distance_difference_m" in candidate_distances.columns:

        for threshold in [5, 10, 25, 50]:

            ambiguous = (
                candidate_distances["distance_difference_m"]
                <= threshold
            ).sum()

            print(
                f"Estaciones cuyo 2.º candidato está a "
                f"<= {threshold} m de diferencia del primero: "
                f"{ambiguous:,}"
            )

    # --------------------------------------------------------
    # 3. ESTACIONES MUNICIPALES SIN CANDIDATO A 25 M
    # --------------------------------------------------------

    unmatched_25m = nearest[
        nearest["distance_m"] > 25
    ].copy()

    print("\n3. ESTACIONES SIN CRTM A 25 METROS")
    print("-" * 75)

    print(f"Total: {len(unmatched_25m):,}")

    if not unmatched_25m.empty:

        display_columns = [
            "municipal_id",
            "municipal_name",
            "crtm_id",
            "crtm_name",
            "crtm_system_name",
            "distance_m"
        ]

        available_columns = [
            col for col in display_columns
            if col in unmatched_25m.columns
        ]

        print(
            unmatched_25m[available_columns]
            .sort_values("distance_m")
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # 4. CRTM QUE SON CANDIDATO MÁS CERCANO A VARIAS MUNICIPALES
    # --------------------------------------------------------

    collisions = nearest.groupby(
        "crtm_id"
    ).agg(
        municipal_stations_assigned=("municipal_id", "nunique"),
        municipal_names=("municipal_name", "first"),
        crtm_name=("crtm_name", "first"),
        nearest_distance_min=("distance_m", "min"),
        nearest_distance_max=("distance_m", "max")
    ).reset_index()

    collisions = collisions[
        collisions["municipal_stations_assigned"] > 1
    ].sort_values(
        "municipal_stations_assigned",
        ascending=False
    )

    print("\n4. POSIBLES COLISIONES GEOGRÁFICAS")
    print("-" * 75)

    print(
        "CRTM que son el candidato más cercano a más de una "
        "estación municipal:",
        len(collisions)
    )

    if not collisions.empty:

        print(
            collisions.head(30).to_string(index=False)
        )

    # --------------------------------------------------------
    # 5. COINCIDENCIAS EXACTAS POR NOMBRE
    # --------------------------------------------------------

    print("\n5. COINCIDENCIAS EXACTAS POR NOMBRE")
    print("-" * 75)

    exact_pairs = exact[
        ["municipal_id", "crtm_id"]
    ].drop_duplicates()

    exact_municipal_counts = exact_pairs.groupby(
        "municipal_id"
    )["crtm_id"].nunique()

    exact_crtm_counts = exact_pairs.groupby(
        "crtm_id"
    )["municipal_id"].nunique()

    municipal_exact_unique = (
        exact_municipal_counts == 1
    ).sum()

    municipal_exact_multiple = (
        exact_municipal_counts > 1
    ).sum()

    municipal_exact_total = (
        exact_municipal_counts.index.nunique()
    )

    print(
        "Municipales con coincidencia exacta:",
        municipal_exact_total
    )

    print(
        "Municipales con exactamente 1 CRTM:",
        municipal_exact_unique
    )

    print(
        "Municipales con varios CRTM:",
        municipal_exact_multiple
    )

    print(
        "CRTM asociados a varias municipales:",
        (exact_crtm_counts > 1).sum()
    )

    exact_multiple = (
        exact_pairs.groupby("municipal_id")
        .filter(lambda x: x["crtm_id"].nunique() > 1)
    )

    # --------------------------------------------------------
    # 6. SIMILITUD DE NOMBRES
    # --------------------------------------------------------

    print("\n6. CANDIDATOS POR SIMILITUD DE NOMBRE")
    print("-" * 75)

    fuzzy["similarity_score"] = pd.to_numeric(
        fuzzy["similarity_score"],
        errors="coerce"
    )

    for threshold in [0.90, 0.85, 0.80, 0.75, 0.70]:

        count = (
            fuzzy["similarity_score"] >= threshold
        ).sum()

        print(
            f"Score >= {threshold:.2f}: {count:,} candidatos"
        )

    # --------------------------------------------------------
    # 7. EXPORTACIÓN
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    nearest.to_csv(
        OUTPUT_DIR / "nearest_crtm_candidate_per_municipal.csv",
        index=False,
        encoding="utf-8-sig"
    )

    candidate_distances.to_csv(
        OUTPUT_DIR / "geographic_ambiguity_audit.csv",
        index=False,
        encoding="utf-8-sig"
    )

    unmatched_25m.to_csv(
        OUTPUT_DIR / "municipal_stations_without_match_25m.csv",
        index=False,
        encoding="utf-8-sig"
    )

    collisions.to_csv(
        OUTPUT_DIR / "geographic_matching_collisions.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exact_pairs.to_csv(
        OUTPUT_DIR / "exact_name_unique_pairs.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exact_multiple.to_csv(
        OUTPUT_DIR / "exact_name_multiple_matches.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 75)
    print("ARCHIVOS DE AUDITORÍA GENERADOS")
    print("=" * 75)

    for file in OUTPUT_DIR.glob("*.csv"):

        print(
            f"{file.name} | "
            f"{file.stat().st_size / 1024:.2f} KB"
        )

    print("\nAUDITORÍA FINALIZADA")


if __name__ == "__main__":
    main()