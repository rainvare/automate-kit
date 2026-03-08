"""
fetch_public_data.py
--------------------
Descarga datos de APIs públicas y los guarda en CSV/Excel listos para analizar.
Soporta: Banco Mundial, REST Countries, Open Exchange Rates (free tier).

Problemas que resuelve:
  - Evitar descargas manuales repetidas de datos públicos
  - Normalizar respuestas de APIs con estructuras inconsistentes
  - Tener un histórico local de datos que cambian con el tiempo

Uso:
  python fetch_public_data.py --source worldbank --indicator NY.GDP.MKTP.CD --countries ARG,VEN,MEX
  python fetch_public_data.py --source countries --output paises.xlsx
  python fetch_public_data.py --source exchangerates --base USD
"""

import argparse
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime


def fetch_worldbank(indicator: str, countries: list[str],
                   start: int = 2000, end: int = 2023) -> pd.DataFrame:
    """Descarga un indicador del Banco Mundial para una lista de países."""
    country_str = ";".join(countries)
    url = (f"https://api.worldbank.org/v2/country/{country_str}/indicator/{indicator}"
           f"?date={start}:{end}&format=json&per_page=500")

    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    if len(data) < 2 or not data[1]:
        print(f"⚠️  Sin datos para {indicator}")
        return pd.DataFrame()

    records = [
        {
            "country": item["country"]["value"],
            "country_code": item["countryiso3code"],
            "indicator": item["indicator"]["value"],
            "year": item["date"],
            "value": item["value"],
        }
        for item in data[1]
    ]
    df = pd.DataFrame(records)
    df["year"] = pd.to_numeric(df["year"])
    df = df.sort_values(["country", "year"])
    print(f"✅ {len(df)} registros descargados — {indicator}")
    return df


def fetch_countries() -> pd.DataFrame:
    """Descarga info básica de todos los países del mundo."""
    r = requests.get("https://restcountries.com/v3.1/all", timeout=15)
    r.raise_for_status()
    data = r.json()

    records = []
    for c in data:
        records.append({
            "name": c.get("name", {}).get("common", ""),
            "official_name": c.get("name", {}).get("official", ""),
            "region": c.get("region", ""),
            "subregion": c.get("subregion", ""),
            "population": c.get("population", None),
            "area_km2": c.get("area", None),
            "capital": ", ".join(c.get("capital", [])),
            "languages": ", ".join(c.get("languages", {}).values()),
            "currencies": ", ".join(c.get("currencies", {}).keys()),
            "timezones": ", ".join(c.get("timezones", [])),
            "independent": c.get("independent", None),
        })

    df = pd.DataFrame(records).sort_values("name")
    print(f"✅ {len(df)} países descargados")
    return df


def fetch_exchange_rates(base: str = "USD") -> pd.DataFrame:
    """Descarga tipos de cambio actuales desde Open Exchange Rates (free)."""
    url = f"https://open.er-api.com/v6/latest/{base}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    rates = data.get("rates", {})
    df = pd.DataFrame([
        {"base": base, "currency": k, "rate": v,
         "updated": data.get("time_last_update_utc", "")}
        for k, v in rates.items()
    ]).sort_values("currency")
    print(f"✅ {len(df)} tipos de cambio descargados (base: {base})")
    return df


def save(df: pd.DataFrame, output: str) -> None:
    out = Path(output)
    if out.suffix in (".xlsx", ".xls"):
        df.to_excel(out, index=False)
    else:
        df.to_csv(out, index=False)
    print(f"💾 Guardado en: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga datos de APIs públicas")
    parser.add_argument("--source", required=True,
                        choices=["worldbank", "countries", "exchangerates"])
    parser.add_argument("--indicator", default="NY.GDP.MKTP.CD",
                        help="Indicador Banco Mundial (default: PIB)")
    parser.add_argument("--countries", default="ARG,MEX,CHL,COL,VEN",
                        help="Códigos ISO separados por coma")
    parser.add_argument("--base", default="USD", help="Moneda base para tipos de cambio")
    parser.add_argument("--output", default=None, help="Archivo de salida")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    default_output = f"{args.source}_{ts}.csv"

    if args.source == "worldbank":
        countries = [c.strip() for c in args.countries.split(",")]
        df = fetch_worldbank(args.indicator, countries)
    elif args.source == "countries":
        df = fetch_countries()
    elif args.source == "exchangerates":
        df = fetch_exchange_rates(args.base)

    if not df.empty:
        save(df, args.output or default_output)
