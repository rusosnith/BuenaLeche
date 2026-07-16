from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buenaleche.dataset import CSV_COLUMNS, report_to_rows
from buenaleche.parser import parse_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Integra de forma incremental los .txt locales en data/dataset.csv y data/reports.json. "
            "Solo procesa archivos cuyo source_id todavía no esté presente en dataset.csv."
        )
    )
    parser.add_argument("--data-dir", default="data", help="Directorio con .txt, dataset.csv y reports.json")
    parser.add_argument("--txt-glob", default="P*.txt", help="Patrón de búsqueda de informes TXT")
    parser.add_argument("--dry-run", action="store_true", help="No escribe cambios, solo informa qué haría")
    return parser.parse_args()


def load_dataset_rows(csv_path: Path) -> tuple[list[dict[str, str]], set[str]]:
    if not csv_path.exists():
        return [], set()

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    source_ids = {row.get("source_id", "").strip() for row in rows if row.get("source_id")}
    return rows, source_ids


def load_reports_index(json_path: Path) -> dict[str, dict]:
    if not json_path.exists():
        return {}

    reports = json.loads(json_path.read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for report in reports:
        source_id = (report.get("source_id") or "").strip()
        if source_id:
            index[source_id] = report
    return index


def write_dataset_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_reports_json(json_path: Path, reports_index: dict[str, dict]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_reports = sorted(
        reports_index.values(),
        key=lambda item: (
            item.get("fecha_proceso") or item.get("fecha_ingreso") or "",
            item.get("protocolo") or 0,
            item.get("source_id") or "",
        ),
    )
    json_path.write_text(json.dumps(sorted_reports, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    csv_path = data_dir / "dataset.csv"
    json_path = data_dir / "reports.json"

    existing_rows, existing_source_ids = load_dataset_rows(csv_path)
    reports_index = load_reports_index(json_path)

    txt_paths = sorted(data_dir.glob(args.txt_glob))
    candidates = [path for path in txt_paths if path.stem not in existing_source_ids]

    parsed_reports = []
    parse_errors: list[str] = []
    added_rows = 0

    for txt_path in candidates:
        source_id = txt_path.stem
        try:
            report = parse_report(txt_path, source_id=source_id)
        except Exception as exc:  # noqa: BLE001 - queremos continuar con el resto
            parse_errors.append(f"{txt_path.name}: {exc}")
            continue

        parsed_reports.append(report)
        reports_index[source_id] = report.to_record()

        report_rows = report_to_rows(report)
        if report_rows:
            existing_rows.extend(report_rows)
            added_rows += len(report_rows)

    if not args.dry_run:
        if parsed_reports:
            if added_rows:
                write_dataset_rows(csv_path, existing_rows)
            write_reports_json(json_path, reports_index)

    summary = {
        "txt_total": len(txt_paths),
        "source_ids_already_in_dataset": len(existing_source_ids),
        "txt_candidates": len(candidates),
        "reports_parsed": len(parsed_reports),
        "rows_added": added_rows,
        "parse_errors": len(parse_errors),
        "dry_run": args.dry_run,
        "dataset": str(csv_path),
        "reports_json": str(json_path),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for error in parse_errors:
        print(f"ERROR: {error}")

    return 0 if not parse_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
