from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .parser import Report, SampleRow


DATA_DIR = Path("data")

CSV_COLUMNS = [
    "source_id",
    "source_file",
    "nro_informe",
    "protocolo",
    "fecha_ingreso",
    "fecha_proceso",
    "propietario",
    "especie",
    "muestras_recibidas",
    "identificacion",
    "rodeo",
    "mg",
    "proteina",
    "lactosa",
    "sng",
    "st",
    "prov",
    "caseina",
    "mun",
    "crioscopia",
    "rcs",
    "rm",
    "observaciones",
]


def load_state(path: Path = DATA_DIR / "state.json") -> dict:
    if not path.exists():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict, path: Path = DATA_DIR / "state.json") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def report_to_rows(report: Report) -> list[dict]:
    rows: list[dict] = []
    for row in report.rows:
        row_dict = _sample_row_to_dict(row)
        rows.append(
            {
                "source_id": report.source_id,
                "source_file": report.source_name,
                "nro_informe": report.nro_informe,
                "protocolo": report.protocolo,
                "fecha_ingreso": _iso(report.fecha_ingreso),
                "fecha_proceso": _iso(report.fecha_proceso),
                "propietario": report.propietario,
                "especie": report.especie,
                "muestras_recibidas": report.muestras_recibidas,
                "observaciones": report.observaciones,
                **row_dict,
            }
        )
    return rows


def write_dataset(reports: Iterable[Report], output_dir: Path = DATA_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    reports_list = list(reports)
    for report in reports_list:
        rows.extend(report_to_rows(report))

    csv_path = output_dir / "dataset.csv"
    json_path = output_dir / "reports.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(
        json.dumps([report.to_record() for report in reports_list], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return csv_path, json_path


def _sample_row_to_dict(row: SampleRow) -> dict:
    return asdict(row)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None
