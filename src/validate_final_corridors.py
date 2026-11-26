from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]

OD_FILE = ROOT / "data" / "processed" / "od_clean" / "od_recurrence_filtered.csv"
STATION_FILE = ROOT / "data" / "processed" / "station_time_recurrence.csv"
CROSS_FILE = ROOT / "data" / "processed" / "cross_analysis" / "od_station_cross_all.csv"

OUT_DIR = ROOT / "analysis" / "validation" / "final_corridors"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# CORREDORES Y COMBINACIONES QUE VAMOS A CONTRASTAR
# ------------------------------------------------------------

CANDIDATES = [
    {
        "route": "Puente Praga -> Paseo de la Esperanza",
        "origin": "Puente Praga",
        "destination": "Paseo de la Esperanza",
        "weekday_hours": [(0, 7), (1, 8), (2, 8), (3, 8)],
    },
    {
        "route": "Fernando el Católico -> Orense 12",
        "origin": "Fernando el Católico",
        "destination": "Orense 12",
        "weekday_hours": [(1, 8), (2, 8), (3, 8)],
    },
    {
        "route": "Galileo -> Diego de León 52",
        "origin": "Galileo",
        "destination": "Diego de León 52",
        "weekday_hours": [(1, 7), (3, 7), (4, 7)],
    },
    {
        "route": "Lavapiés -> Atocha A",
        "origin": "Plaza de Lavapiés",
        "destination": "Atocha A",
        "weekday_hours": [(1, 7), (2, 7), (3, 7)],
    },
]

WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
}

# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------

def normalize(text):
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_col(df, candidates):
    normalized = {normalize(c): c for c in df.columns}

    for candidate in candidates:
        candidate_norm = normalize(candidate)
        if candidate_norm in normalized:
            return normalized[candidate_norm]

    for candidate in candidates:
        candidate_norm = normalize(candidate)
        for norm_col, original_col in normalized.items():
            if candidate_norm in norm_col:
                return original_col

    return None


def station_id_from_name(name):
    """
    Extrae el identificador inicial de nombres como:
    '173 - Puente Praga'
    '53 - Plaza de Lavapiés'
    """
    match = re.match(r"\s*(\d+)", str(name))
    return int(match.group(1)) if match else np.nan


def load_csv(path, label):
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {label}: {path}")

    df = pd.read_csv(path, low_memory=False)
    print(f"{label}: {len(df):,} filas")
    return df


