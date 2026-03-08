"""
time_tracker.py
---------------
Parsea un log de texto con entradas de tiempo y genera reporte de horas
por proyecto, cliente o categoría.

Formato del log (un archivo .txt o .md):
  2024-03-01 09:00-11:30 | ClienteA | Desarrollo API
  2024-03-01 14:00-16:00 | ClienteB | Reunión de kick-off
  2024-03-02 10:00-12:00 | ClienteA | Code review
  2024-03-02 15:30-17:00 | Admin | Facturación

Problemas que resuelve:
  - Trackear horas sin herramientas pagas
  - Generar reporte de horas para facturación
  - Ver dónde va el tiempo realmente

Uso:
  python time_tracker.py --input mis_horas.txt
  python time_tracker.py --input horas.txt --output reporte.md --period semana
"""

import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


LINE_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s*\|\s*([^|]+)\s*\|\s*(.+)"
)


def parse_log(file_path: Path) -> list[dict]:
    entries = []
    errors = []

    for i, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = LINE_PATTERN.match(line)
        if not match:
            errors.append(f"Línea {i} no reconocida: {line}")
            continue

        date_str, start_str, end_str, client, task = match.groups()
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
            end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")

            if end < start:  # Cruce de medianoche
                end += timedelta(days=1)

            hours = (end - start).total_seconds() / 3600

            entries.append({
                "date": date,
                "date_str": date_str,
                "start": start_str,
                "end": end_str,
                "client": client.strip(),
                "task": task.strip(),
                "hours": round(hours, 2),
            })
        except ValueError as e:
            errors.append(f"Línea {i}: error de formato — {e}")

    if errors:
        print(f"⚠️  {len(errors)} línea(s) con formato incorrecto:")
        for e in errors[:5]:
            print(f"   {e}")

    return entries


def generate_report(entries: list[dict], period: str = "todo") -> str:
    if not entries:
        return "❌ No se encontraron entradas válidas."

    # Totales por cliente
    by_client = defaultdict(float)
    by_task = defaultdict(float)
    by_date = defaultdict(float)

    for e in entries:
        by_client[e["client"]] += e["hours"]
        by_task[e["task"]] += e["hours"]
        by_date[e["date_str"]] += e["hours"]

    total_hours = sum(e["hours"] for e in entries)
    date_range = f"{min(e['date_str'] for e in entries)} → {max(e['date_str'] for e in entries)}"

    lines = [
        f"# Reporte de horas",
        f"*Período: {date_range} | Total: {total_hours:.1f}h*\n",
        "## Por cliente / proyecto",
        "| Cliente | Horas | % |",
        "|---|---|---|",
    ]

    for client, hours in sorted(by_client.items(), key=lambda x: -x[1]):
        pct = hours / total_hours * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"| {client} | {hours:.1f}h | {pct:.0f}% {bar[:10]} |")

    lines.append("")
    lines.append("## Por día")
    lines.append("| Fecha | Horas |")
    lines.append("|---|---|")
    for date, hours in sorted(by_date.items()):
        lines.append(f"| {date} | {hours:.1f}h |")

    lines.append("")
    lines.append("## Detalle completo")
    lines.append("| Fecha | Horario | Cliente | Tarea | Horas |")
    lines.append("|---|---|---|---|---|")
    for e in sorted(entries, key=lambda x: (x["date_str"], x["start"])):
        lines.append(
            f"| {e['date_str']} | {e['start']}–{e['end']} "
            f"| {e['client']} | {e['task']} | {e['hours']:.1f}h |"
        )

    lines.append(f"\n**Total: {total_hours:.1f} horas**")

    return "\n".join(lines)


def run(input_file: str, output: str = None, period: str = "todo") -> None:
    p = Path(input_file)
    if not p.exists():
        print(f"❌ Archivo no encontrado: {p}")
        return

    print(f"⏱️  Parseando: {p.name}")
    entries = parse_log(p)
    print(f"✅ {len(entries)} entradas procesadas")

    report = generate_report(entries, period)

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"💾 Reporte guardado en: {output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reporte de horas desde log de texto")
    parser.add_argument("--input", required=True, help="Archivo de log de horas")
    parser.add_argument("--output", default=None, help="Guardar reporte en .md")
    parser.add_argument("--period", default="todo",
                        choices=["hoy", "semana", "mes", "todo"])
    args = parser.parse_args()
    run(args.input, args.output, args.period)
