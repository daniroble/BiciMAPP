import zipfile
from pathlib import Path

RAW = Path("data/raw")

for zip_path in sorted(RAW.glob("bicimad_*.zip")):
    print("\n" + "=" * 80)
    print(f"ZIP: {zip_path.name}")
    print(f"Tamaño: {zip_path.stat().st_size / (1024**2):.2f} MB")
    print("=" * 80)

    with zipfile.ZipFile(zip_path) as z:
        files = [f for f in z.infolist() if not f.is_dir()]

        print(f"Archivos dentro: {len(files)}")

        for f in files:
            print(f"{f.filename} | {f.file_size / (1024**2):.2f} MB")
