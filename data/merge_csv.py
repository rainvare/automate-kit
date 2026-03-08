"""
merge_csv.py
------------
Consolida múltiples CSVs o Excels de una carpeta en un solo archivo.

Problemas que resuelve:
  - Reportes mensuales en archivos separados que hay que unir cada vez
  - Archivos con columnas en distinto orden
  - Archivos con columnas extra o faltantes (las alinea automáticamente)
  - Agrega columna con el nombre del archivo fuente para trazabilidad

Uso:
  python merge_csv.py --folder ./reportes --output consolidado.xlsx
  python merge_csv.py --folder ./data --output out.csv --pattern "*ventas*"
"""

import argparse
import pandas as pd
from pathlib import Path
import glob


def merge(folder: str, output: str, pattern: str = "*") -> None:
    folder_path = Path(folder)
    files = sorted([
        f for f in folder_path.glob(pattern)
        if f.suffix in (".csv", ".xlsx", ".xls")
    ])

    if not files:
        print(f"❌ No se encontraron archivos en {folder} con patrón '{pattern}'")
        return

    print(f"📂 {len(files)} archivo(s) encontrado(s):")
    dfs = []

    for f in files:
        print(f"   → {f.name}")
        try:
            df = pd.read_excel(f) if f.suffix in (".xlsx", ".xls") else pd.read_csv(f)
            df["_source_file"] = f.name
            dfs.append(df)
        except Exception as e:
            print(f"   ⚠️  Error leyendo {f.name}: {e}")

    if not dfs:
        print("❌ Ningún archivo pudo ser leído.")
        return

    # Concatenar alineando columnas automáticamente
    consolidated = pd.concat(dfs, ignore_index=True, sort=False)

    print(f"\n✅ Consolidado: {len(consolidated)} filas × {len(consolidated.columns)} columnas")
    print(f"   Columnas: {list(consolidated.columns)}")

    # Guardar
    out = Path(output)
    if out.suffix in (".xlsx", ".xls"):
        consolidated.to_excel(out, index=False)
    else:
        consolidated.to_csv(out, index=False)

    print(f"💾 Guardado en: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolida múltiples CSVs/Excels en uno")
    parser.add_argument("--folder", required=True, help="Carpeta con los archivos")
    parser.add_argument("--output", required=True, help="Archivo de salida")
    parser.add_argument("--pattern", default="*", help="Patrón de nombre (ej: '*ventas*')")
    args = parser.parse_args()
    merge(args.folder, args.output, args.pattern)