def section(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


# ------------------------------------------------------------
# CARGA
# ------------------------------------------------------------

def main():

    section("VALIDACIÓN FINAL DE CORREDORES")

    od = load_csv(OD_FILE, "Recurrencia OD")
    stations = load_csv(STATION_FILE, "Recurrencia de estaciones")

    cross = None
    if CROSS_FILE.exists():
        cross = pd.read_csv(CROSS_FILE, low_memory=False)
        print(f"Cruce OD-estaciones: {len(cross):,} filas")
    else:
        print("Aviso: no se encontró cross-analysis.")

    # --------------------------------------------------------
    # DETECTAR COLUMNAS OD
    # --------------------------------------------------------

    od_origin_id = find_col(od, ["origin_id"])
    od_origin_name = find_col(od, ["origin_name"])
    od_destination_id = find_col(od, ["destination_id"])
    od_destination_name = find_col(od, ["destination_name"])
    od_weekday = find_col(od, ["weekday", "weekday_num"])
    od_hour = find_col(od, ["hour"])
    od_total = find_col(od, ["total_trips"])
    od_active = find_col(od, ["active_days"])
    od_eligible = find_col(od, ["eligible_days"])
    od_recurrence = find_col(od, ["recurrence_pct"])
    od_avg_eligible = find_col(od, ["avg_trips_per_eligible_day"])
    od_avg_active = find_col(od, ["avg_trips_per_active_day"])

    required_od = [
        od_origin_id,
        od_origin_name,
        od_destination_id,
        od_destination_name,
        od_weekday,
        od_hour,
        od_total,
        od_recurrence,
    ]

    if any(c is None for c in required_od):
        raise ValueError(
            "No se pudieron detectar todas las columnas necesarias del archivo OD."
        )

    # --------------------------------------------------------
    # DETECTAR COLUMNAS DE RECURRENCIA DE ESTACIONES
    # --------------------------------------------------------

    st_id = find_col(stations, ["station_id"])
    st_name = find_col(stations, ["station_name"])
    st_weekday = find_col(stations, ["weekday_num", "weekday"])
    st_hour = find_col(stations, ["hour"])

    st_observed = find_col(stations, ["observed_days"])
    st_avg_dep = find_col(stations, ["avg_daily_departures"])
    st_avg_arr = find_col(stations, ["avg_daily_arrivals"])
    st_balance = find_col(stations, ["avg_daily_balance"])
    st_abs_balance = find_col(stations, ["avg_abs_daily_balance"])
    st_positive_pct = find_col(stations, ["positive_days_pct"])
    st_negative_pct = find_col(stations, ["negative_days_pct"])
    st_activity = find_col(stations, ["avg_daily_activity"])

    required_station = [
        st_id,
        st_weekday,
        st_hour,
        st_balance,
        st_positive_pct,
        st_negative_pct,
    ]

    if any(c is None for c in required_station):
        raise ValueError(
            "No se pudieron detectar las columnas necesarias del archivo "
            "de recurrencia de estaciones."
        )

    # --------------------------------------------------------
    # NORMALIZAR TIPOS
    # --------------------------------------------------------

    od[od_weekday] = pd.to_numeric(od[od_weekday], errors="coerce")
    od[od_hour] = pd.to_numeric(od[od_hour], errors="coerce")
    od[od_origin_id] = pd.to_numeric(od[od_origin_id], errors="coerce")
    od[od_destination_id] = pd.to_numeric(od[od_destination_id], errors="coerce")

    stations[st_id] = pd.to_numeric(stations[st_id], errors="coerce")
    stations[st_weekday] = pd.to_numeric(stations[st_weekday], errors="coerce")
    stations[st_hour] = pd.to_numeric(stations[st_hour], errors="coerce")

    for col in [
        st_observed,
        st_avg_dep,
        st_avg_arr,
        st_balance,
        st_abs_balance,
        st_positive_pct,
        st_negative_pct,
        st_activity,
    ]:
        if col:
            stations[col] = pd.to_numeric(stations[col], errors="coerce")

    # --------------------------------------------------------
    # AUDITAR NOMBRES E IDs
    # --------------------------------------------------------

    section("CONTROL DE IDENTIFICACIÓN DE ESTACIONES")

    if st_name:
        stations["station_name_clean"] = stations[st_name].astype(str)

    print(f"IDs únicos estaciones: {stations[st_id].nunique()}")
    print(
        "Duplicados estación-día-hora:",
        stations.duplicated(
            subset=[st_id, st_weekday, st_hour]
        ).sum()
    )

    # --------------------------------------------------------
    # VALIDAR CORREDORES
    # --------------------------------------------------------

    results = []
    station_results = []

    for candidate in CANDIDATES:

        section(candidate["route"])

        origin_key = normalize(candidate["origin"])
        destination_key = normalize(candidate["destination"])

        for weekday, hour in candidate["weekday_hours"]:

            weekday_name = WEEKDAYS[weekday]

            route_rows = od[
                (od[od_weekday] == weekday)
                & (od[od_hour] == hour)
                & (od[od_origin_name].astype(str).apply(normalize).str.contains(
                    origin_key, regex=False
                ))
                & (od[od_destination_name].astype(str).apply(normalize).str.contains(
                    destination_key, regex=False
                ))
            ]

            if route_rows.empty:
                print(
                    f"NO ENCONTRADA: {weekday_name} {hour}:00 "
                    f"{candidate['route']}"
                )
                continue

            route = route_rows.sort_values(
                od_total, ascending=False
            ).iloc[0]

            origin_id = int(route[od_origin_id])
            destination_id = int(route[od_destination_id])

            # ------------------------------------------------
            # DATOS OD
            # ------------------------------------------------

            total_trips = route[od_total]
            recurrence = route[od_recurrence]

            active_days = route[od_active] if od_active else np.nan
            eligible_days = route[od_eligible] if od_eligible else np.nan
            avg_eligible = route[od_avg_eligible] if od_avg_eligible else np.nan
            avg_active = route[od_avg_active] if od_avg_active else np.nan

            print(f"\n{weekday_name} {hour:02d}:00")
            print(
                f"{route[od_origin_name]} -> "
                f"{route[od_destination_name]}"
            )
            print(
                f"Viajes={total_trips}, "
                f"recurrencia={recurrence:.2f}%, "
                f"días activos={active_days}, "
                f"días elegibles={eligible_days}"
            )

            # ------------------------------------------------
            # BALANCE DE ORIGEN
            # ------------------------------------------------

            origin_station = stations[
                (stations[st_id] == origin_id)
                & (stations[st_weekday] == weekday)
                & (stations[st_hour] == hour)
            ]

            # ------------------------------------------------
            # BALANCE DE DESTINO
            # ------------------------------------------------

            destination_station = stations[
                (stations[st_id] == destination_id)
                & (stations[st_weekday] == weekday)
                & (stations[st_hour] == hour)
            ]

            def get_station_record(df, role):

                if df.empty:
                    print(f"{role}: SIN DIAGNÓSTICO")
                    return None

                record = df.iloc[0]

                balance = record[st_balance]
                positive_pct = record[st_positive_pct]
                negative_pct = record[st_negative_pct]

                observed = record[st_observed] if st_observed else np.nan
                departures = record[st_avg_dep] if st_avg_dep else np.nan
                arrivals = record[st_avg_arr] if st_avg_arr else np.nan
                activity = record[st_activity] if st_activity else np.nan
                abs_balance = record[st_abs_balance] if st_abs_balance else np.nan

                print(
                    f"{role}: balance={balance:+.2f}, "
                    f"persistencia positiva={positive_pct:.1f}%, "
                    f"persistencia negativa={negative_pct:.1f}%, "
                    f"días observados={observed}"
                )

                station_results.append({
                    "route": candidate["route"],
                    "weekday": weekday_name,
                    "weekday_num": weekday,
                    "hour": hour,
                    "role": role,
                    "station_id": int(record[st_id]),
                    "station_name": record[st_name] if st_name else "",
                    "observed_days": observed,
                    "avg_daily_departures": departures,
                    "avg_daily_arrivals": arrivals,
                    "avg_daily_balance": balance,
                    "avg_abs_daily_balance": abs_balance,
                    "avg_daily_activity": activity,
                    "positive_days_pct": positive_pct,
                    "negative_days_pct": negative_pct,
                })

                return {
                    "balance": balance,
                    "positive_pct": positive_pct,
                    "negative_pct": negative_pct,
                    "observed_days": observed,
                    "departures": departures,
                    "arrivals": arrivals,
                    "activity": activity,
                    "abs_balance": abs_balance,
                }

            origin_info = get_station_record(
                origin_station, "ORIGEN"
            )

            destination_info = get_station_record(
                destination_station, "DESTINO"
            )

            # ------------------------------------------------
            # CLASIFICACIÓN EVIDENCIA
            # ------------------------------------------------

            evidence = "SOLO DEMANDA"

            if origin_info and destination_info:

                origin_balance = origin_info["balance"]
                destination_balance = destination_info["balance"]

                origin_negative = origin_info["negative_pct"]
                destination_positive = destination_info["positive_pct"]

                if (
                    origin_balance <= -5
                    and destination_balance >= 5
                    and origin_negative >= 80
                    and destination_positive >= 80
                ):
                    evidence = "EVIDENCIA FUERTE DE EMISOR-RECEPTOR"

                elif (
                    origin_balance < 0
                    and destination_balance > 0
                    and origin_negative >= 60
                    and destination_positive >= 60
                ):
                    evidence = "EVIDENCIA PARCIAL DE EMISOR-RECEPTOR"

                else:
                    evidence = "DEMANDA RECURRENTE SIN BALANCE CONCLUYENTE"

            elif origin_info or destination_info:
                evidence = "DEMANDA + DIAGNÓSTICO PARCIAL"

            print(f"CLASIFICACIÓN: {evidence}")

            results.append({
                "route": candidate["route"],
                "weekday": weekday_name,
                "weekday_num": weekday,
                "hour": hour,
                "origin_id": origin_id,
                "origin_name": route[od_origin_name],
                "destination_id": destination_id,
                "destination_name": route[od_destination_name],
                "total_trips": total_trips,
                "active_days": active_days,
                "eligible_days": eligible_days,
                "recurrence_pct": recurrence,
                "avg_trips_per_eligible_day": avg_eligible,
                "avg_trips_per_active_day": avg_active,
                "origin_balance": (
                    origin_info["balance"] if origin_info else np.nan
                ),
                "origin_negative_days_pct": (
                    origin_info["negative_pct"] if origin_info else np.nan
                ),
                "origin_positive_days_pct": (
                    origin_info["positive_pct"] if origin_info else np.nan
                ),
                "destination_balance": (
                    destination_info["balance"] if destination_info else np.nan
                ),
                "destination_positive_days_pct": (
                    destination_info["positive_pct"] if destination_info else np.nan
                ),
                "destination_negative_days_pct": (
                    destination_info["negative_pct"] if destination_info else np.nan
                ),
                "evidence_class": evidence,
            })

    # --------------------------------------------------------
    # EXPORTAR
    # --------------------------------------------------------

    section("EXPORTACIÓN DE RESULTADOS")

    result_df = pd.DataFrame(results)
    station_df = pd.DataFrame(station_results)

    result_file = OUT_DIR / "final_corridor_evidence.csv"
    station_file = OUT_DIR / "final_corridor_station_diagnosis.csv"

    result_df.to_csv(result_file, index=False, encoding="utf-8-sig")
    station_df.to_csv(station_file, index=False, encoding="utf-8-sig")

    print(f"Resultados: {result_file}")
    print(f"Diagnóstico estaciones: {station_file}")

    # --------------------------------------------------------
    # RESUMEN POR CORREDOR
    # --------------------------------------------------------

    section("RESUMEN FINAL POR CORREDOR")

    if not result_df.empty:

        summary = result_df.groupby("route").agg(
            combinations=("weekday", "count"),
            total_trips=("total_trips", "sum"),
            mean_recurrence=("recurrence_pct", "mean"),
            mean_trips_per_eligible_day=(
                "avg_trips_per_eligible_day", "mean"
            ),
            strong_evidence=(
                "evidence_class",
                lambda x: (x == "EVIDENCIA FUERTE DE EMISOR-RECEPTOR").sum()
            ),
            partial_evidence=(
                "evidence_class",
                lambda x: (x == "EVIDENCIA PARCIAL DE EMISOR-RECEPTOR").sum()
            ),
            demand_only=(
                "evidence_class",
                lambda x: x.str.contains("DEMANDA", na=False).sum()
            ),
        ).reset_index()

        summary = summary.sort_values(
            ["strong_evidence", "mean_recurrence", "total_trips"],
            ascending=[False, False, False]
        )

        print(summary.to_string(index=False))

        summary_file = OUT_DIR / "final_corridor_summary.csv"
        summary.to_csv(summary_file, index=False, encoding="utf-8-sig")

        print(f"\nResumen exportado: {summary_file}")

    section("FINAL")
    print("Validación conjunta de corredores completada.")


if __name__ == "__main__":
    main()