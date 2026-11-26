# src/audit_crtm_station_matching.py

from pathlib import Path
import re
import unicodedata
import pandas as pd
from difflib import SequenceMatcher


# ============================================================
# CONFIGURACIÓN
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MUNICIPAL_FILE = ROOT / "data" / "raw" / "bikestationbicimad_csv.csv"
CRTM_FILE = ROOT / "data" / "raw" / "Bici_Publica_TP_-7733901207477329617.csv"

OUTPUT_DIR = ROOT / "data" / "processed" / "crtm_integration"

# Umbrales de proximidad (metros)
DISTANCES = [25, 50, 100, 250]


# ============================================================
# UTILIDADES
# ============================================================

def normalize_name(value):
    """Normaliza nombres para comparar estaciones."""

    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    # Eliminar acentos
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )

    # Eliminar prefijos numéricos como '2 - ', '123 - ', etc.
    text = re.sub(r"^\s*\d+\s*[-–—]\s*", "", text)

    # Normalizar puntuación y espacios
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_coordinate(value):
    """Convierte coordenadas con coma o punto decimal."""

    if pd.isna(value):
        return None

    text = str(value).strip().replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def haversine_meters(lon1, lat1, lon2, lat2):
    """Calcula distancia geográfica entre dos coordenadas."""

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


def read_csv_safely(path, separator):
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo:\n{path}")

    return pd.read_csv(
        path,
        sep=separator,
        encoding="utf-8",
        low_memory=False
    )


# ============================================================
# CARGA Y LIMPIEZA DE FUENTES
# ============================================================

def load_municipal_stations():

    print("\n" + "=" * 70)
    print("CARGANDO DATASET MUNICIPAL BICIMAD")
    print("=" * 70)

    df = read_csv_safely(MUNICIPAL_FILE, separator=";")

    required_columns = [
        "OBJECTID",
        "Name",
        "Address",
        "TotalBases",
        "State",
        "POINT_X",
        "POINT_Y"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Faltan columnas en el dataset municipal: {missing}"
        )

    df = df.copy()

    df["municipal_id"] = df["OBJECTID"]
    df["municipal_name"] = df["Name"].astype(str).str.strip()
    df["municipal_name_normalized"] = (
        df["municipal_name"].apply(normalize_name)
    )

    df["municipal_lon"] = df["POINT_X"].apply(parse_coordinate)
    df["municipal_lat"] = df["POINT_Y"].apply(parse_coordinate)

    df["municipal_bases"] = pd.to_numeric(
        df["TotalBases"],
        errors="coerce"
    )

    df["municipal_state"] = df["State"]

    print(f"Filas municipales: {len(df):,}")
    print(
        "Coordenadas válidas:",
        df[["municipal_lon", "municipal_lat"]]
        .notna()
        .all(axis=1)
        .sum()
    )
    print(
        "Nombres únicos:",
        df["municipal_name_normalized"].nunique()
    )

    return df


def load_crtm_stations():

    print("\n" + "=" * 70)
    print("CARGANDO DATASET CRTM")
    print("=" * 70)

    df = read_csv_safely(CRTM_FILE, separator=",")

    required_columns = [
        "OBJECTID",
        "DS_STATION",
        "DS_STATI_1",
        "NM_TOTAL_B",
        "DS_LONGITU",
        "DS_LATITUD"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Faltan columnas en el dataset CRTM: {missing}"
        )

    df = df.copy()

    df["crtm_id"] = df["OBJECTID"]

    df["crtm_name"] = (
        df["DS_STATI_1"]
        .fillna(df["DS_STATION"])
        .astype(str)
        .str.strip()
    )

    df["crtm_system_name"] = (
        df["DS_STATION"]
        .astype(str)
        .str.strip()
    )

    df["crtm_name_normalized"] = (
        df["crtm_name"].apply(normalize_name)
    )

    df["crtm_system_normalized"] = (
        df["crtm_system_name"].apply(normalize_name)
    )

    df["crtm_lon"] = pd.to_numeric(
        df["DS_LONGITU"],
        errors="coerce"
    )

    df["crtm_lat"] = pd.to_numeric(
        df["DS_LATITUD"],
        errors="coerce"
    )

    df["crtm_bikes"] = pd.to_numeric(
        df["NM_TOTAL_B"],
        errors="coerce"
    )

    print(f"Filas CRTM: {len(df):,}")
    print(
        "Coordenadas válidas:",
        df[["crtm_lon", "crtm_lat"]]
        .notna()
        .all(axis=1)
        .sum()
    )
    print(
        "Nombres únicos:",
        df["crtm_name_normalized"].nunique()
    )
    print(
        "Sistemas/nombres de sistema únicos:",
        df["crtm_system_normalized"].nunique()
    )

    return df


