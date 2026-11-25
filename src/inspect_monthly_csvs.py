import zipfile
import io
import csv
from pathlib import Path

RAW = Path("data/raw")

for outer_zip in sorted(RAW.glob("bicimad_*.zip")):
    print("\n" + "#" * 90)
    print(f"ARCHIVO: {outer_zip.name}")
    print("#" * 90)

    with zipfile.ZipFile(outer_zip) as outer:
        monthly_zips = [
            f for f in outer.namelist()
            if f.endswith(".zip")
            and "trips_" in f
            and not f.startswith("__MACOSX")
        ]

        for monthly_name in sorted(monthly_zips):
            print(f"\n--- {monthly_name} ---")

            monthly_bytes = outer.read(monthly_name)

            with zipfile.ZipFile(io.BytesIO(monthly_bytes)) as monthly:
                csv_files = [
                    f for f in monthly.namelist()
                    if f.lower().endswith(".csv")
                    and not f.startswith("__MACOSX")
                ]

                for csv_name in csv_files:
                    with monthly.open(csv_name) as f:
                        text = f.read(10000).decode("utf-8", errors="replace")

                    reader = csv.reader(
                        io.StringIO(text),
                        delimiter=";"
                    )

                    rows = [
                        row for row in reader
                        if row and any(value.strip() for value in row)
                    ]

                    print(f"CSV: {csv_name}")

                    if rows:
                        print(f"Número de columnas del encabezado: {len(rows[0])}")
                        print("ENCABEZADO:")
                        print(rows[0])

                        print("MUESTRA:")
                        for row in rows[1:4]:
                            print(row)
