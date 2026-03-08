"""
api_poller.py
-------------
Consulta una API REST en intervalos definidos, guarda las respuestas
y detecta cambios entre consultas. Útil para monitorear endpoints
o rastrear datos que cambian con el tiempo.

Problemas que resuelve:
  - Monitorear el estado de una API de terceros
  - Registrar histórico de respuestas para análisis posterior
  - Detectar cuándo cambia un valor específico (precio, estado, etc.)

Uso:
  python api_poller.py --url https://api.example.com/data --interval 60
  python api_poller.py --url https://api.coinbase.com/v2/prices/BTC-USD/spot --interval 30 --watch price.amount
"""

import argparse
import requests
import json
import time
import logging
from pathlib import Path
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("api_poller.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def get_nested(data: dict, dotted_key: str):
    """Accede a claves anidadas con notación punto. Ej: 'data.price.amount'"""
    keys = dotted_key.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return None
    return val


def fetch(url: str, headers: dict = None, timeout: int = 10,
          retries: int = 3) -> dict | None:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.warning(f"Intento {attempt}/{retries} fallido: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    log.error(f"Todos los intentos fallaron para {url}")
    return None


def poll(url: str, interval: int, watch_key: str = None,
         output_dir: str = ".", max_runs: int = None) -> None:

    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    history_file = out / "poll_history.jsonl"

    log.info(f"Iniciando polling — URL: {url} | Intervalo: {interval}s")
    if watch_key:
        log.info(f"Monitoreando cambios en: {watch_key}")

    last_value = None
    runs = 0

    while True:
        if max_runs and runs >= max_runs:
            log.info("Máximo de ejecuciones alcanzado. Finalizando.")
            break

        data = fetch(url)
        ts = datetime.now().isoformat()

        if data:
            record = {"timestamp": ts, "data": data}
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            if watch_key:
                current_value = get_nested(data, watch_key)
                if current_value != last_value:
                    if last_value is not None:
                        log.info(f"🔔 CAMBIO detectado en '{watch_key}': {last_value} → {current_value}")
                    else:
                        log.info(f"📍 Valor inicial de '{watch_key}': {current_value}")
                    last_value = current_value
                else:
                    log.info(f"Sin cambios en '{watch_key}': {current_value}")
            else:
                log.info(f"✅ Respuesta recibida ({len(str(data))} chars)")
        else:
            log.error(f"❌ Sin respuesta en {ts}")

        runs += 1
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pollea una API REST en intervalos")
    parser.add_argument("--url", required=True)
    parser.add_argument("--interval", type=int, default=60, help="Segundos entre consultas")
    parser.add_argument("--watch", default=None,
                        help="Clave a monitorear con notación punto (ej: data.price)")
    parser.add_argument("--output", default=".", help="Directorio de salida")
    parser.add_argument("--runs", type=int, default=None,
                        help="Número máximo de ejecuciones (omitir = infinito)")
    args = parser.parse_args()
    poll(args.url, args.interval, args.watch, args.output, args.runs)