# ============================================================
# MATCHING POR NOMBRE
# ============================================================

def exact_name_matching(municipal, crtm):

    print("\n" + "=" * 70)
    print("MATCHING EXACTO POR NOMBRE NORMALIZADO")
    print("=" * 70)

    # Crear claves para los dos campos descriptivos CRTM
    crtm_name_matches = crtm[
        [
            "crtm_id",
            "crtm_name",
            "crtm_system_name",
            "crtm_name_normalized",
            "crtm_system_normalized",
            "crtm_lon",
            "crtm_lat",
            "crtm_bikes"
        ]
    ].copy()

    # Coincidencia con nombre descriptivo
    matches_station_name = municipal.merge(
        crtm_name_matches,
        left_on="municipal_name_normalized",
        right_on="crtm_name_normalized",
        how="inner"
    )

    matches_station_name["match_type"] = "exact_name_crtm_station"

    # Coincidencia con el otro campo de nombre CRTM
    matches_system_name = municipal.merge(
        crtm_name_matches,
        left_on="municipal_name_normalized",
        right_on="crtm_system_normalized",
        how="inner"
    )

    matches_system_name["match_type"] = "exact_name_crtm_system"

    matches = pd.concat(
        [
            matches_station_name,
            matches_system_name
        ],
        ignore_index=True
    )

    # Eliminar coincidencias duplicadas
    matches = matches.drop_duplicates(
        subset=["municipal_id", "crtm_id", "match_type"]
    )

    print(
        "Coincidencias exactas por nombre:",
        len(matches)
    )

    return matches


# ============================================================
# MATCHING GEOGRÁFICO
# ============================================================

def geographic_matching(municipal, crtm):

    print("\n" + "=" * 70)
    print("MATCHING GEOGRÁFICO")
    print("=" * 70)

    municipal_valid = municipal.dropna(
        subset=["municipal_lon", "municipal_lat"]
    ).copy()

    crtm_valid = crtm.dropna(
        subset=["crtm_lon", "crtm_lat"]
    ).copy()

    results = []

    for _, municipal_row in municipal_valid.iterrows():

        distances = []

        for _, crtm_row in crtm_valid.iterrows():

            distance = haversine_meters(
                municipal_row["municipal_lon"],
                municipal_row["municipal_lat"],
                crtm_row["crtm_lon"],
                crtm_row["crtm_lat"]
            )

            distances.append({
                "municipal_id": municipal_row["municipal_id"],
                "municipal_name": municipal_row["municipal_name"],
                "municipal_name_normalized": (
                    municipal_row["municipal_name_normalized"]
                ),
                "municipal_lon": municipal_row["municipal_lon"],
                "municipal_lat": municipal_row["municipal_lat"],
                "municipal_bases": municipal_row["municipal_bases"],
                "municipal_state": municipal_row["municipal_state"],
                "crtm_id": crtm_row["crtm_id"],
                "crtm_name": crtm_row["crtm_name"],
                "crtm_system_name": crtm_row["crtm_system_name"],
                "crtm_lon": crtm_row["crtm_lon"],
                "crtm_lat": crtm_row["crtm_lat"],
                "crtm_bikes": crtm_row["crtm_bikes"],
                "distance_m": distance
            })

        station_distances = pd.DataFrame(distances)

        station_distances = station_distances.sort_values(
            "distance_m"
        )

        # Guardar los 5 candidatos más próximos
        top_candidates = station_distances.head(5).copy()

        top_candidates["nearest_rank"] = range(
            1,
            len(top_candidates) + 1
        )

        # Número de candidatos dentro de diferentes radios
        for threshold in DISTANCES:

            count = (
                station_distances["distance_m"]
                <= threshold
            ).sum()

            top_candidates[
                f"crtm_candidates_within_{threshold}m"
            ] = count

        results.append(top_candidates)

    if results:

        result = pd.concat(
            results,
            ignore_index=True
        )

    else:

        result = pd.DataFrame()

    print(f"Candidatos geográficos generados: {len(result):,}")

    return result


# ============================================================
# AUDITORÍA DE COBERTURA
# ============================================================

