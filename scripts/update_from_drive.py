from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buenaleche.dashboard import build_dashboard
from buenaleche.dataset import load_state, save_state, write_dataset
from buenaleche.drive_sync import build_drive_service, download_file, folder_id_from_url, list_reports
from buenaleche.parser import parse_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Actualiza dataset y dashboard desde informes PDF/TXT en Google Drive")
    parser.add_argument("--folder-url", default=os.getenv("DRIVE_FOLDER_URL", ""), help="URL de la carpeta de Drive")
    parser.add_argument("--credentials", default=os.getenv("GOOGLE_CREDENTIALS_JSON", "service_account.json"), help="JSON de la cuenta de servicio")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_DIR", "dist"), help="Directorio de salida")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.folder_url:
        raise SystemExit("Falta DRIVE_FOLDER_URL o --folder-url")

    output_dir = Path(args.output_dir)
    data_dir = Path("data")
    reports_dir = data_dir / "reports"
    state_path = data_dir / "state.json"
    state = load_state(state_path)
    state.setdefault("files", {})

    service = build_drive_service(args.credentials)
    folder_id = folder_id_from_url(args.folder_url)
    files = list_reports(service, folder_id)

    reports = []
    for file_item in reversed(files):
        file_state = state["files"].get(file_item.id)
        if file_state and file_state.get("modified_time") == file_item.modified_time:
            report_path = Path(file_state["local_path"])
            if report_path.exists():
                reports.append(parse_report(report_path, source_id=file_item.id))
                continue

        local_path = reports_dir / file_item.name
        download_file(service, file_item.id, local_path)
        report = parse_report(local_path, source_id=file_item.id)
        reports.append(report)
        state["files"][file_item.id] = {
            "name": file_item.name,
            "modified_time": file_item.modified_time,
            "local_path": str(local_path),
        }

    csv_path, json_path = write_dataset(reports, data_dir)
    dashboard_path = build_dashboard([report.to_record() for report in reports], output_dir / "index.html")
    save_state(state, state_path)

    summary = {
        "files_seen": len(files),
        "reports": len(reports),
        "csv": str(csv_path),
        "json": str(json_path),
        "html": str(dashboard_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
