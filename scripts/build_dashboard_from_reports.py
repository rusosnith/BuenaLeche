from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buenaleche.dashboard import build_dashboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera dist/index.html a partir de data/reports.json")
    parser.add_argument("--reports-json", default="data/reports.json", help="Ruta al reports.json")
    parser.add_argument("--output", default="dist/index.html", help="Ruta del HTML de salida")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reports_path = Path(args.reports_json)
    output_path = Path(args.output)

    if not reports_path.exists():
        raise SystemExit(f"No existe el archivo de reportes: {reports_path}")

    reports = json.loads(reports_path.read_text(encoding="utf-8"))
    html_path = build_dashboard(reports, output_path)
    print(json.dumps({"reports": len(reports), "html": str(html_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
