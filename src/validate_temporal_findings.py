# src/validate_temporal_findings.py

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

FILES = {
    "weekday": DATA / "demand_weekday.csv",
    "hourly": DATA / "demand_hourly.csv",
    "monthly": DATA / "demand_monthly.csv",
}


def load_file(path, name):

    if not path.exists():

        print(f"\n[AVISO] No existe: {path}")
        return None

    df = pd.read_csv(
        path,
        low_memory=False
    )

    print(f"\nArchivo: {name}")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {list(df.columns)}")

    return df


def find_trip_column(df):

    candidates = [
        "trips",
        "total_trips",
        "trip_count",
        "count",
        "viajes",
        "total",
        "n_trips",
    ]

    for col in candidates:

        if col in df.columns:
            return col

    # Búsqueda por nombre de columna
    for col in df.columns:

        normalized = col.lower()

        if (
            "trip" in normalized
            or "viaje" in normalized
        ):

            return col

    return None


def find_dimension_column(df, candidates):

    for col in candidates:

        if col in df.columns:
            return col

    return None


def print_top(df, dimension, trips, label, n=10):

    if dimension is None or trips is None:

        print(
            f"\nNo se han podido identificar "
            f"automáticamente las columnas de {label}."
        )

        print(df.head(10).to_string(index=False))

        return

    temp = df.copy()

    temp[trips] = pd.to_numeric(
        temp[trips],
        errors="coerce"
    )

    temp = temp.sort_values(
        trips,
        ascending=False
    )

    print(f"\nTOP {n} — {label}")
    print("-" * 75)

    print(
        temp[
            [dimension, trips]
        ]
        .head(n)
        .to_string(index=False)
    )


def main():

    print("\n" + "=" * 78)
    print("VALIDACIÓN DE HALLAZGOS TEMPORALES BiciMAPP")
    print("=" * 78)

    weekday = load_file(
        FILES["weekday"],
        "DEMANDA POR DÍA DE LA SEMANA"
    )

    hourly = load_file(
        FILES["hourly"],
        "DEMANDA POR HORA"
    )

    monthly = load_file(
        FILES["monthly"],
        "DEMANDA POR MES"
    )

    # ======================================================
    # 1. VALIDAR DÍA DE LA SEMANA
    # ======================================================

    if weekday is not None:

        weekday_trip_col = find_trip_column(
            weekday
        )

        weekday_dimension = find_dimension_column(
            weekday,
            [
                "weekday_name",
                "day_name",
                "weekday",
                "day",
                "dia",
                "día",
            ]
        )

        print("\n" + "=" * 78)
        print("1. VALIDACIÓN SEMANAL")
        print("=" * 78)

        if weekday_trip_col:

            weekday_total = pd.to_numeric(
                weekday[weekday_trip_col],
                errors="coerce"
            ).sum()

            print(
                "Total de viajes representados:",
                f"{weekday_total:,.0f}"
            )

            print(
                "Número de categorías:",
                len(weekday)
            )

        print_top(
            weekday,
            weekday_dimension,
            weekday_trip_col,
            "DÍAS DE LA SEMANA",
            n=7
        )

        if weekday_trip_col:

            temp = weekday.copy()

            temp[weekday_trip_col] = pd.to_numeric(
                temp[weekday_trip_col],
                errors="coerce"
            )

            total = temp[weekday_trip_col].sum()

            temp["share_pct"] = (
                temp[weekday_trip_col]
                / total
                * 100
            )

            print("\nPORCENTAJE DE VIAJES POR DÍA")
            print("-" * 75)

            print(
                temp[
                    [
                        weekday_dimension,
                        weekday_trip_col,
                        "share_pct"
                    ]
                ]
                .sort_values(
                    weekday_trip_col,
                    ascending=False
                )
                .to_string(
                    index=False,
                    formatters={
                        "share_pct": "{:.2f}%".format
                    }
                )
            )

            if weekday_dimension:

                temp = temp.sort_values(
                    weekday_trip_col,
                    ascending=False
                )

                max_day = temp.iloc[0]
                min_day = temp.iloc[-1]

                difference = (
                    max_day[weekday_trip_col]
                    - min_day[weekday_trip_col]
                )

                ratio = (
                    max_day[weekday_trip_col]
                    / min_day[weekday_trip_col]
                )

                print("\nCOMPARACIÓN EXTREMOS")
                print("-" * 75)

                print(
                    f"Día máximo: "
                    f"{max_day[weekday_dimension]} "
                    f"({max_day[weekday_trip_col]:,.0f})"
                )

                print(
                    f"Día mínimo: "
                    f"{min_day[weekday_dimension]} "
                    f"({min_day[weekday_trip_col]:,.0f})"
                )

                print(
                    f"Diferencia absoluta: "
                    f"{difference:,.0f}"
                )

                print(
                    f"Ratio máximo/mínimo: "
                    f"{ratio:.3f}"
                )

    # ======================================================
    # 2. VALIDAR DEMANDA HORARIA
    # ======================================================

    if hourly is not None:

        hourly_trip_col = find_trip_column(
            hourly
        )

        hourly_dimension = find_dimension_column(
            hourly,
            [
                "hour",
                "hora",
                "hour_of_day",
            ]
        )

        print("\n" + "=" * 78)
        print("2. VALIDACIÓN HORARIA")
        print("=" * 78)

        if hourly_trip_col:

            hourly_total = pd.to_numeric(
                hourly[hourly_trip_col],
                errors="coerce"
            ).sum()

            print(
                "Total de viajes representados:",
                f"{hourly_total:,.0f}"
            )

            print(
                "Número de categorías:",
                len(hourly)
            )

        print_top(
            hourly,
            hourly_dimension,
            hourly_trip_col,
            "HORAS",
            n=10
        )

        if hourly_trip_col:

            temp = hourly.copy()

            temp[hourly_trip_col] = pd.to_numeric(
                temp[hourly_trip_col],
                errors="coerce"
            )

            total = temp[hourly_trip_col].sum()

            temp["share_pct"] = (
                temp[hourly_trip_col]
                / total
                * 100
            )

            print("\nPORCENTAJE DE VIAJES POR HORA")
            print("-" * 75)

            print(
                temp[
                    [
                        hourly_dimension,
                        hourly_trip_col,
                        "share_pct"
                    ]
                ]
                .sort_values(
                    hourly_trip_col,
                    ascending=False
                )
                .to_string(
                    index=False,
                    formatters={
                        "share_pct": "{:.2f}%".format
                    }
                )
            )

    # ======================================================
    # 3. VALIDAR DEMANDA MENSUAL
    # ======================================================

    if monthly is not None:

        monthly_trip_col = find_trip_column(
            monthly
        )

        monthly_dimension = find_dimension_column(
            monthly,
            [
                "month",
                "month_name",
                "month_num",
                "mes",
            ]
        )

        print("\n" + "=" * 78)
        print("3. VALIDACIÓN MENSUAL")
        print("=" * 78)

        print_top(
            monthly,
            monthly_dimension,
            monthly_trip_col,
            "MESES",
            n=12
        )

    # ======================================================
    # 4. CONCLUSIÓN
    # ======================================================

    print("\n" + "=" * 78)
    print("AUDITORÍA TEMPORAL COMPLETADA")
    print("=" * 78)

    print(
        "Esta auditoría verifica los agregados existentes. "
        "No vuelve a procesar los viajes originales."
    )

    print(
        "El periodo debe identificarse explícitamente "
        "antes de utilizar estos resultados en el pitch."
    )


if __name__ == "__main__":
    main()