def summarize_geographic_coverage(geographic_candidates):

    print("\n" + "=" * 70)
    print("RESUMEN DE COBERTURA GEOGRÁFICA")
    print("=" * 70)

    if geographic_candidates.empty:
        return pd.DataFrame()

    nearest = geographic_candidates[
        geographic_candidates["nearest_rank"] == 1
    ].copy()

    rows = []

    for threshold in DISTANCES:

        matched = (
            nearest["distance_m"] <= threshold
        ).sum()

        total = len(nearest)

        percentage = (
            matched / total * 100
            if total > 0
            else 0
        )

        rows.append({
            "threshold_m": threshold,
            "municipal_stations": total,
            "nearest_crtm_within_threshold": matched,
            "percentage": percentage
        })

        print(
            f"{threshold:>3} m: "
            f"{matched:,}/{total:,} "
            f"({percentage:.2f}%)"
        )

    return pd.DataFrame(rows)


# ============================================================
# MATCHING POR NOMBRE SIMILAR
# ============================================================

def fuzzy_name_candidates(municipal, crtm):

    print("\n" + "=" * 70)
    print("CANDIDATOS POR SIMILITUD DE NOMBRE")
    print("=" * 70)

    results = []

    for _, municipal_row in municipal.iterrows():

        municipal_name = (
            municipal_row["municipal_name_normalized"]
        )

        if not municipal_name:
            continue

        for _, crtm_row in crtm.iterrows():

            names_to_compare = [
                crtm_row["crtm_name_normalized"],
                crtm_row["crtm_system_normalized"]
            ]

            for crtm_name in names_to_compare:

                if not crtm_name:
                    continue

                score = SequenceMatcher(
                    None,
                    municipal_name,
                    crtm_name
                ).ratio()

                if score >= 0.70:

                    results.append({
                        "municipal_id": municipal_row["municipal_id"],
                        "municipal_name": municipal_row["municipal_name"],
                        "municipal_name_normalized": municipal_name,
                        "crtm_id": crtm_row["crtm_id"],
                        "crtm_name": crtm_row["crtm_name"],
                        "crtm_system_name": crtm_row["crtm_system_name"],
                        "crtm_name_normalized": crtm_name,
                        "similarity_score": score
                    })

    result = pd.DataFrame(results)

    if not result.empty:

        result = result.sort_values(
            "similarity_score",
            ascending=False
        )

        result = result.drop_duplicates(
            subset=["municipal_id", "crtm_id"]
        )

    print(
        "Candidatos de similitud de nombre:",
        len(result)
    )

    return result


# ============================================================
# EXPORTACIÓN
# ============================================================

def export_results(
    municipal,
    crtm,
    exact_matches,
    geographic_candidates,
    geographic_summary,
    fuzzy_candidates
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    municipal.to_csv(
        OUTPUT_DIR / "municipal_stations_clean.csv",
        index=False,
        encoding="utf-8-sig"
    )

    crtm.to_csv(
        OUTPUT_DIR / "crtm_stations_clean.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exact_matches.to_csv(
        OUTPUT_DIR / "exact_name_matches.csv",
        index=False,
        encoding="utf-8-sig"
    )

    geographic_candidates.to_csv(
        OUTPUT_DIR / "geographic_matching_candidates.csv",
        index=False,
        encoding="utf-8-sig"
    )

    geographic_summary.to_csv(
        OUTPUT_DIR / "geographic_matching_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    fuzzy_candidates.to_csv(
        OUTPUT_DIR / "fuzzy_name_candidates.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 70)
    print("ARCHIVOS GENERADOS")
    print("=" * 70)

    for file in OUTPUT_DIR.glob("*.csv"):

        print(
            f"{file.name} "
            f"({file.stat().st_size / 1024:.2f} KB)"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("AUDITORÍA DE INTEGRACIÓN MUNICIPAL - CRTM")
    print("=" * 70)

    municipal = load_municipal_stations()
    crtm = load_crtm_stations()

    exact_matches = exact_name_matching(
        municipal,
        crtm
    )

    geographic_candidates = geographic_matching(
        municipal,
        crtm
    )

    geographic_summary = summarize_geographic_coverage(
        geographic_candidates
    )

    fuzzy_candidates = fuzzy_name_candidates(
        municipal,
        crtm
    )

    export_results(
        municipal,
        crtm,
        exact_matches,
        geographic_candidates,
        geographic_summary,
        fuzzy_candidates
    )

    print("\nAUDITORÍA TERMINADA")
    print(
        "No se ha realizado todavía una integración definitiva."
    )
    print(
        "Los resultados son candidatos de correspondencia "
        "y deben validarse."
    )


if __name__ == "__main__":
    main()