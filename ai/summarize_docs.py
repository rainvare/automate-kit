"""
summarize_docs.py
-----------------
Resume documentos (PDF, TXT, DOCX) usando la API de Claude.
Procesa uno o varios archivos y genera resúmenes en el idioma del documento.

Problemas que resuelve:
  - Revisar decenas de documentos rápidamente
  - Generar resúmenes ejecutivos automáticos
  - Extraer puntos clave de informes largos

Dependencias:
  pip install anthropic pymupdf python-docx

Uso:
  export ANTHROPIC_API_KEY=sk-...
  python summarize_docs.py --input informe.pdf
  python summarize_docs.py --folder ./documentos --output resúmenes.md
  python summarize_docs.py --input contrato.pdf --style bullet --lang es
"""

import argparse
import os
from pathlib import Path
from datetime import datetime

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import fitz  # PyMuPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


STYLE_PROMPTS = {
    "paragraph": "Resume el siguiente documento en 3-5 párrafos concisos.",
    "bullet": "Resume el siguiente documento como una lista de puntos clave (máximo 10 puntos).",
    "executive": (
        "Genera un resumen ejecutivo del siguiente documento con estas secciones: "
        "1. Contexto (1 párrafo), 2. Puntos clave (lista), 3. Conclusión (1 párrafo)."
    ),
}


def extract_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")
    elif ext == ".pdf":
        if not HAS_PDF:
            raise ImportError("Instalar pymupdf: pip install pymupdf")
        doc = fitz.open(str(file_path))
        return "\n".join(page.get_text() for page in doc)
    elif ext in (".docx", ".doc"):
        if not HAS_DOCX:
            raise ImportError("Instalar python-docx: pip install python-docx")
        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def summarize(text: str, style: str = "bullet", lang: str = "es",
              max_chars: int = 80000) -> str:
    if not HAS_ANTHROPIC:
        raise ImportError("Instalar anthropic: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Variable de entorno ANTHROPIC_API_KEY no encontrada.")

    client = anthropic.Anthropic(api_key=api_key)

    # Truncar si excede el límite
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... documento truncado ...]"

    prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["bullet"])
    prompt += f"\n\nResponde en {'español' if lang == 'es' else lang}.\n\nDocumento:\n{text}"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def process_file(file_path: Path, style: str, lang: str) -> dict:
    print(f"  📄 Procesando: {file_path.name}")
    try:
        text = extract_text(file_path)
        if not text.strip():
            return {"file": file_path.name, "summary": "⚠️ Documento vacío o sin texto extraíble."}
        summary = summarize(text, style, lang)
        return {"file": file_path.name, "summary": summary}
    except Exception as e:
        return {"file": file_path.name, "summary": f"❌ Error: {e}"}


def run(input_file: str = None, folder: str = None,
        style: str = "bullet", lang: str = "es", output: str = None) -> None:

    files = []
    if input_file:
        files.append(Path(input_file))
    if folder:
        folder_path = Path(folder)
        files.extend([
            f for f in folder_path.iterdir()
            if f.suffix.lower() in (".pdf", ".txt", ".docx", ".doc")
        ])

    if not files:
        print("❌ No se encontraron archivos para procesar.")
        return

    print(f"\n📚 Resumiendo {len(files)} documento(s) — estilo: {style}\n")
    results = [process_file(f, style, lang) for f in files]

    # Output en markdown
    md_lines = [f"# Resúmenes automáticos\n*Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"]
    for r in results:
        md_lines.append(f"\n## {r['file']}\n\n{r['summary']}\n\n---")

    md_content = "\n".join(md_lines)

    if output:
        Path(output).write_text(md_content, encoding="utf-8")
        print(f"\n💾 Resúmenes guardados en: {output}")
    else:
        print("\n" + md_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume documentos con Claude AI")
    parser.add_argument("--input", default=None, help="Archivo individual a resumir")
    parser.add_argument("--folder", default=None, help="Carpeta con documentos")
    parser.add_argument("--style", default="bullet",
                        choices=["paragraph", "bullet", "executive"])
    parser.add_argument("--lang", default="es", help="Idioma del resumen (default: es)")
    parser.add_argument("--output", default=None, help="Guardar en archivo .md")
    args = parser.parse_args()
    run(args.input, args.folder, args.style, args.lang, args.output)
