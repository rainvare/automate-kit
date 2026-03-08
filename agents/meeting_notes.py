"""
meeting_notes.py
----------------
Toma una transcripción de reunión (texto plano) y genera:
  - Resumen ejecutivo
  - Decisiones tomadas
  - Tareas asignadas (con responsable y fecha si se mencionan)
  - Puntos pendientes

Problemas que resuelve:
  - Reuniones largas donde nadie tomó notas estructuradas
  - Transcripciones de Zoom/Meet que hay que procesar manualmente
  - Seguimiento de compromisos acordados en reunión

Dependencias:
  pip install anthropic

Uso:
  export ANTHROPIC_API_KEY=sk-...
  python meeting_notes.py --input transcripcion.txt
  python meeting_notes.py --input reunion.txt --output notas.md --lang es
"""

import argparse
import os
import json
from pathlib import Path
from datetime import datetime

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """Eres un asistente especializado en procesar transcripciones de reuniones.
Tu tarea es extraer información estructurada de manera precisa y concisa.
Responde SIEMPRE en el idioma que se te indique.
No inventes información que no esté en la transcripción."""

USER_PROMPT = """Analiza esta transcripción de reunión y genera un reporte estructurado en JSON con exactamente este formato:

{{
  "resumen": "Resumen ejecutivo en 2-3 oraciones",
  "participantes": ["lista de nombres mencionados"],
  "decisiones": ["lista de decisiones tomadas"],
  "tareas": [
    {{
      "descripcion": "qué hay que hacer",
      "responsable": "nombre o 'Sin asignar'",
      "fecha": "fecha mencionada o 'Sin fecha'"
    }}
  ],
  "pendientes": ["temas que quedaron sin resolver o para próxima reunión"],
  "proxima_reunion": "fecha/hora mencionada o null"
}}

Idioma de respuesta: {lang}

Transcripción:
{transcript}"""


def process_transcript(transcript: str, lang: str = "es") -> dict:
    if not HAS_ANTHROPIC:
        raise ImportError("Instalar anthropic: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no encontrada en variables de entorno.")

    client = anthropic.Anthropic(api_key=api_key)

    # Truncar si es muy larga
    max_chars = 60000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[... transcripción truncada ...]"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": USER_PROMPT.format(lang=lang, transcript=transcript)
        }]
    )

    raw = message.content[0].text.strip()

    # Limpiar markdown si viene envuelto en ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


def format_markdown(data: dict, source_file: str) -> str:
    lines = [
        f"# Notas de reunión",
        f"*Fuente: {source_file} | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        f"## Resumen\n{data.get('resumen', '—')}\n",
    ]

    if data.get("participantes"):
        lines.append("## Participantes")
        lines.append(", ".join(data["participantes"]) + "\n")

    if data.get("decisiones"):
        lines.append("## Decisiones tomadas")
        for d in data["decisiones"]:
            lines.append(f"- {d}")
        lines.append("")

    if data.get("tareas"):
        lines.append("## Tareas")
        lines.append("| Tarea | Responsable | Fecha |")
        lines.append("|---|---|---|")
        for t in data["tareas"]:
            lines.append(f"| {t['descripcion']} | {t['responsable']} | {t['fecha']} |")
        lines.append("")

    if data.get("pendientes"):
        lines.append("## Pendientes para próxima reunión")
        for p in data["pendientes"]:
            lines.append(f"- {p}")
        lines.append("")

    if data.get("proxima_reunion"):
        lines.append(f"## Próxima reunión\n{data['proxima_reunion']}\n")

    return "\n".join(lines)


def run(input_file: str, output: str = None, lang: str = "es") -> None:
    p = Path(input_file)
    if not p.exists():
        print(f"❌ Archivo no encontrado: {p}")
        return

    transcript = p.read_text(encoding="utf-8", errors="ignore")
    if not transcript.strip():
        print("❌ El archivo está vacío.")
        return

    print(f"📋 Procesando transcripción: {p.name} ({len(transcript)} caracteres)")

    data = process_transcript(transcript, lang)
    md = format_markdown(data, p.name)

    if output:
        Path(output).write_text(md, encoding="utf-8")
        print(f"✅ Notas guardadas en: {output}")
    else:
        print("\n" + md)

    # También guardar JSON raw
    json_out = Path(output).with_suffix(".json") if output else p.with_suffix(".notes.json")
    json_out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"📊 JSON guardado en: {json_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera notas estructuradas de reuniones")
    parser.add_argument("--input", required=True, help="Transcripción en .txt")
    parser.add_argument("--output", default=None, help="Guardar en .md")
    parser.add_argument("--lang", default="es", help="Idioma (default: es)")
    args = parser.parse_args()
    run(args.input, args.output, args.lang)
