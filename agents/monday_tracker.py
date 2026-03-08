"""
monday_tracker.py
-----------------
Consulta Monday.com via API GraphQL, extrae tareas asignadas
y genera un reporte de estado diario/semanal.

Problemas que resuelve:
  - Ver todas tus tareas pendientes sin abrir Monday
  - Generar reporte de progreso para standup o reunión semanal
  - Detectar tareas vencidas o sin fecha

Setup:
  1. Obtener API token en Monday.com → Profile → Developers → API
  2. export MONDAY_API_TOKEN=tu_token
  3. pip install requests

Uso:
  export MONDAY_API_TOKEN=...
  python monday_tracker.py --board 123456789
  python monday_tracker.py --board 123456789 --user "Tu Nombre" --output reporte.md
"""

import argparse
import os
import requests
import json
from pathlib import Path
from datetime import datetime, date


MONDAY_API_URL = "https://api.monday.com/v2"


def query_monday(query: str, token: str) -> dict:
    """Ejecuta una query GraphQL contra la API de Monday."""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    r = requests.post(
        MONDAY_API_URL,
        json={"query": query},
        headers=headers,
        timeout=15
    )
    r.raise_for_status()
    return r.json()


def get_board_items(board_id: str, token: str) -> list[dict]:
    """Recupera todos los items de un board con sus columnas clave."""
    query = f"""
    {{
      boards(ids: [{board_id}]) {{
        name
        items_page(limit: 200) {{
          items {{
            id
            name
            state
            column_values {{
              id
              title
              text
              value
            }}
          }}
        }}
      }}
    }}
    """

    data = query_monday(query, token)
    boards = data.get("data", {}).get("boards", [])

    if not boards:
        print(f"❌ Board {board_id} no encontrado o sin acceso.")
        return []

    board_name = boards[0]["name"]
    items = boards[0].get("items_page", {}).get("items", [])
    print(f"📋 Board: {board_name} | {len(items)} items encontrados")
    return items, board_name


def parse_items(items: list, filter_user: str = None) -> list[dict]:
    """Normaliza items y extrae campos relevantes."""
    parsed = []
    for item in items:
        cols = {c["title"].lower(): c["text"] for c in item.get("column_values", [])}

        assignee = cols.get("person", cols.get("owner", cols.get("assigned to", "")))
        status = cols.get("status", item.get("state", ""))
        due_date = cols.get("date", cols.get("due date", cols.get("deadline", "")))

        if filter_user and filter_user.lower() not in (assignee or "").lower():
            continue

        parsed.append({
            "id": item["id"],
            "name": item["name"],
            "status": status,
            "assignee": assignee,
            "due_date": due_date,
            "overdue": _is_overdue(due_date),
        })

    return parsed


def _is_overdue(due_date_str: str) -> bool:
    if not due_date_str:
        return False
    try:
        due = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
        return due < date.today()
    except Exception:
        return False


def generate_report(items: list[dict], board_name: str,
                    filter_user: str = None) -> str:
    total = len(items)
    done = [i for i in items if "done" in (i["status"] or "").lower()
            or "complete" in (i["status"] or "").lower()]
    overdue = [i for i in items if i["overdue"] and i not in done]
    in_progress = [i for i in items if i not in done and i not in overdue]
    no_date = [i for i in items if not i["due_date"]]

    lines = [
        f"# Reporte Monday.com — {board_name}",
        f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        f"{f' | Filtro: {filter_user}' if filter_user else ''}*\n",
        f"**Total:** {total} tareas | "
        f"**Completadas:** {len(done)} | "
        f"**En progreso:** {len(in_progress)} | "
        f"**Vencidas:** {len(overdue)}\n",
    ]

    if overdue:
        lines.append("## 🔴 Vencidas")
        for i in overdue:
            lines.append(f"- **{i['name']}** — {i['status']} | Vencimiento: {i['due_date']}"
                         f"{f' | {i[\"assignee\"]}' if i['assignee'] else ''}")
        lines.append("")

    if in_progress:
        lines.append("## 🟡 En progreso")
        for i in in_progress:
            due = f" | Vence: {i['due_date']}" if i["due_date"] else " | Sin fecha"
            lines.append(f"- **{i['name']}** — {i['status']}{due}"
                         f"{f' | {i[\"assignee\"]}' if i['assignee'] else ''}")
        lines.append("")

    if done:
        lines.append("## ✅ Completadas")
        for i in done:
            lines.append(f"- ~~{i['name']}~~")
        lines.append("")

    if no_date:
        lines.append(f"## ⚠️ Sin fecha asignada ({len(no_date)})")
        for i in no_date:
            lines.append(f"- {i['name']} — {i['status']}")

    return "\n".join(lines)


def run(board_id: str, filter_user: str = None, output: str = None) -> None:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        print("❌ Variable MONDAY_API_TOKEN no encontrada.")
        print("   Obtenerla en: Monday.com → Profile → Developers → API")
        return

    result = get_board_items(board_id, token)
    if not result:
        return

    items_raw, board_name = result
    items = parse_items(items_raw, filter_user)

    if not items:
        print(f"ℹ️  No se encontraron tareas"
              f"{f' para {filter_user}' if filter_user else ''}.")
        return

    report = generate_report(items, board_name, filter_user)

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"💾 Reporte guardado en: {output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reporte de tareas desde Monday.com")
    parser.add_argument("--board", required=True, help="ID del board de Monday")
    parser.add_argument("--user", default=None, help="Filtrar por nombre de persona")
    parser.add_argument("--output", default=None, help="Guardar en archivo .md")
    args = parser.parse_args()
    run(args.board, args.user, args.output)
