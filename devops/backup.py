"""
backup.py
---------
Hace backup comprimido de archivos o carpetas con rotación automática.
Mantiene solo los N backups más recientes y loguea todo.

Problemas que resuelve:
  - Backups manuales que se olvidan
  - Acumulación infinita de archivos de backup
  - Falta de trazabilidad de qué se respaldó y cuándo

Uso:
  python backup.py --source ./datos --dest ./backups
  python backup.py --source ./proyecto --dest /mnt/backup --keep 7 --prefix prod
"""

import argparse
import shutil
import logging
import os
from pathlib import Path
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("backup.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def create_backup(source: str, dest: str, prefix: str = "backup",
                  keep: int = 5) -> Path | None:
    source_path = Path(source)
    dest_path = Path(dest)

    if not source_path.exists():
        log.error(f"Fuente no encontrada: {source_path}")
        return None

    dest_path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{prefix}_{ts}"
    backup_path = dest_path / backup_name

    log.info(f"Iniciando backup: {source_path} → {backup_path}.zip")

    try:
        shutil.make_archive(str(backup_path), 'zip', str(source_path))
        final_path = Path(str(backup_path) + ".zip")
        size_mb = round(final_path.stat().st_size / 1024 / 1024, 2)
        log.info(f"✅ Backup creado: {final_path.name} ({size_mb} MB)")
    except Exception as e:
        log.error(f"Error creando backup: {e}")
        return None

    # Rotación: eliminar backups viejos
    existing = sorted(dest_path.glob(f"{prefix}_*.zip"))
    if len(existing) > keep:
        to_delete = existing[:len(existing) - keep]
        for old in to_delete:
            old.unlink()
            log.info(f"🗑️  Eliminado backup antiguo: {old.name}")

    log.info(f"📦 Backups activos: {len(existing) - len(to_delete) if len(existing) > keep else len(existing)}/{keep}")
    return final_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup comprimido con rotación automática")
    parser.add_argument("--source", required=True, help="Carpeta o archivo a respaldar")
    parser.add_argument("--dest", required=True, help="Carpeta de destino")
    parser.add_argument("--keep", type=int, default=5,
                        help="Número de backups a conservar (default: 5)")
    parser.add_argument("--prefix", default="backup",
                        help="Prefijo del nombre del archivo (default: backup)")
    args = parser.parse_args()
    create_backup(args.source, args.dest, args.prefix, args.keep)
