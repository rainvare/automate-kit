"""
clean_excel.py
--------------
Toma un Excel o CSV sucio y produce una versión limpia con reporte de cambios.

Problemas que resuelve:
  - Columnas con nombres inconsistentes (espacios, mayúsculas, caracteres raros)
  - Filas completamente vacías
  - Duplicados exactos
  - Tipos de dato incorrectos (fechas como texto, números como string)
  - Valores nulos — reporta por columna, no elimina sin avisar

Uso:
  python clean_excel.py --input datos.xlsx --output datos_limpio.xlsx
  python clean_excel.py --input datos.csv --output datos_limpio.csv --sep ";"
"""

import argparse
import pandas as pd
import json
from pathlib import Path
from datetime import datetime


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Normaliza nombres de columnas: minúsculas, sin espacios, sin caracteres especiales."""
    original = list(df.columns)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r'[^a-z0-9_]', '_', regex=True)
        .str.replace(r'_+', '_', regex=True)
        .str.strip('_')
    )
    changes = [
        {"original": o, "normalized": n}
        for o, n in zip(original, df.columns) if o != n
    ]
    return df, changes


def infer_and_convert_types(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Intenta convertir columnas de texto a tipos más apropiados."""
    conversions = []
    for col in df.columns:
        original_dtype = str(df[col].dtype)
        if df[col].dtype == object:
            # Intentar fecha
            try:
                converted = pd.to_datetime(df[col], dayfirst=True, errors='raise')
                df[col] = converted
                conversions.append({"column": col, "from": original_dtype, "to": "datetime"})
                continue
            except Exception:
                pass
            # Intentar numérico
            try:
                numeric = pd.to_numeric(df[col].str.replace(',', '.', regex=False), errors='raise')
                df[col] = numeric
                conversions.append({"column": col, "from": original_dtype, "to": str(numeric.dtype)})
            except Exception:
                pass
    return df, conversions


def generate_report(original_shape, final_shape, col_changes, type_changes,
                    duplicates_removed, nulls_per_col) -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "rows": {"original": original_shape[0], "final": final_shape[0],
                 "removed": original_shape[0] - final_shape[0]},
        "columns": {"original": original_shape[1], "final": final_shape[1]},
        "column_renames": col_changes,
        "type_conversions": type_changes,
        "duplicates_removed": duplicates_removed,
        "nulls_by_column": nulls_per_col,
    }


def clean(input_path: str, output_path: str, sep: str = ",") -> None:
    p = Path(input_path)

    # Carga
    if p.suffix in (".xlsx", ".xls"):
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p, sep=sep)

    original_shape = df.shape
    print(f"📂 Cargado: {original_shape[0]} filas × {original_shape[1]} columnas")

    # 1. Normalizar columnas
    df, col_changes = normalize_columns(df)
    if col_changes:
        print(f"🔤 {len(col_changes)} columna(s) renombrada(s)")

    # 2. Eliminar filas completamente vacías
    before = len(df)
    df = df.dropna(how='all')
    empty_rows = before - len(df)
    if empty_rows:
        print(f"🗑️  {empty_rows} fila(s) vacía(s) eliminada(s)")

    # 3. Eliminar duplicados exactos
    before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before - len(df)
    if duplicates_removed:
        print(f"♻️  {duplicates_removed} duplicado(s) eliminado(s)")

    # 4. Inferir tipos
    df, type_changes = infer_and_convert_types(df)
    if type_changes:
        print(f"🔁 {len(type_changes)} columna(s) convertida(s) de tipo")

    # 5. Reporte de nulos
    nulls = df.isnull().sum()
    nulls_per_col = {col: int(n) for col, n in nulls.items() if n > 0}
    if nulls_per_col:
        print(f"⚠️  Nulos detectados: {nulls_per_col}")

    # Guardar output
    out = Path(output_path)
    if out.suffix in (".xlsx", ".xls"):
        df.to_excel(out, index=False)
    else:
        df.to_csv(out, index=False)
    print(f"✅ Guardado en: {out}")

    # Guardar reporte JSON
    report = generate_report(original_shape, df.shape, col_changes,
                             type_changes, duplicates_removed, nulls_per_col)
    report_path = out.with_suffix('.report.json')
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"📋 Reporte guardado en: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpia un Excel o CSV sucio")
    parser.add_argument("--input", required=True, help="Archivo de entrada (.xlsx, .xls, .csv)")
    parser.add_argument("--output", required=True, help="Archivo de salida")
    parser.add_argument("--sep", default=",", help="Separador para CSV (default: ,)")
    args = parser.parse_args()
    clean(args.input, args.output, args.sep)
