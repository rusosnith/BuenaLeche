"""Descarga los .txt listados en data/datasetsLEche.csv y reconstruye dataset.csv/reports.json.

El CSV de entrada (exportado del sistema LABVIMA) trae, por cada informe, un link de
descarga en la columna "Descargar TXT" con la forma:
    http://190.105.213.89/administracion/descargatxt.php?Id=02988264

Este script:
1. Lee ese CSV.
2. Descarga cada .txt (si todavía no existe localmente) a data/.
3. Parsea todos los .txt disponibles con el parser existente (buenaleche.parser).
4. Regenera data/dataset.csv y data/reports.json con todos los informes.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buenaleche.dataset import write_dataset
from buenaleche.parser import parse_report

DATA_DIR = ROOT / "data"
LINKS_CSV = DATA_DIR / "datasetsLEche.csv"


def extract_report_id(url: str) -> str | None:
    if not url:
        return None
    values = parse_qs(urlparse(url).query).get("Id")
    return values[0] if values else None


def download_txt(url: str, destination: Path, *, timeout: int = 30) -> bool:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content = response.content
    if not content.strip():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--links-csv", default=str(LINKS_CSV), help="CSV con los links de descarga")
    parser.add_argument("--data-dir", default=str(DATA_DIR), help="Directorio donde guardar los .txt y el dataset")
    parser.add_argument("--force", action="store_true", help="Vuelve a descargar aunque el .txt ya exista localmente")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    links_csv = Path(args.links_csv)
    data_dir = Path(args.data_dir)

    with links_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    reports = []
    skipped: list[dict[str, str]] = []
    downloaded = 0

    for row in rows:
        protocolo = row.get("Protocolo", "")
        url = (row.get("Descargar TXT") or "").strip()
        report_id = extract_report_id(url)

        if not report_id:
            skipped.append({"protocolo": protocolo, "motivo": "sin URL de TXT"})
            continue

        source_id = f"P{report_id}"
        local_path = data_dir / f"{source_id}.txt"

        if args.force or not local_path.exists():
            try:
                ok = download_txt(url, local_path)
            except requests.RequestException as exc:
                skipped.append({"protocolo": protocolo, "motivo": f"error de descarga ({exc})"})
                continue

            if ok:
                downloaded += 1
            elif not local_path.exists():
                skipped.append({"protocolo": protocolo, "motivo": "informe aún no disponible (contenido vacío)"})
                continue

        try:
            reports.append(parse_report(local_path, source_id=source_id))
        except Exception as exc:  # noqa: BLE001 - queremos seguir con el resto de informes
            skipped.append({"protocolo": protocolo, "motivo": f"error de parseo ({exc})"})

    reports.sort(key=lambda report: report.protocolo or 0)
    csv_path, json_path = write_dataset(reports, data_dir)

    print(f"Informes en el CSV de links: {len(rows)}")
    print(f"Archivos .txt descargados en esta corrida: {downloaded}")
    print(f"Informes incorporados al dataset: {len(reports)}")
    print(f"Omitidos: {len(skipped)}")
    for item in skipped:
        print(f"  - Protocolo {item['protocolo']}: {item['motivo']}")
    print(f"Dataset: {csv_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
