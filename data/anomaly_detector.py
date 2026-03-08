"""
anomaly_detector.py
-------------------
Detecta valores anómalos en una serie de tiempo usando Z-score e IQR.
Genera un reporte y un gráfico con los outliers marcados.

Problemas que resuelve:
  - Detectar picos o caídas inusuales en métricas de negocio
  - Identificar errores de carga de datos (valores imposibles)
  - Monitoreo básico sin necesidad de infraestructura compleja

Uso:
  python anomaly_detector.py --input ventas.csv --column monto --date_col fecha
  python anomaly_detector.py --input metricas.xlsx --column visitas --threshold 2.5
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def detect_anomalies(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Retorna máscara booleana: True donde hay anomalía (Z-score o IQR)."""
    # Z-score
    mean, std = series.mean(), series.std()
    z_scores = np.abs((series - mean) / std)
    z_mask = z_scores > threshold

    # IQR
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    iqr_mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)

    return z_mask | iqr_mask


def run(input_path: str, column: str, date_col: str = None,
        threshold: float = 3.0) -> None:
    p = Path(input_path)
    df = pd.read_excel(p) if p.suffix in (".xlsx", ".xls") else pd.read_csv(p)

    if column not in df.columns:
        print(f"❌ Columna '{column}' no encontrada. Columnas disponibles: {list(df.columns)}")
        return

    series = pd.to_numeric(df[column], errors='coerce').dropna()
    mask = detect_anomalies(series, threshold)
    anomalies = df.loc[series.index[mask]]

    print(f"📊 Serie analizada: {len(series)} valores")
    print(f"⚠️  Anomalías detectadas: {mask.sum()}")

    if mask.sum() > 0:
        print("\nTop anomalías:")
        print(anomalies[[date_col, column] if date_col and date_col in df.columns
                        else [column]].head(10).to_string(index=False))

    # Gráfico
    fig, ax = plt.subplots(figsize=(12, 4))
    x = df[date_col] if date_col and date_col in df.columns else series.index

    ax.plot(x, series.values, color='#1A1A2E', linewidth=1, label='Serie')
    ax.scatter(
        x[mask], series[mask],
        color='#C0392B', s=60, zorder=5, label=f'Anomalías ({mask.sum()})'
    )
    ax.axhline(series.mean(), color='#D4963A', linestyle='--',
               linewidth=0.8, alpha=0.7, label='Media')
    ax.set_title(f'Detección de anomalías — {column}', fontsize=11)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=7)
    plt.tight_layout()

    out_img = p.with_name(f"anomalias_{column}.png")
    plt.savefig(out_img, dpi=150)
    print(f"\n📈 Gráfico guardado en: {out_img}")

    # Reporte CSV
    if mask.sum() > 0:
        out_csv = p.with_name(f"anomalias_{column}.csv")
        anomalies.to_csv(out_csv, index=False)
        print(f"📋 Detalle guardado en: {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta anomalías en una serie de tiempo")
    parser.add_argument("--input", required=True)
    parser.add_argument("--column", required=True, help="Columna numérica a analizar")
    parser.add_argument("--date_col", default=None, help="Columna de fecha (opcional)")
    parser.add_argument("--threshold", type=float, default=3.0,
                        help="Umbral Z-score (default: 3.0)")
    args = parser.parse_args()
    run(args.input, args.column, args.date_col, args.threshold)
