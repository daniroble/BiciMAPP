# src/audit_crtm_final_exceptions.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BASE = ROOT / "data" / "processed" / "crtm_integration"
REVIEW = BASE / "match_review"
OUTPUT = REVIEW / "final_audit"

EXACT_FILE = REVIEW / "exact_match_review.csv"
NO_EXACT_FILE = REVIEW / "municipal_without_exact_match_review.csv"
CRTM_NO_EXACT_FILE = REVIEW / "crtm_without_exact_match.csv"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    return pd.read_csv(path, low_memory=False)


def main():

    print("\n" + "=" * 78)
    print("AUDITORÍA FINAL DE EXCEPCIONES CRTM")
    print("=" * 78)

    exact = read_csv(EXACT_FILE)
    no_exact = read_csv(NO_EXACT_FILE)
    crtm_no_exact = read_csv(CRTM_NO_EXACT_FILE)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # 1. NORMALIZAR TIPOS
    # ======================================================

    numeric_columns = [
        "municipal_id",
        "crtm_id",
        "exact_crtm_matches",
        "municipal_matches_for_crtm",
        "exact_name_distance_m",
        "nearest_crtm_id",
        "nearest_distance_m",
    ]

    for df in [exact, no_exact]:

        for col in numeric_columns:

            if col in df.columns:

                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

    # ======================================================
    # 2. COMPROBAR DUPLICADOS
    # ======================================================

    print("\n1. CONTROL DE DUPLICADOS")
    print("-" * 78)

    print(
        "Filas de match exacto:",
        len(exact)
    )

    print(
        "Municipales únicas en matches exactos:",
        exact["municipal_id"].nunique()
    )

    print(
        "CRTM únicos en matches exactos:",
        exact["crtm_id"].nunique()
    )

    duplicate_municipal_rows = exact[
        exact.duplicated(
            "municipal_id",
            keep=False
        )
    ].sort_values("municipal_id")

    duplicate_crtm_rows = exact[
        exact.duplicated(
            "crtm_id",
            keep=False
        )
    ].sort_values("crtm_id")

    print(
        "Municipales con varias filas de matching:",
        duplicate_municipal_rows["municipal_id"].nunique()
    )

    print(
        "CRTM con varias filas de matching:",
        duplicate_crtm_rows["crtm_id"].nunique()
    )

    # ======================================================
    # 3. MATCHES EXACTOS DE ALTA CONFIANZA
    # ======================================================

    high_confidence = exact[
        (exact["exact_crtm_matches"] == 1)
        & (exact["municipal_matches_for_crtm"] == 1)
        & (exact["exact_name_distance_m"] <= 25)
        & (exact["exact_match_is_nearest"] == True)
    ].copy()

    high_confidence_unique = (
        high_confidence
        .drop_duplicates("municipal_id")
        .copy()
    )

    print("\n2. MATCHES DE ALTA CONFIANZA")
    print("-" * 78)

    print(
        "Filas de alta confianza:",
        len(high_confidence)
    )

    print(
        "Municipales únicas de alta confianza:",
        high_confidence_unique["municipal_id"].nunique()
    )

    print(
        "CRTM únicos en alta confianza:",
        high_confidence_unique["crtm_id"].nunique()
    )

    # ======================================================
    # 4. MATCHES EXACTOS QUE NECESITAN REVISIÓN
    # ======================================================

    exact_review_cases = exact[
        ~(
            (exact["exact_crtm_matches"] == 1)
            & (exact["municipal_matches_for_crtm"] == 1)
            & (exact["exact_name_distance_m"] <= 25)
            & (exact["exact_match_is_nearest"] == True)
        )
    ].copy()

    print("\n3. MATCHES EXACTOS QUE NECESITAN REVISIÓN")
    print("-" * 78)

    print(
        "Filas:",
        len(exact_review_cases)
    )

    if not exact_review_cases.empty:

        print(
            exact_review_cases[
                [
                    "municipal_id",
                    "municipal_name",
                    "crtm_id",
                    "crtm_name",
                    "exact_name_distance_m",
                    "exact_crtm_matches",
                    "municipal_matches_for_crtm",
                    "nearest_crtm_id",
                    "nearest_distance_m",
                    "exact_match_is_nearest",
                    "provisional_status"
                ]
            ]
            .sort_values(
                "exact_name_distance_m",
                ascending=False
            )
            .head(30)
            .to_string(index=False)
        )

    # ======================================================
    # 5. MUNICIPALES SIN MATCH EXACTO
    # ======================================================

    print("\n4. MUNICIPALES SIN MATCH EXACTO")
    print("-" * 78)

    print(
        "Total:",
        len(no_exact)
    )

    if not no_exact.empty:

        print(
            no_exact[
                [
                    "municipal_id",
                    "municipal_name",
                    "nearest_crtm_id",
                    "nearest_crtm_name",
                    "nearest_distance_m",
                    "second_distance_m",
                    "distance_gap_m",
                    "provisional_status"
                ]
            ]
            .sort_values("nearest_distance_m")
            .to_string(index=False)
        )

    # ======================================================
    # 6. CANDIDATOS ESPACIALES SIN MATCH EXACTO
    # ======================================================

    spatial_candidates = no_exact[
        no_exact["nearest_distance_m"] <= 25
    ].copy()

    spatial_candidates = spatial_candidates.sort_values(
        ["nearest_distance_m", "distance_gap_m"],
        ascending=[True, False]
    )

    print("\n5. CANDIDATOS ESPACIALES SIN MATCH EXACTO <=25 M")
    print("-" * 78)

    print(
        "Total:",
        len(spatial_candidates)
    )

    # ======================================================
    # 7. ESTACIONES CRTM SIN MATCH EXACTO
    # ======================================================

    print("\n6. CRTM SIN MATCH EXACTO")
    print("-" * 78)

    print(
        "Total:",
        len(crtm_no_exact)
    )

    # ======================================================
    # 8. EXPORTAR
    # ======================================================

    high_confidence_unique.to_csv(
        OUTPUT / "high_confidence_exact_matches.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exact_review_cases.to_csv(
        OUTPUT / "exact_matches_requiring_review.csv",
        index=False,
        encoding="utf-8-sig"
    )

    spatial_candidates.to_csv(
        OUTPUT / "spatial_candidates_without_exact_name.csv",
        index=False,
        encoding="utf-8-sig"
    )

    duplicate_municipal_rows.to_csv(
        OUTPUT / "duplicate_municipal_matching_rows.csv",
        index=False,
        encoding="utf-8-sig"
    )

    duplicate_crtm_rows.to_csv(
        OUTPUT / "duplicate_crtm_matching_rows.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ======================================================
    # 9. RESUMEN FINAL
    # ======================================================

    summary = pd.DataFrame(
        [
            {
                "metric": "exact_matching_rows",
                "value": len(exact)
            },
            {
                "metric": "municipal_unique_exact",
                "value": exact["municipal_id"].nunique()
            },
            {
                "metric": "crtm_unique_exact",
                "value": exact["crtm_id"].nunique()
            },
            {
                "metric": "high_confidence_municipal_unique",
                "value": high_confidence_unique["municipal_id"].nunique()
            },
            {
                "metric": "high_confidence_crtm_unique",
                "value": high_confidence_unique["crtm_id"].nunique()
            },
            {
                "metric": "exact_matches_requiring_review",
                "value": len(exact_review_cases)
            },
            {
                "metric": "municipal_without_exact_match",
                "value": len(no_exact)
            },
            {
                "metric": "spatial_candidates_without_exact_name_25m",
                "value": len(spatial_candidates)
            },
            {
                "metric": "crtm_without_exact_match",
                "value": len(crtm_no_exact)
            },
        ]
    )

    summary.to_csv(
        OUTPUT / "final_audit_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n7. RESUMEN EXPORTADO")
    print("-" * 78)

    print(summary.to_string(index=False))

    print("\nARCHIVOS GENERADOS")
    print("-" * 78)

    for file in sorted(OUTPUT.glob("*.csv")):

        print(
            f"{file.name} | "
            f"{file.stat().st_size / 1024:.2f} KB"
        )

    print("\nAUDITORÍA FINAL TERMINADA")


if __name__ == "__main__":
    main()