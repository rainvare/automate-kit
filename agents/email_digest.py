"""
email_digest.py
---------------
Conecta con Gmail via API, recupera emails no leídos del día
y genera un resumen priorizado usando Claude.

Problemas que resuelve:
  - Inbox lleno que tarda en procesar
  - Perder emails importantes entre el ruido
  - Necesitar un resumen diario sin leer todo

Setup (una sola vez):
  1. Habilitar Gmail API en https://console.cloud.google.com
  2. Descargar credentials.json y colocarlo en la misma carpeta
  3. pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client anthropic

Uso:
  export ANTHROPIC_API_KEY=sk-...
  python email_digest.py                    # Emails de hoy
  python email_digest.py --days 3           # Últimos 3 días
  python email_digest.py --output digest.md # Guardar resumen
"""

import argparse
import os
import base64
import json
from pathlib import Path
from datetime import datetime, timedelta

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    """Autentica y retorna el servicio de Gmail."""
    if not HAS_GOOGLE:
        raise ImportError(
            "Instalar dependencias: pip install google-auth-oauthlib "
            "google-auth-httplib2 google-api-python-client"
        )

    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_emails(service, days: int = 1, max_results: int = 50) -> list[dict]:
    """Recupera emails de los últimos N días."""
    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"after:{after_date} is:unread"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    print(f"📬 {len(messages)} email(s) no leídos encontrados")

    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", messageId=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        snippet = detail.get("snippet", "")

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(sin asunto)"),
            "from": headers.get("From", "desconocido"),
            "date": headers.get("Date", ""),
            "snippet": snippet[:300],
        })

    return emails


def generate_digest(emails: list[dict], lang: str = "es") -> str:
    """Genera un resumen priorizado con Claude."""
    if not HAS_ANTHROPIC:
        raise ImportError("Instalar anthropic: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no encontrada.")

    client = anthropic.Anthropic(api_key=api_key)

    emails_text = "\n\n".join([
        f"De: {e['from']}\nAsunto: {e['subject']}\nFecha: {e['date']}\nFragmento: {e['snippet']}"
        for e in emails
    ])

    prompt = f"""Analiza estos emails y genera un digest priorizado en {'español' if lang == 'es' else lang}.

Clasifícalos en:
1. 🔴 Urgente / Requiere acción hoy
2. 🟡 Importante / Responder esta semana
3. 🟢 Informativo / Solo leer
4. 🗑️ Ruido / Puede ignorarse

Para cada categoría lista los emails relevantes con una línea de descripción.
Al final, sugiere el orden en que deberían atenderse.

Emails:
{emails_text}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def run(days: int = 1, output: str = None, lang: str = "es") -> None:
    print(f"\n📧 Email Digest — últimos {days} día(s)\n")

    service = get_gmail_service()
    emails = fetch_emails(service, days)

    if not emails:
        print("✅ No hay emails no leídos en el período especificado.")
        return

    print("🤖 Generando resumen con IA...\n")
    digest = generate_digest(emails, lang)

    header = (
        f"# Email Digest\n"
        f"*{datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"{len(emails)} emails | últimos {days} día(s)*\n\n"
    )
    full_output = header + digest

    if output:
        Path(output).write_text(full_output, encoding="utf-8")
        print(f"💾 Digest guardado en: {output}")
    else:
        print(full_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digest de emails con IA")
    parser.add_argument("--days", type=int, default=1, help="Días hacia atrás (default: 1)")
    parser.add_argument("--output", default=None, help="Guardar en archivo .md")
    parser.add_argument("--lang", default="es")
    args = parser.parse_args()
    run(args.days, args.output, args.lang)
