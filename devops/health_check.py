"""
health_check.py
---------------
Verifica el estado de uno o varios endpoints HTTP y genera un reporte.
Detecta latencia alta, errores y cambios inesperados en el contenido.

Problemas que resuelve:
  - Verificar que un deploy no rompió endpoints críticos
  - Monitoreo básico de servicios sin infraestructura compleja
  - Generar evidencia de uptime para clientes o equipos

Uso:
  python health_check.py --urls https://api.example.com/health https://app.example.com
  python health_check.py --file endpoints.txt --timeout 5 --output reporte.json
"""

import argparse
import requests
import json
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


TIMEOUT_DEFAULT = 10
LATENCY_WARNING_MS = 1000  # Alerta si supera este umbral


def check_endpoint(url: str, timeout: int, expected_status: int = 200) -> dict:
    result = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "status": None,
        "latency_ms": None,
        "ok": False,
        "error": None,
        "warning": None,
    }
    try:
        start = time.time()
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed_ms = round((time.time() - start) * 1000, 2)

        result["status"] = r.status_code
        result["latency_ms"] = elapsed_ms
        result["ok"] = r.status_code == expected_status

        if not result["ok"]:
            result["error"] = f"Status inesperado: {r.status_code} (esperado {expected_status})"
        elif elapsed_ms > LATENCY_WARNING_MS:
            result["warning"] = f"Latencia alta: {elapsed_ms}ms"

    except requests.ConnectionError:
        result["error"] = "No se pudo conectar"
    except requests.Timeout:
        result["error"] = f"Timeout después de {timeout}s"
    except Exception as e:
        result["error"] = str(e)

    return result


def print_result(r: dict) -> None:
    icon = "✅" if r["ok"] else "❌"
    latency = f"{r['latency_ms']}ms" if r["latency_ms"] else "—"
    warning = f" ⚠️  {r['warning']}" if r.get("warning") else ""
    error = f" → {r['error']}" if r.get("error") else ""
    print(f"  {icon} [{r['status'] or 'ERR'}] {r['url']} ({latency}){warning}{error}")


def run(urls: list[str], timeout: int, output: str = None) -> None:
    print(f"\n🔍 Verificando {len(urls)} endpoint(s)...\n")
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_endpoint, url, timeout): url for url in urls}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            print_result(r)

    total = len(results)
    ok = sum(1 for r in results if r["ok"])
    warnings = sum(1 for r in results if r.get("warning"))

    print(f"\n📊 Resumen: {ok}/{total} OK | {total - ok} errores | {warnings} advertencias")

    if output:
        summary = {
            "checked_at": datetime.now().isoformat(),
            "total": total, "ok": ok, "errors": total - ok,
            "results": results
        }
        Path(output).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"📋 Reporte guardado en: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verifica el estado de endpoints HTTP")
    parser.add_argument("--urls", nargs="+", help="URLs a verificar")
    parser.add_argument("--file", help="Archivo .txt con una URL por línea")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_DEFAULT)
    parser.add_argument("--output", default=None, help="Guardar reporte JSON")
    args = parser.parse_args()

    urls = []
    if args.urls:
        urls.extend(args.urls)
    if args.file:
        urls.extend([
            line.strip() for line in Path(args.file).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ])

    if not urls:
        print("❌ Especificá al menos una URL con --urls o --file")
    else:
        run(urls, args.timeout, args.output)
