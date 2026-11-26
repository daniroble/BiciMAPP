from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

OD_DIR = ROOT / "data" / "processed" / "od_clean"
CROSS_DIR = ROOT / "data" / "processed" / "cross_analysis"
OUT_DIR = ROOT / "analysis" / "validation"

OUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "filtered": OD_DIR / "od_recurrence_filtered.csv",
    "recurrence_rank": OD_DIR / "od_recurrence_rank.csv",
    "daily_rank": OD_DIR / "od_daily_demand_rank.csv",
    "total_rank": OD_DIR / "od_total_demand_rank.csv",
    "cross": CROSS_DIR / "od_station_cross_all.csv",
}

WEEKDAYS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def load_csv(path):
    if not path.exists():
        print(f"\nNO ENCONTRADO: {path}")
        return None

    df = pd.read_csv(path)

    print(f"\nArchivo: {path.name}")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {list(df.columns)}")

    return df


def to_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def audit_recurrence(df):
    section("1. CONTROL DE CALIDAD DEL ARCHIVO DE RECURRENCIA")

    required = [
        "weekday",
        "weekday_name",
        "hour",
        "origin_id",
        "origin_name",
        "destination_id",
        "destination_name",
        "total_trips",
        "active_days",
        "eligible_days",
        "recurrence_pct",
        "avg_trips_per_eligible_day",
        "avg_trips_per_active_day",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        print("ERROR: Faltan columnas necesarias:")
        print(missing)
        return None

    numeric_cols = [
        "weekday",
        "hour",
        "origin_id",
        "destination_id",
        "total_trips",
        "active_days",
        "eligible_days",
        "recurrence_pct",
        "avg_trips_per_eligible_day",
        "avg_trips_per_active_day",
    ]

    df = to_numeric(df, numeric_cols)

    print(f"Filas: {len(df):,}")
    print(f"Duplicados exactos: {df.duplicated().sum():,}")

    key = [
        "weekday",
        "hour",
        "origin_id",
        "destination_id",
    ]

    print(
        "Duplicados por ruta-día-hora:",
        df.duplicated(key, keep=False).sum(),
    )

    print("\nDías de semana:")
    print(sorted(df["weekday"].dropna().unique()))

    print("\nHoras:")
    print(sorted(df["hour"].dropna().unique()))

    print("\nDistribución de días elegibles:")
    print(df["eligible_days"].describe())

    print("\nDistribución de días activos:")
    print(df["active_days"].describe())

    section("2. CONTROLES LÓGICOS")

    bad_active = df[df["active_days"] > df["eligible_days"]]
    bad_trips = df[df["total_trips"] < df["active_days"]]
    bad_zero_active = df[df["active_days"] == 0]
    bad_eligible = df[df["eligible_days"] <= 0]

    print(f"active_days > eligible_days: {len(bad_active):,}")
    print(f"total_trips < active_days: {len(bad_trips):,}")
    print(f"active_days = 0: {len(bad_zero_active):,}")
    print(f"eligible_days <= 0: {len(bad_eligible):,}")

    section("3. RECÁLCULO DE INDICADORES")

    df["recurrence_recalculated"] = (
        df["active_days"] / df["eligible_days"] * 100
    )

    df["avg_per_eligible_recalculated"] = (
        df["total_trips"] / df["eligible_days"]
    )

    df["avg_per_active_recalculated"] = (
        df["total_trips"] / df["active_days"].replace(0, np.nan)
    )

    df["recurrence_diff"] = (
        df["recurrence_pct"] - df["recurrence_recalculated"]
    )

    df["avg_eligible_diff"] = (
        df["avg_trips_per_eligible_day"]
        - df["avg_per_eligible_recalculated"]
    )

    df["avg_active_diff"] = (
        df["avg_trips_per_active_day"]
        - df["avg_per_active_recalculated"]
    )

    print(
        "Máxima diferencia recurrencia:",
        df["recurrence_diff"].abs().max(),
    )

    print(
        "Máxima diferencia media/día elegible:",
        df["avg_eligible_diff"].abs().max(),
    )

    print(
        "Máxima diferencia media/día activo:",
        df["avg_active_diff"].abs().max(),
    )

    section("4. AUDITORÍA DE DENOMINADORES")

    denominator_table = (
        df.groupby(["weekday", "weekday_name", "hour"])
        ["eligible_days"]
        .agg(["min", "max", "nunique", "count"])
        .reset_index()
    )

    print(denominator_table.to_string(index=False))

    denominator_table.to_csv(
        OUT_DIR / "od_eligible_days_audit.csv",
        index=False,
    )

    section("5. TOP 25 POR RECURRENCIA")

    columns = [
        "weekday",
        "weekday_name",
        "hour",
        "origin_name",
        "destination_name",
        "total_trips",
        "active_days",
        "eligible_days",
        "recurrence_pct",
        "avg_trips_per_eligible_day",
        "avg_trips_per_active_day",
    ]

    top_recurrence = df.sort_values(
        ["recurrence_pct", "total_trips"],
        ascending=False,
    ).head(25)

    print(top_recurrence[columns].to_string(index=False))

    section("6. TOP 25 POR DEMANDA MEDIA DIARIA")

    top_daily = df.sort_values(
        ["avg_trips_per_eligible_day", "recurrence_pct"],
        ascending=False,
    ).head(25)

    print(top_daily[columns].to_string(index=False))

    section("7. TOP 25 POR VOLUMEN TOTAL")

    top_volume = df.sort_values(
        ["total_trips", "recurrence_pct"],
        ascending=False,
    ).head(25)

    print(top_volume[columns].to_string(index=False))

    section("8. RECURRENCIA ALTA, INTENSIDAD BAJA")

    low_intensity = df[
        (df["recurrence_pct"] >= 50)
        & (df["avg_trips_per_eligible_day"] < 1)
    ].sort_values(
        ["recurrence_pct", "total_trips"],
        ascending=False,
    )

    print(f"Rutas encontradas: {len(low_intensity):,}")

    if len(low_intensity):
        print(low_intensity[columns].head(30).to_string(index=False))

    # Exportaciones
    df.to_csv(
        OUT_DIR / "od_recurrence_audited.csv",
        index=False,
    )

    top_recurrence.to_csv(
        OUT_DIR / "od_top_recurrence_audited.csv",
        index=False,
    )

    top_daily.to_csv(
        OUT_DIR / "od_top_daily_demand_audited.csv",
        index=False,
    )

    top_volume.to_csv(
        OUT_DIR / "od_top_total_volume_audited.csv",
        index=False,
    )

    low_intensity.to_csv(
        OUT_DIR / "od_high_recurrence_low_intensity.csv",
        index=False,
    )

    return df


def compare_rank_file(name, df):
    section(f"9. ARCHIVO DE RANKING: {name}")

    if df is None:
        print("Archivo no disponible.")
        return

    print(f"Filas: {len(df):,}")
    print("Columnas:", list(df.columns))

    print("\nPrimeras 10 filas:")
    print(df.head(10).to_string(index=False))


def find_balance_column(df, side):
    """
    Busca columnas de balance para origen/destino
    sin asumir una única nomenclatura.
    """

    aliases = {
        "origin": [
            "origin_avg_balance",
            "origin_avg_daily_balance",
            "origin_avg_daily_net_balance",
            "avg_balance_origin",
            "origin_balance",
        ],
        "destination": [
            "destination_avg_balance",
            "destination_avg_daily_balance",
            "destination_avg_daily_net_balance",
            "avg_balance_destination",
            "destination_balance",
        ],
    }

    # 1. Coincidencia exacta con alias
    for col in aliases[side]:
        if col in df.columns:
            return col

    # 2. Búsqueda flexible
    side_words = (
        ["origin", "orig"]
        if side == "origin"
        else ["destination", "dest"]
    )

    candidates = []

    for col in df.columns:
        lower = col.lower()

        contains_side = any(word in lower for word in side_words)
        contains_balance = "balance" in lower

        if contains_side and contains_balance:
            candidates.append(col)

    if candidates:
        return candidates[0]

    return None


def audit_cross_analysis(cross):
    section("10. AUDITORÍA DEL CRUCE CON ESTACIONES")

    if cross is None:
        print("Archivo de cruce no disponible.")
        return

    print(f"Filas: {len(cross):,}")
    print("Columnas:")
    print(list(cross.columns))

    origin_col = find_balance_column(cross, "origin")
    destination_col = find_balance_column(cross, "destination")

    print("\nColumnas detectadas:")
    print(f"Balance origen: {origin_col}")
    print(f"Balance destino: {destination_col}")

    if origin_col is None:
        print(
            "\nNo se encontró columna de balance del origen. "
            "Se omite ese cálculo."
        )

    if destination_col is None:
        print(
            "\nNo se encontró columna de balance del destino. "
            "Se omite ese cálculo."
        )

    if origin_col:
        cross[origin_col] = pd.to_numeric(
            cross[origin_col],
            errors="coerce",
        )

    if destination_col:
        cross[destination_col] = pd.to_numeric(
            cross[destination_col],
            errors="coerce",
        )

    if origin_col and destination_col:

        origin_available = cross[origin_col].notna()
        destination_available = cross[destination_col].notna()

        both_available = (
            origin_available & destination_available
        )

        neither_available = (
            ~origin_available & ~destination_available
        )

        origin_only = (
            origin_available & ~destination_available
        )

        destination_only = (
            ~origin_available & destination_available
        )

        section("11. COBERTURA DEL DIAGNÓSTICO DE ESTACIONES")

        total = len(cross)

        print(f"Total rutas: {total:,}")
        print(
            f"Diagnóstico origen disponible: "
            f"{origin_available.sum():,} "
            f"({origin_available.mean() * 100:.2f}%)"
        )

        print(
            f"Diagnóstico destino disponible: "
            f"{destination_available.sum():,} "
            f"({destination_available.mean() * 100:.2f}%)"
        )

        print(
            f"Ambos disponibles: "
            f"{both_available.sum():,} "
            f"({both_available.mean() * 100:.2f}%)"
        )

        print(
            f"Solo origen: "
            f"{origin_only.sum():,} "
            f"({origin_only.mean() * 100:.2f}%)"
        )

        print(
            f"Solo destino: "
            f"{destination_only.sum():,} "
            f"({destination_only.mean() * 100:.2f}%)"
        )

        print(
            f"Ninguno disponible: "
            f"{neither_available.sum():,} "
            f"({neither_available.mean() * 100:.2f}%)"
        )

        coverage = pd.DataFrame(
            {
                "category": [
                    "origin_available",
                    "destination_available",
                    "both_available",
                    "origin_only",
                    "destination_only",
                    "neither_available",
                ],
                "count": [
                    origin_available.sum(),
                    destination_available.sum(),
                    both_available.sum(),
                    origin_only.sum(),
                    destination_only.sum(),
                    neither_available.sum(),
                ],
            }
        )

        coverage["pct"] = coverage["count"] / total * 100

        coverage.to_csv(
            OUT_DIR / "od_station_cross_coverage_audited.csv",
            index=False,
        )

    else:

        print(
            "\nNo se pueden calcular coberturas completas porque "
            "no se han detectado ambas columnas de balance."
        )

    cross.to_csv(
        OUT_DIR / "od_station_cross_audited.csv",
        index=False,
    )


def main():
    section("AUDITORÍA DE RECURRENCIA DE RUTAS OD")

    filtered = load_csv(FILES["filtered"])
    recurrence_rank = load_csv(FILES["recurrence_rank"])
    daily_rank = load_csv(FILES["daily_rank"])
    total_rank = load_csv(FILES["total_rank"])
    cross = load_csv(FILES["cross"])

    audited = None

    if filtered is not None:
        audited = audit_recurrence(filtered)

    compare_rank_file(
        "RECURRENCIA",
        recurrence_rank,
    )

    compare_rank_file(
        "DEMANDA DIARIA",
        daily_rank,
    )

    compare_rank_file(
        "VOLUMEN TOTAL",
        total_rank,
    )

    audit_cross_analysis(cross)

    section("12. FINAL")

    print("Auditoría completada.")
    print(f"Resultados exportados a: {OUT_DIR}")


if __name__ == "__main__":
    main()