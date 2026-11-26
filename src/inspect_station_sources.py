from pathlib import Path
import csv
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "CRTM": ROOT / "data" / "raw" / "Bici_Publica_TP_-7733901207477329617.csv",
    "AYUNTAMIENTO": ROOT / "data" / "raw" / "bikestationbicimad_csv.csv",
}

CANDIDATE_SEPARATORS = [",", ";", "\t", "|"]


def detect_separator(path):
    """
    Detecta el separador usando consistencia del número de campos
    en las primeras líneas del CSV.
    """
    results = []

    for separator in CANDIDATE_SEPARATORS:
        counts = []

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.reader(file, delimiter=separator)

                for i, row in enumerate(reader):
                    if i >= 20:
                        break
                    if row:
                        counts.append(len(row))

        except Exception:
            continue

        if not counts:
            continue

        mode_count = max(set(counts), key=counts.count)
        consistency = counts.count(mode_count) / len(counts)

        results.append({
            "separator": separator,
            "mode_columns": mode_count,
            "consistency": consistency,
            "counts": counts,
        })

    results.sort(
        key=lambda result: (
            result["consistency"],
            result["mode_columns"],
        ),
        reverse=True,
    )

    return results


def inspect_file(label, path):
    print("\n" + "=" * 80)
    print(f"FUENTE: {label}")
    print("=" * 80)

    if not path.exists():
        print(f"ERROR: No existe el archivo: {path}")
        return

    print(f"Archivo: {path}")

    # Mostrar primeras líneas RAW
    print("\nPRIMERAS 8 LÍNEAS RAW:")
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            for i, line in enumerate(file):
                if i >= 8:
                    break
                print(f"{i + 1}: {line.rstrip()}")
    except Exception as exc:
        print(f"No se pudieron leer las líneas raw: {exc}")

    # Detectar separador
    separator_results = detect_separator(path)

    print("\nDETECCIÓN DE SEPARADOR:")
    for result in separator_results:
        separator_display = (
            "TAB" if result["separator"] == "\t"
            else result["separator"]
        )

        print(
            f"Separador={separator_display!r} | "
            f"columnas frecuentes={result['mode_columns']} | "
            f"consistencia={result['consistency']:.2%} | "
            f"campos por línea={result['counts']}"
        )

    if not separator_results:
        print("No se pudo detectar ningún separador.")
        return

    best_separator = separator_results[0]["separator"]

    print(
        "\nSeparador seleccionado: "
        f"{'TAB' if best_separator == chr(9) else best_separator!r}"
    )

    # Leer con el separador seleccionado
    try:
        df = pd.read_csv(
            path,
            sep=best_separator,
            encoding="utf-8-sig",
            engine="python",
        )

    except Exception as exc:
        print(f"\nERROR al cargar CSV con pandas: {exc}")
        return

    print(f"\nDimensiones: {df.shape[0]:,} filas x {df.shape[1]} columnas")

    print("\nCOLUMNAS:")
    for column in df.columns:
        print(f" - {column}")

    print("\nTIPOS DE DATOS:")
    print(df.dtypes.to_string())

    print("\nVALORES NULOS:")
    print(df.isna().sum().to_string())

    print("\nPRIMERAS 10 FILAS:")
    print(df.head(10).to_string(index=False))

    print("\n" + "-" * 80)


def main():
    for label, path in FILES.items():
        inspect_file(label, path)


if __name__ == "__main__":
    main()