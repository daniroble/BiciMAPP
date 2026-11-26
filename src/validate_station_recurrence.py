# src/validate_station_recurrence.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

FILE = (
    ROOT
    / "data"
    / "processed"
    / "station_time_recurrence.csv"
)

OUTPUT_DIR = (
    ROOT
    / "analysis"
    / "validation"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def section(title):

    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def format_table(df, columns):

    formatters = {
        "avg_daily_departures": "{:.2f}".format,
        "avg_daily_arrivals": "{:.2f}".format,
        "avg_daily_balance": "{:.2f}".format,
        "positive_days_pct": "{:.2f}%".format,
        "negative_days_pct": "{:.2f}%".format,
        "balanced_days_pct": "{:.2f}%".format,
        "avg_daily_activity": "{:.2f}".format,
        "avg_abs_daily_balance": "{:.2f}".format,
    }

    formatters = {
        col: formatter
        for col, formatter in formatters.items()
        if col in columns
    }

    return df[columns].to_string(
        index=False,
        formatters=formatters
    )


def main():

    section(
        "AUDITORÍA DE DESEQUILIBRIOS RECURRENTES POR ESTACIÓN"
    )

    if not FILE.exists():

        print(f"ERROR: No existe el archivo:\n{FILE}")
        return

    df = pd.read_csv(
        FILE,
        low_memory=False
    )

    print("\nARCHIVO")
    print("-" * 100)

    print(f"Ruta: {FILE}")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {list(df.columns)}")

    required = [
        "station_id",
        "station_name",
        "weekday_num",
        "hour",
        "observed_days",
        "avg_daily_departures",
        "avg_daily_arrivals",
        "avg_daily_balance",
        "avg_abs_daily_balance",
        "avg_daily_activity",
        "positive_days",
        "negative_days",
        "balanced_days",
        "positive_days_pct",
        "negative_days_pct",
        "balanced_days_pct",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        print("\nERROR: Faltan columnas:")
        print(missing)

        print("\nMuestra del archivo:")
        print(df.head(10).to_string(index=False))

        return

    # ======================================================
    # 1. NORMALIZACIÓN DE TIPOS
    # ======================================================

    numeric_cols = [
        "station_id",
        "weekday_num",
        "hour",
        "observed_days",
        "avg_daily_departures",
        "avg_daily_arrivals",
        "avg_daily_balance",
        "avg_abs_daily_balance",
        "avg_daily_activity",
        "positive_days",
        "negative_days",
        "balanced_days",
        "positive_days_pct",
        "negative_days_pct",
        "balanced_days_pct",
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df["station_name"] = (
        df["station_name"]
        .fillna("SIN NOMBRE")
        .astype(str)
    )

    # ======================================================
    # 2. CONTROL DE CALIDAD
    # ======================================================

    section(
        "1. CONTROL DE CALIDAD Y ESTRUCTURA"
    )

    print(
        "Estaciones únicas:",
        df["station_id"].nunique()
    )

    print(
        "Combinaciones estación-día-hora:",
        len(df)
    )

    print(
        "Horas:",
        sorted(
            df["hour"]
            .dropna()
            .unique()
            .tolist()
        )
    )

    print(
        "Días de semana:",
        sorted(
            df["weekday_num"]
            .dropna()
            .unique()
            .tolist()
        )
    )

    duplicate_count = df.duplicated(
        [
            "station_id",
            "weekday_num",
            "hour"
        ]
    ).sum()

    print(
        "Duplicados estación-día-hora:",
        duplicate_count
    )

    print("\nDías observados:")

    print(
        df["observed_days"]
        .describe()
        .to_string()
    )

    # ======================================================
    # 3. VALIDACIÓN DEL BALANCE
    # ======================================================

    section(
        "2. COMPROBACIÓN DE DEFINICIÓN DEL BALANCE"
    )

    df["balance_recalculated"] = (
        df["avg_daily_arrivals"]
        - df["avg_daily_departures"]
    )

    df["balance_difference"] = (
        df["avg_daily_balance"]
        - df["balance_recalculated"]
    )

    max_error = (
        df["balance_difference"]
        .abs()
        .max()
    )

    print(
        "Balance definido como llegadas - salidas."
    )

    print(
        "Máxima diferencia entre balance almacenado "
        "y balance recalculado:",
        max_error
    )

    print(
        "\nInterpretación:"
    )

    print(
        "Balance positivo: más llegadas que salidas."
    )

    print(
        "Balance negativo: más salidas que llegadas."
    )

    # ======================================================
    # 4. COLUMNAS DE RESULTADOS
    # ======================================================

    cols = [
        "station_id",
        "station_name",
        "weekday_num",
        "hour",
        "observed_days",
        "avg_daily_departures",
        "avg_daily_arrivals",
        "avg_daily_balance",
        "positive_days_pct",
        "negative_days_pct",
        "balanced_days_pct",
        "avg_daily_activity",
    ]

    # ======================================================
    # 5. TOP POSITIVOS
    # ======================================================

    section(
        "3. TOP DESEQUILIBRIOS POSITIVOS"
    )

    positive = df.sort_values(
        "avg_daily_balance",
        ascending=False
    )

    print(
        format_table(
            positive.head(20),
            cols
        )
    )

    # ======================================================
    # 6. TOP NEGATIVOS
    # ======================================================

    section(
        "4. TOP DESEQUILIBRIOS NEGATIVOS"
    )

    negative = df.sort_values(
        "avg_daily_balance",
        ascending=True
    )

    print(
        format_table(
            negative.head(20),
            cols
        )
    )

    # ======================================================
    # 7. PERSISTENCIA POSITIVA
    # ======================================================

    section(
        "5. PATRONES POSITIVOS PERSISTENTES"
    )

    persistent_positive = df[
        (df["observed_days"] >= 30)
        &
        (df["avg_daily_balance"] >= 5)
        &
        (df["positive_days_pct"] >= 80)
    ].copy()

    persistent_positive = (
        persistent_positive
        .sort_values(
            [
                "positive_days_pct",
                "avg_daily_balance",
                "observed_days"
            ],
            ascending=[
                False,
                False,
                False
            ]
        )
    )

    print(
        "Número de candidatos:",
        len(persistent_positive)
    )

    print(
        format_table(
            persistent_positive.head(30),
            cols
        )
    )

    # ======================================================
    # 8. PERSISTENCIA NEGATIVA
    # ======================================================

    section(
        "6. PATRONES NEGATIVOS PERSISTENTES"
    )

    persistent_negative = df[
        (df["observed_days"] >= 30)
        &
        (df["avg_daily_balance"] <= -5)
        &
        (df["negative_days_pct"] >= 80)
    ].copy()

    persistent_negative = (
        persistent_negative
        .sort_values(
            [
                "negative_days_pct",
                "avg_daily_balance",
                "observed_days"
            ],
            ascending=[
                False,
                True,
                False
            ]
        )
    )

    print(
        "Número de candidatos:",
        len(persistent_negative)
    )

    print(
        format_table(
            persistent_negative.head(30),
            cols
        )
    )

    # ======================================================
    # 9. CANDIDATOS PREVIOS
    # ======================================================

    section(
        "7. VALIDACIÓN DE CANDIDATOS PREVIOS"
    )

    # weekday_num:
    # 0 = lunes
    # 1 = martes
    # 2 = miércoles
    # 3 = jueves
    # 4 = viernes
    # 5 = sábado
    # 6 = domingo

    candidates = [
        # Plaza Independencia
        (64, "Plaza Independencia", 3, 8),  # jueves
        (64, "Plaza Independencia", 2, 8),  # miércoles
        (64, "Plaza Independencia", 1, 8),  # martes
        (64, "Plaza Independencia", 0, 8),  # lunes

        # Velázquez 130
        (162, "Velázquez 130", 2, 8),  # miércoles
        (162, "Velázquez 130", 3, 8),  # jueves
        (162, "Velázquez 130", 1, 8),  # martes

        # Plaza de los Carros
        (42, "Plaza de los Carros", 3, 8),  # jueves
        (42, "Plaza de los Carros", 1, 8),  # martes
        (42, "Plaza de los Carros", 2, 8),  # miércoles

        # La Cebada
        (43, "Plaza de la Cebada", 2, 8),  # miércoles

        # Galileo
        (253, "Galileo", 0, 8),  # lunes
        (253, "Galileo", 1, 8),  # martes

        # Santa Isabel
        (46, "Santa Isabel", 1, 8),  # martes

        # Fernando el Católico
        (168, "Fernando el Católico", 1, 8),  # martes
        (168, "Fernando el Católico", 2, 8),  # miércoles
    ]

    weekday_names = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    for station_id, expected_name, weekday, hour in candidates:

        row = df[
            (df["station_id"] == station_id)
            &
            (df["weekday_num"] == weekday)
            &
            (df["hour"] == hour)
        ]

        if row.empty:

            print(
                f"\nNO ENCONTRADO: "
                f"{station_id} | "
                f"{expected_name} | "
                f"{weekday_names[weekday]} | "
                f"{hour:02d}:00"
            )

            continue

        row = row.iloc[0]

        print(
            f"\n{row['station_id']} | "
            f"{row['station_name']} | "
            f"{weekday_names[weekday]} | "
            f"{hour:02d}:00"
        )

        print(
            f"  Días observados: "
            f"{row['observed_days']:.0f}"
        )

        print(
            f"  Salidas medias: "
            f"{row['avg_daily_departures']:.3f}"
        )

        print(
            f"  Llegadas medias: "
            f"{row['avg_daily_arrivals']:.3f}"
        )

        print(
            f"  Balance medio: "
            f"{row['avg_daily_balance']:.3f}"
        )

        print(
            f"  Días positivos: "
            f"{row['positive_days_pct']:.2f}%"
        )

        print(
            f"  Días negativos: "
            f"{row['negative_days_pct']:.2f}%"
        )

        print(
            f"  Días equilibrados: "
            f"{row['balanced_days_pct']:.2f}%"
        )

        print(
            f"  Actividad media: "
            f"{row['avg_daily_activity']:.3f}"
        )

    # ======================================================
    # 10. EXPORTACIÓN
    # ======================================================

    section(
        "8. EXPORTACIÓN DE RESULTADOS"
    )

    persistent_positive.to_csv(
        OUTPUT_DIR
        / "persistent_positive_station_patterns.csv",
        index=False
    )

    persistent_negative.to_csv(
        OUTPUT_DIR
        / "persistent_negative_station_patterns.csv",
        index=False
    )

    positive.head(100).to_csv(
        OUTPUT_DIR
        / "top_positive_station_patterns.csv",
        index=False
    )

    negative.head(100).to_csv(
        OUTPUT_DIR
        / "top_negative_station_patterns.csv",
        index=False
    )

    print(
        "Archivos guardados en:",
        OUTPUT_DIR
    )

    print(
        "\n- persistent_positive_station_patterns.csv"
    )

    print(
        "- persistent_negative_station_patterns.csv"
    )

    print(
        "- top_positive_station_patterns.csv"
    )

    print(
        "- top_negative_station_patterns.csv"
    )

    section(
        "AUDITORÍA FINALIZADA"
    )

    print(
        "Filtros exploratorios aplicados:"
    )

    print(
        "- Al menos 30 días observados"
    )

    print(
        "- Balance medio >= +5 para patrones positivos"
    )

    print(
        "- Balance medio <= -5 para patrones negativos"
    )

    print(
        "- Persistencia >=80% en la misma dirección"
    )

    print(
        "\nEstos umbrales sirven para priorizar candidatos. "
        "No representan una necesidad operativa demostrada."
    )


if __name__ == "__main__":
    main()