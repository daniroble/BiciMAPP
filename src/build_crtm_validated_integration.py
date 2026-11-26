# src/build_crtm_validated_integration.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BASE = ROOT / "data" / "processed" / "crtm_integration"
REVIEW = BASE / "match_review"
AUDIT = REVIEW / "final_audit"

HIGH_CONFIDENCE_FILE = (
    AUDIT / "high_confidence_exact_matches.csv"
)

EXACT_REVIEW_FILE = (
    AUDIT / "exact_matches_requiring_review.csv"
)

SPATIAL_CANDIDATES_FILE = (
    AUDIT / "spatial_candidates_without_exact_name.csv"
)

NO_EXACT_FILE = (
    REVIEW / "municipal_without_exact_match_review.csv"
)

CRTM_NO_EXACT_FILE = (
    REVIEW / "crtm_without_exact_match.csv"
)

OUTPUT = BASE / "validated_integration"


def load_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"No se encuentra el archivo:\n{path}"
        )

    return pd.read_csv(
        path,
        low_memory=False
    )


def require_columns(df, columns, source_name):

    missing = [
        col
        for col in columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            f"\nFaltan columnas en {source_name}:\n"
            f"{missing}\n\n"
            f"Columnas disponibles:\n"
            f"{list(df.columns)}"
        )


