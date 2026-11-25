import csv
import io
import zipfile
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

OUTPUT_FILE = PROCESSED_DIR / "trips_2022_2023.csv"

OUTER_ZIPS = [
    RAW_DIR / "bicimad_2022.zip",
    RAW_DIR / "bicimad_2023.zip",
]

# Columnas que queremos conservar
KEEP_COLUMNS = [
    "fecha",
    "idBike",
    "fleet",
    "trip_minutes",
    "unlock_date",
    "lock_date",
    "station_unlock",
    "unlock_station_name",
    "station_lock",
    "lock_station_name",
]

# Renombrado normalizado
RENAME = {
    "fecha": "date",
    "idBike": "bike_id",
    "fleet": "fleet",
    "trip_minutes": "trip_minutes",
    "unlock_date": "unlock_date",
    "lock_date": "lock_date",
    "station_unlock": "station_unlock",
    "unlock_station_name": "unlock_station_name",
    "station_lock": "station_lock",
    "lock_station_name": "lock_station_name",
}


def is_blank_row(row):
    return not row or all(not str(value).strip() for value in row)


def process_file():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    invalid_rows = 0
    monthly_results = []

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=list(RENAME.values()),
        )
        writer.writeheader()

        for outer_zip_path in OUTER_ZIPS:
            if not outer_zip_path.exists():
                print(f"ERROR: No existe {outer_zip_path}")
                continue

            print(f"\nProcesando: {outer_zip_path.name}")

            with zipfile.ZipFile(outer_zip_path) as outer_zip:
                monthly_zip_names = [
                    name for name in outer_zip.namelist()
    if name.endswith("-csv.zip")
    and not name.startswith("__MACOSX/")
    and not name.split("/")[-1].startswith("._")
                ]

                for monthly_zip_name in monthly_zip_names:
                    print(f"  -> {monthly_zip_name}")

                    monthly_zip_bytes = outer_zip.read(monthly_zip_name)

                    with zipfile.ZipFile(
                        io.BytesIO(monthly_zip_bytes)
                    ) as monthly_zip:

                        csv_names = [
                            name for name in monthly_zip.namelist()
                            if name.lower().endswith(".csv")
                        ]

                        if not csv_names:
                            print("     ERROR: No se encontró CSV")
                            continue

                        csv_name = csv_names[0]

                        with monthly_zip.open(csv_name) as csv_binary:
                            text_stream = io.TextIOWrapper(
                                csv_binary,
                                encoding="utf-8",
                                errors="replace",
                                newline=""
                            )

                            reader = csv.reader(
                                text_stream,
                                delimiter=";",
                                quotechar='"'
                            )

                            header = next(reader, None)

                            if header is None:
                                continue

                            header = [
                                column.strip().lstrip("\ufeff")
                                for column in header
                            ]

                            positions = {
                                column: index
                                for index, column in enumerate(header)
                            }

                            missing = [
                                column for column in KEEP_COLUMNS
                                if column not in positions
                            ]

                            if missing:
                                print(
                                    f"     AVISO: columnas ausentes: {missing}"
                                )

                            month_rows = 0

                            for row in reader:
                                if is_blank_row(row):
                                    continue

                                if len(row) != len(header):
                                    invalid_rows += 1
                                    continue

                                record = {}

                                for original, normalized in RENAME.items():
                                    if original in positions:
                                        value = row[positions[original]].strip()
                                    else:
                                        value = ""

                                    record[normalized] = value

                                # Excluir registros sin estaciones
                                if (
                                    not record["station_unlock"]
                                    or not record["station_lock"]
                                ):
                                    invalid_rows += 1
                                    continue

                                writer.writerow(record)

                                total_rows += 1
                                month_rows += 1

                            monthly_results.append(
                                (monthly_zip_name, month_rows)
                            )

                            print(
                                f"     Registros válidos: {month_rows:,}"
                            )

    print("\n" + "=" * 60)
    print("PROCESAMIENTO TERMINADO")
    print("=" * 60)
    print(f"Total registros: {total_rows:,}")
    print(f"Registros descartados: {invalid_rows:,}")
    print(f"Archivo generado: {OUTPUT_FILE}")
    print(f"Tamaño: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")

    print("\nResumen mensual:")
    for filename, count in monthly_results:
        print(f"{filename}: {count:,}")


if __name__ == "__main__":
    process_file()