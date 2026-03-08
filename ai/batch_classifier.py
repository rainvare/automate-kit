"""
batch_classifier.py
-------------------
Clasifica cualquier lista de textos (emails, tickets, comentarios, productos)
usando Claude. Sin entrenamiento previo — solo describí las categorías.

Problemas que resuelve:
  - Clasificar cientos de tickets de soporte por tipo
  - Categorizar comentarios de clientes por sentimiento o tema
  - Etiquetar productos, tareas o cualquier lista de texto

Uso:
  export ANTHROPIC_API_KEY=sk-...

  # Clasificar tickets de soporte
  python batch_classifier.py --input tickets.csv --column descripcion \
    --categories "Bug técnico,Consulta,Facturación,Solicitud de feature" \
    --output tickets_clasificados.csv

  # Clasificar con archivo de categorías
  python batch_classifier.py --input comentarios.xlsx --column texto \
    --categories_file categorias.txt --batch_size 20
"""

import argparse
import os
import json
import time
import pandas as pd
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def classify_batch(texts: list[str], categories: list[str],
                   client, context: str = "") -> list[dict]:
    """Clasifica un batch de textos de una sola llamada a la API."""

    categories_str = "\n".join(f"- {c}" for c in categories)
    items_str = "\n".join(f"{i+1}. {text[:300]}" for i, text in enumerate(texts))

    prompt = f"""Clasifica cada uno de los siguientes textos en UNA de estas categorías:

{categories_str}

{f'Contexto adicional: {context}' if context else ''}

Responde SOLO con un JSON array con exactamente {len(texts)} objetos, sin texto adicional:
[
  {{"index": 1, "category": "nombre_categoria", "confidence": "high|medium|low", "reason": "breve razón"}},
  ...
]

Textos a clasificar:
{items_str}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


def run(input_file: str, column: str, categories: list[str],
        output: str = None, batch_size: int = 10,
        context: str = "") -> None:

    if not HAS_ANTHROPIC:
        print("❌ Instalar: pip install anthropic")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY no encontrada.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # Cargar datos
    p = Path(input_file)
    df = pd.read_excel(p) if p.suffix in (".xlsx", ".xls") else pd.read_csv(p)

    if column not in df.columns:
        print(f"❌ Columna '{column}' no encontrada. Disponibles: {list(df.columns)}")
        return

    texts = df[column].fillna("").astype(str).tolist()
    total = len(texts)
    print(f"📊 {total} textos a clasificar en {len(categories)} categorías")
    print(f"📦 Batch size: {batch_size} | Llamadas a API: {(total + batch_size - 1) // batch_size}")

    results = [None] * total

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"  🔄 Batch {batch_num}/{total_batches} ({len(batch)} items)...")

        try:
            classified = classify_batch(batch, categories, client, context)
            for item in classified:
                idx = i + item["index"] - 1
                if 0 <= idx < total:
                    results[idx] = item
            time.sleep(0.5)  # Rate limit gentil
        except Exception as e:
            print(f"  ⚠️  Error en batch {batch_num}: {e}")
            for j in range(len(batch)):
                if results[i + j] is None:
                    results[i + j] = {"category": "Error", "confidence": "low", "reason": str(e)}

    # Agregar columnas al DataFrame
    df["categoria"] = [r["category"] if r else "Sin clasificar" for r in results]
    df["confianza"] = [r.get("confidence", "") if r else "" for r in results]
    df["razon"] = [r.get("reason", "") if r else "" for r in results]

    # Estadísticas
    print(f"\n✅ Clasificación completada:")
    print(df["categoria"].value_counts().to_string())

    # Guardar
    out_path = Path(output) if output else p.with_stem(p.stem + "_clasificado")
    if out_path.suffix in (".xlsx", ".xls"):
        df.to_excel(out_path, index=False)
    else:
        df.to_csv(out_path, index=False)
    print(f"\n💾 Guardado en: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clasifica textos con IA")
    parser.add_argument("--input", required=True)
    parser.add_argument("--column", required=True, help="Columna con el texto a clasificar")
    parser.add_argument("--categories", required=False,
                        help="Categorías separadas por coma")
    parser.add_argument("--categories_file", required=False,
                        help="Archivo .txt con una categoría por línea")
    parser.add_argument("--output", default=None)
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--context", default="",
                        help="Contexto adicional para mejorar clasificación")
    args = parser.parse_args()

    categories = []
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    elif args.categories_file:
        categories = [
            line.strip() for line in Path(args.categories_file).read_text().splitlines()
            if line.strip()
        ]

    if not categories:
        print("❌ Especificá categorías con --categories o --categories_file")
    else:
        run(args.input, args.column, categories, args.output, args.batch_size, args.context)