def main():

    print("\n" + "=" * 78)
    print("CONSTRUCCIÓN DE INTEGRACIÓN CRTM VALIDADA")
    print("=" * 78)

    high = load_csv(
        HIGH_CONFIDENCE_FILE
    )

    exact_review = load_csv(
        EXACT_REVIEW_FILE
    )

    spatial = load_csv(
        SPATIAL_CANDIDATES_FILE
    )

    no_exact = load_csv(
        NO_EXACT_FILE
    )

    crtm_no_exact = load_csv(
        CRTM_NO_EXACT_FILE
    )

    # ------------------------------------------------------
    # 1. VALIDACIÓN DE ESTRUCTURA
    # ------------------------------------------------------

    required = [
        "municipal_id",
        "municipal_name",
        "municipal_lon",
        "municipal_lat",
        "crtm_id",
        "crtm_name",
        "crtm_system_name",
        "crtm_lon",
        "crtm_lat",
        "exact_name_distance_m",
        "exact_match_is_nearest",
        "municipal_bases",
        "crtm_bikes",
    ]

    require_columns(
        high,
        required,
        "high_confidence_exact_matches.csv"
    )

    print("\n1. VALIDACIÓN DE DATOS")
    print("-" * 78)

    print(
        "Filas de alta confianza:",
        len(high)
    )

    print(
        "IDs municipales únicos:",
        high["municipal_id"].nunique()
    )

    print(
        "IDs CRTM únicos:",
        high["crtm_id"].nunique()
    )

    # ------------------------------------------------------
    # 2. CONTROL DE UNICIDAD
    # ------------------------------------------------------

    duplicate_municipal = high[
        high.duplicated(
            "municipal_id",
            keep=False
        )
    ]

    duplicate_crtm = high[
        high.duplicated(
            "crtm_id",
            keep=False
        )
    ]

    if not duplicate_municipal.empty:

        raise ValueError(
            "ERROR: existen municipales duplicadas "
            "en la tabla de alta confianza."
        )

    if not duplicate_crtm.empty:

        raise ValueError(
            "ERROR: existen IDs CRTM duplicados "
            "en la tabla de alta confianza."
        )

    if len(high) != high["municipal_id"].nunique():

        raise ValueError(
            "ERROR: el número de filas no coincide "
            "con el número de municipales únicas."
        )

    if len(high) != high["crtm_id"].nunique():

        raise ValueError(
            "ERROR: el número de filas no coincide "
            "con el número de CRTM únicos."
        )

    print(
        "Control de unicidad: OK"
    )

    # ------------------------------------------------------
    # 3. DISTANCIA Y CONTROL DE UMBRAL
    # ------------------------------------------------------

    high["exact_name_distance_m"] = pd.to_numeric(
        high["exact_name_distance_m"],
        errors="coerce"
    )

    invalid_distance = high[
        high["exact_name_distance_m"] > 25
    ]

    if not invalid_distance.empty:

        raise ValueError(
            "ERROR: hay matches de alta confianza "
            "con distancia superior a 25 metros."
        )

    not_nearest = high[
        high["exact_match_is_nearest"] != True
    ]

    if not not_nearest.empty:

        raise ValueError(
            "ERROR: hay matches de alta confianza "
            "que no son el candidato geográfico más cercano."
        )

    print(
        "Control de distancia <=25 m: OK"
    )

    print(
        "Control de candidato más cercano: OK"
    )

    # ------------------------------------------------------
    # 4. CREAR TABLA DE INTEGRACIÓN
    # ------------------------------------------------------

    integration = high[
        [
            "municipal_id",
            "municipal_name",
            "municipal_lon",
            "municipal_lat",
            "municipal_bases",
            "municipal_state",
            "crtm_id",
            "crtm_name",
            "crtm_system_name",
            "crtm_lon",
            "crtm_lat",
            "crtm_bikes",
            "exact_name_distance_m",
        ]
    ].copy()

    integration = integration.rename(
        columns={
            "municipal_id": "bicimad_station_id",
            "municipal_name": "bicimad_station_name",
            "municipal_lon": "bicimad_lon",
            "municipal_lat": "bicimad_lat",
            "municipal_bases": "bicimad_bases",
            "municipal_state": "bicimad_state",
            "crtm_id": "crtm_station_id",
            "crtm_name": "crtm_station_name",
            "crtm_system_name": "crtm_system",
            "crtm_lon": "crtm_lon",
            "crtm_lat": "crtm_lat",
            "crtm_bikes": "crtm_inventory_field",
            "exact_name_distance_m": "match_distance_m",
        }
    )

    integration["match_method"] = (
        "normalized_exact_name"
    )

    integration["match_confidence"] = (
        "high"
    )

    integration["match_validation"] = (
        "exact_name_unique_both_sides"
        "_distance_le_25m_nearest_candidate"
    )

    integration["source_municipal"] = (
        "Madrid BiciMAD municipal dataset"
    )

    integration["source_crtm"] = (
        "CRTM Bici Publica TP dataset"
    )

    # ------------------------------------------------------
    # 5. CREAR TABLA DE EXCEPCIONES
    # ------------------------------------------------------

    exception_summary = pd.DataFrame(
        [
            {
                "exception_group": (
                    "exact_matches_requiring_review"
                ),
                "rows": len(exact_review),
                "description": (
                    "Exact name matches with distance, "
                    "multiplicity or nearest-candidate issues"
                ),
            },
            {
                "exception_group": (
                    "municipal_without_exact_name"
                ),
                "rows": len(no_exact),
                "description": (
                    "Municipal stations without exact "
                    "normalized name match"
                ),
            },
            {
                "exception_group": (
                    "spatial_candidates_without_exact_name"
                ),
                "rows": len(spatial),
                "description": (
                    "Potential geographic candidates "
                    "within 25m, not validated"
                ),
            },
            {
                "exception_group": (
                    "crtm_without_exact_name"
                ),
                "rows": len(crtm_no_exact),
                "description": (
                    "CRTM stations without exact "
                    "municipal name association"
                ),
            },
        ]
    )

    # ------------------------------------------------------
    # 6. RESUMEN
    # ------------------------------------------------------

    total_municipal = 631
    total_crtm = 625

    summary = pd.DataFrame(
        [
            {
                "metric": "municipal_total",
                "value": total_municipal,
            },
            {
                "metric": "crtm_total",
                "value": total_crtm,
            },
            {
                "metric": "validated_high_confidence_matches",
                "value": len(integration),
            },
            {
                "metric": "municipal_coverage_pct",
                "value": round(
                    len(integration)
                    / total_municipal
                    * 100,
                    2
                ),
            },
            {
                "metric": "crtm_coverage_pct",
                "value": round(
                    len(integration)
                    / total_crtm
                    * 100,
                    2
                ),
            },
            {
                "metric": "mean_match_distance_m",
                "value": round(
                    integration[
                        "match_distance_m"
                    ].mean(),
                    3
                ),
            },
            {
                "metric": "max_match_distance_m",
                "value": round(
                    integration[
                        "match_distance_m"
                    ].max(),
                    3
                ),
            },
        ]
    )

    # ------------------------------------------------------
    # 7. EXPORTAR
    # ------------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    integration.to_csv(
        OUTPUT / "bicimad_crtm_validated_599.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exception_summary.to_csv(
        OUTPUT / "matching_exceptions_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    summary.to_csv(
        OUTPUT / "validated_integration_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Guardar también los casos de revisión completos
    exact_review.to_csv(
        OUTPUT / "exact_matches_for_manual_review.csv",
        index=False,
        encoding="utf-8-sig"
    )

    spatial.to_csv(
        OUTPUT / "spatial_candidates_not_integrated.csv",
        index=False,
        encoding="utf-8-sig"
    )

    no_exact.to_csv(
        OUTPUT / "municipal_without_exact_match.csv",
        index=False,
        encoding="utf-8-sig"
    )

    crtm_no_exact.to_csv(
        OUTPUT / "crtm_without_exact_match.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ------------------------------------------------------
    # 8. INFORME DE CONSOLA
    # ------------------------------------------------------

    print("\n2. TABLA DE INTEGRACIÓN")
    print("-" * 78)

    print(
        "Matches validados:",
        len(integration)
    )

    print(
        "Municipales únicas:",
        integration["bicimad_station_id"].nunique()
    )

    print(
        "CRTM únicos:",
        integration["crtm_station_id"].nunique()
    )

    print(
        "Distancia media:",
        round(
            integration["match_distance_m"].mean(),
            2
        ),
        "m"
    )

    print(
        "Distancia máxima:",
        round(
            integration["match_distance_m"].max(),
            2
        ),
        "m"
    )

    print("\n3. COBERTURA")
    print("-" * 78)

    print(
        f"Cobertura municipal: "
        f"{len(integration) / total_municipal * 100:.2f}%"
    )

    print(
        f"Cobertura CRTM: "
        f"{len(integration) / total_crtm * 100:.2f}%"
    )

    print("\n4. RESUMEN")
    print("-" * 78)

    print(
        summary.to_string(index=False)
    )

    print("\n5. ARCHIVOS GENERADOS")
    print("-" * 78)

    for file in sorted(
        OUTPUT.glob("*.csv")
    ):

        print(
            f"{file.name} | "
            f"{file.stat().st_size / 1024:.2f} KB"
        )

    print("\nINTEGRACIÓN VALIDADA GENERADA")
    print(
        "Se han integrado únicamente los matches "
        "de alta confianza."
    )


if __name__ == "__main__":
    main()