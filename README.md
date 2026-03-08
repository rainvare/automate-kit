# ⚙️ automate-kit

Scripts de automatización para problemas reales en Data, APIs, DevOps, IA y trabajo administrativo.

Cada script es independiente, documentado, y resuelve un problema concreto. Sin frameworks innecesarios.

---

## Estructura

```
automate-kit/
│
├── data/                        # Excel, CSV y análisis de datos
│   ├── clean_excel.py           # Limpia archivos sucios con reporte de cambios
│   ├── merge_csv.py             # Consolida múltiples archivos en uno
│   └── anomaly_detector.py      # Detecta outliers en series de tiempo
│
├── apis/                        # Integración con APIs externas
│   ├── api_poller.py            # Pollea una API en intervalos, detecta cambios
│   └── fetch_public_data.py     # Descarga datos del Banco Mundial, países, FX
│
├── devops/                      # Operaciones e infraestructura
│   ├── health_check.py          # Verifica endpoints HTTP en paralelo
│   └── backup.py                # Backup comprimido con rotación automática
│
├── ai/                          # Scripts con IA (Claude API)
│   ├── summarize_docs.py        # Resume PDFs, TXTs y DOCXs automáticamente
│   └── batch_classifier.py      # Clasifica listas de textos sin entrenamiento
│
└── agents/                      # Agentes para tareas administrativas
    ├── meeting_notes.py         # Notas estructuradas desde transcripciones
    ├── email_digest.py          # Digest priorizado de emails con Gmail API
    ├── monday_tracker.py        # Reporte de tareas desde Monday.com
    └── time_tracker.py          # Reporte de horas desde log de texto plano
```

---

## Scripts

### 📊 data/

#### `clean_excel.py` — Limpieza de archivos
Normaliza columnas, elimina duplicados y filas vacías, infiere tipos de dato, reporta nulos. Genera reporte JSON de cambios.
```bash
python data/clean_excel.py --input datos.xlsx --output datos_limpio.xlsx
```

#### `merge_csv.py` — Consolidación de archivos
Une múltiples CSVs/Excels de una carpeta en un solo archivo. Alinea columnas automáticamente aunque no coincidan. Agrega columna `_source_file` para trazabilidad.
```bash
python data/merge_csv.py --folder ./reportes --output consolidado.xlsx --pattern "*ventas*"
```

#### `anomaly_detector.py` — Detección de anomalías
Z-score + IQR para detectar outliers en cualquier serie numérica. Genera gráfico con anomalías marcadas y CSV con el detalle.
```bash
python data/anomaly_detector.py --input metricas.csv --column ventas --date_col fecha
```

---

### 🌐 apis/

#### `api_poller.py` — Monitor de APIs
Consulta una API en intervalos definidos, guarda historial en JSONL y alerta cuando cambia un valor específico. Reintentos automáticos con backoff exponencial.
```bash
python apis/api_poller.py --url https://api.example.com/status --interval 60 --watch data.status
```

#### `fetch_public_data.py` — Datos públicos
Descarga datos del Banco Mundial (cualquier indicador), REST Countries o tipos de cambio. Listo para análisis sin setup complejo.
```bash
python apis/fetch_public_data.py --source worldbank --indicator NY.GDP.MKTP.CD --countries ARG,MEX,COL
python apis/fetch_public_data.py --source exchangerates --base USD
```

---

### 🔧 devops/

#### `health_check.py` — Verificación de endpoints
Chequea múltiples URLs en paralelo. Reporta status, latencia y alerta si supera umbral. Salida en JSON.
```bash
python devops/health_check.py --urls https://api.miapp.com/health https://app.miapp.com --output reporte.json
```

#### `backup.py` — Backup con rotación
Comprime carpetas en ZIP con timestamp. Mantiene solo los N más recientes. Loguea todo.
```bash
python devops/backup.py --source ./datos --dest ./backups --keep 7 --prefix prod
```

---

### 🤖 ai/

> Requieren `ANTHROPIC_API_KEY` en variables de entorno.

#### `summarize_docs.py` — Resumen de documentos
Resume PDFs, TXTs y DOCXs en tres estilos: párrafo, bullets o resumen ejecutivo. Procesa carpetas completas.
```bash
export ANTHROPIC_API_KEY=sk-...
python ai/summarize_docs.py --folder ./informes --style executive --output resumenes.md
```

#### `batch_classifier.py` — Clasificador sin entrenamiento
Clasifica cualquier lista de textos en categorías definidas por vos. Sin modelos, sin entrenamiento — solo describe las categorías.
```bash
python ai/batch_classifier.py --input tickets.csv --column descripcion \
  --categories "Bug,Consulta,Facturación,Feature request" --output tickets_clasificados.csv
```

---

### 🗂️ agents/

> Los que usan IA requieren `ANTHROPIC_API_KEY`. Gmail requiere setup OAuth2. Monday requiere API token.

#### `meeting_notes.py` — Notas de reunión
Toma una transcripción y extrae: resumen, decisiones, tareas con responsable/fecha, pendientes. Salida en Markdown + JSON.
```bash
python agents/meeting_notes.py --input transcripcion.txt --output notas.md
```

#### `email_digest.py` — Digest de emails
Conecta con Gmail, recupera no leídos y genera resumen priorizado en 4 niveles (urgente / importante / informativo / ruido).
```bash
python agents/email_digest.py --days 1 --output digest.md
```
*Setup: [Gmail API](https://console.cloud.google.com) → habilitar → descargar `credentials.json`*

#### `monday_tracker.py` — Reporte de tareas
Consulta un board de Monday.com via GraphQL y genera reporte de estado con tareas vencidas, en progreso y completadas.
```bash
export MONDAY_API_TOKEN=...
python agents/monday_tracker.py --board 123456789 --user "Tu Nombre" --output reporte.md
```

#### `time_tracker.py` — Tracker de horas
Parsea un log de texto simple y genera reporte de horas por cliente/proyecto/día. Sin apps, sin suscripciones.
```bash
python agents/time_tracker.py --input mis_horas.txt --output reporte.md
```
Formato del log:
```
2024-03-01 09:00-11:30 | ClienteA | Desarrollo API
2024-03-01 14:00-16:00 | ClienteB | Reunión kick-off
```

---

## Instalación

```bash
git clone https://github.com/rainvare/automate-kit
cd automate-kit
pip install -r requirements.txt
```

### Variables de entorno necesarias

```bash
export ANTHROPIC_API_KEY=sk-...      # Para scripts en ai/ y agents/
export MONDAY_API_TOKEN=...           # Para monday_tracker.py
```

---

## Stack

`Python 3.10+` · `pandas` · `anthropic` · `requests` · `matplotlib` · `google-api-python-client`

---

## Autor

**R. Indira Valentina Réquiz Molina**  
[GitHub](https://github.com/rainvare) · [Portfolio](https://rainvare.github.io/portfolio/)
