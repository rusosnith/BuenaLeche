from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BuenaLeche Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffaf2;
      --ink: #1f2933;
      --muted: #667085;
      --accent: #0f766e;
      --accent-2: #b45309;
      --border: rgba(31, 41, 51, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 30%),
        radial-gradient(circle at top right, rgba(180, 83, 9, 0.12), transparent 24%),
        var(--bg);
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 32px 20px 48px; }
    .hero {
      display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      align-items: end; margin-bottom: 24px;
    }
    .eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: 12px; color: var(--accent); }
    h1 { margin: 0; font-size: clamp(32px, 6vw, 56px); line-height: 0.95; }
    .subtitle { color: var(--muted); max-width: 70ch; }
    .cards { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin: 24px 0; }
    .card, .panel {
      background: rgba(255, 250, 242, 0.82);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: 0 18px 40px rgba(31,41,51,.08);
      backdrop-filter: blur(10px);
    }
    .card { padding: 18px; }
    .card .value { font-size: 32px; font-weight: 700; margin-top: 6px; }
    .grid { display: grid; gap: 16px; grid-template-columns: 2fr 1fr; }
    .panel { padding: 18px; }
    .panel h2 { margin: 0 0 14px; font-size: 18px; }
    .chart-shell { position: relative; height: 320px; min-height: 320px; }
    canvas { display: block; width: 100% !important; height: 100% !important; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 600; }
    .small { color: var(--muted); font-size: 13px; }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .chart-shell { height: 280px; min-height: 280px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <div class="eyebrow">LABVIMA</div>
        <h1>BuenaLeche</h1>
      </div>
      <div class="subtitle">
        Dashboard generado automáticamente desde PDFs subidos a Google Drive. El panel resume volumen, tendencia y distribución de los indicadores principales.
      </div>
    </div>

    <div class="cards">
      <div class="card"><div class="small">Informes</div><div class="value">{{total_reports}}</div></div>
      <div class="card"><div class="small">Filas analizadas</div><div class="value">{{total_rows}}</div></div>
      <div class="card"><div class="small">Último informe</div><div class="value">{{last_report}}</div></div>
      <div class="card"><div class="small">Propietarios</div><div class="value">{{owners}}</div></div>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Promedio de MG por informe</h2>
        <div class="chart-shell">
          <canvas id="mgChart"></canvas>
        </div>
      </div>
      <div class="panel">
        <h2>Distribución de identificaciones</h2>
        <div class="chart-shell">
          <canvas id="idChart"></canvas>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px;">
      <h2>Resumen de los últimos informes</h2>
      <table>
        <thead><tr><th>Informe</th><th>Fecha</th><th>Propietario</th><th>Filas</th><th>MG</th><th>RCS</th></tr></thead>
        <tbody>
          {{recent_rows}}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    const mgLabels = {{mg_labels}};
    const mgValues = {{mg_values}};
    new Chart(document.getElementById('mgChart'), {
      type: 'line',
      data: { labels: mgLabels, datasets: [{ label: 'MG promedio', data: mgValues, tension: 0.3, borderColor: '#0f766e', backgroundColor: 'rgba(15,118,110,.15)', fill: true }] },
      options: { responsive: true, maintainAspectRatio: false }
    });

    const idLabels = {{id_labels}};
    const idValues = {{id_values}};
    new Chart(document.getElementById('idChart'), {
      type: 'doughnut',
      data: { labels: idLabels, datasets: [{ data: idValues, backgroundColor: ['#0f766e', '#b45309', '#7c3aed', '#dc2626', '#0891b2', '#16a34a'] }] },
      options: { responsive: true, maintainAspectRatio: false }
    });
  </script>
</body>
</html>
"""


def build_dashboard(reports: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_rows = []
    mg_series = []
    id_counts = defaultdict(int)
    owners = set()

    sorted_reports = sorted(
        reports,
        key=lambda item: (item.get("fecha_proceso") or item.get("fecha_ingreso") or "", item.get("protocolo") or 0),
    )

    for report in sorted_reports:
        rows = report.get("rows", [])
        owners.add(report.get("propietario") or "")
        mg_values = [row.get("mg") for row in rows if row.get("mg") is not None]
        rcs_values = [row.get("rcs") for row in rows if row.get("rcs") is not None]
        mg_avg = round(sum(mg_values) / len(mg_values), 3) if mg_values else None
        rcs_avg = round(sum(rcs_values) / len(rcs_values), 3) if rcs_values else None
        report_rows.append(
            {
                "protocolo": report.get("protocolo") or report.get("nro_informe") or "-",
                "fecha": report.get("fecha_proceso") or report.get("fecha_ingreso") or "-",
                "propietario": report.get("propietario") or "-",
                "filas": len(rows),
                "mg_avg": mg_avg,
                "rcs_avg": rcs_avg,
            }
        )
        if mg_avg is not None:
            mg_series.append((report_rows[-1]["fecha"], mg_avg))
        for row in rows:
            id_counts[row.get("identificacion") or "-"] += 1

    recent_rows_html = "\n".join(
        f"<tr><td>{item['protocolo']}</td><td>{item['fecha']}</td><td>{item['propietario']}</td><td>{item['filas']}</td><td>{item['mg_avg'] if item['mg_avg'] is not None else ''}</td><td>{item['rcs_avg'] if item['rcs_avg'] is not None else ''}</td></tr>"
        for item in report_rows[-12:][::-1]
    )

    html = HTML_TEMPLATE
    html = html.replace("{{total_reports}}", str(len(sorted_reports)))
    html = html.replace("{{total_rows}}", str(sum(len(r.get('rows', [])) for r in sorted_reports)))
    html = html.replace("{{last_report}}", str(report_rows[-1]["protocolo"]) if report_rows else "-")
    html = html.replace("{{owners}}", str(len({o for o in owners if o})))
    html = html.replace("{{recent_rows}}", recent_rows_html)
    html = html.replace("{{mg_labels}}", json.dumps([label for label, _ in mg_series], ensure_ascii=False))
    html = html.replace("{{mg_values}}", json.dumps([value for _, value in mg_series], ensure_ascii=False))
    sorted_ids = sorted(id_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    html = html.replace("{{id_labels}}", json.dumps([label for label, _ in sorted_ids], ensure_ascii=False))
    html = html.replace("{{id_values}}", json.dumps([value for _, value in sorted_ids], ensure_ascii=False))

    output_path.write_text(html, encoding="utf-8")
    return output_path
