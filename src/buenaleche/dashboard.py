from __future__ import annotations

from html import escape
import json
from pathlib import Path


METRIC_SPECS = [
    {"key": "mg", "label": "MG", "color": "#0f766e"},
    {"key": "proteina", "label": "Prote", "color": "#b45309"},
    {"key": "lactosa", "label": "Lacto", "color": "#0891b2"},
    {"key": "sng", "label": "SNG", "color": "#7c3aed"},
    {"key": "st", "label": "ST", "color": "#dc2626"},
    {"key": "prov", "label": "Pro.V", "color": "#16a34a"},
    {"key": "caseina", "label": "Caseína", "color": "#ea580c"},
    {"key": "mun", "label": "MUN", "color": "#0284c7"},
    {"key": "crioscopia", "label": "Crioscopía", "color": "#9333ea"},
    {"key": "rcs", "label": "RCS", "color": "#be123c"},
    {"key": "rm", "label": "RM", "color": "#475569"},
]


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
    .stack { display: grid; gap: 16px; }
    .panel { padding: 18px; }
    .panel h2 { margin: 0 0 14px; font-size: 18px; }
    .panel-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .panel-note { color: var(--muted); font-size: 13px; }
    .controls-panel { padding: 20px; }
    .controls-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin-bottom: 18px;
    }
    .control-label {
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--accent);
      margin-bottom: 8px;
    }
    .select, .button {
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.72);
      color: var(--ink);
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
    }
    .segmented { display: inline-flex; gap: 8px; flex-wrap: wrap; }
    .segmented label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      cursor: pointer;
      font-size: 14px;
    }
    .filter-block + .filter-block { margin-top: 16px; }
    .filter-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    .filter-actions { display: inline-flex; gap: 8px; flex-wrap: wrap; }
    .pill-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    }
    .pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.65);
      font-size: 14px;
    }
    .pill input { accent-color: var(--accent); }
    .chart-shell { position: relative; height: 380px; min-height: 380px; }
    .chart-shell.tall { height: 460px; min-height: 460px; }
    canvas { display: block; width: 100% !important; height: 100% !important; }
    .chart-empty {
      display: none;
      border: 1px dashed var(--border);
      border-radius: 16px;
      padding: 28px;
      text-align: center;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.42);
    }
    .chart-empty.visible { display: block; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 600; }
    .small { color: var(--muted); font-size: 13px; }
    @media (max-width: 900px) {
      .chart-shell { height: 320px; min-height: 320px; }
      .chart-shell.tall { height: 380px; min-height: 380px; }
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

    <div class="panel controls-panel">
      <div class="controls-grid">
        <div>
          <label class="control-label" for="reportSelect">Informe para barras</label>
          <select id="reportSelect" class="select"></select>
        </div>
        <div>
          <div class="control-label">Modo de barras</div>
          <div class="segmented">
            <label><input type="radio" name="barMode" value="grouped" checked /> Agrupado</label>
            <label><input type="radio" name="barMode" value="stacked" /> Apilado</label>
          </div>
        </div>
      </div>

      <div class="filter-block">
        <div class="filter-head">
          <div class="control-label">Mediciones visibles</div>
          <div class="filter-actions">
            <button type="button" class="button" id="metricsAll">Todas</button>
            <button type="button" class="button" id="metricsNone">Ninguna</button>
          </div>
        </div>
        <div id="metricFilters" class="pill-grid"></div>
      </div>

      <div class="filter-block">
        <div class="filter-head">
          <div class="control-label">Rodeos visibles</div>
          <div class="filter-actions">
            <button type="button" class="button" id="rodeosAll">Todos</button>
            <button type="button" class="button" id="rodeosNone">Ninguno</button>
          </div>
        </div>
        <div id="rodeoFilters" class="pill-grid"></div>
      </div>
    </div>

    <div class="stack">
      <div class="panel">
        <div class="panel-head">
          <h2>Mediciones por rodeo</h2>
          <div class="panel-note">Barras horizontales para comparar las columnas seleccionadas dentro de un informe.</div>
        </div>
        <div class="chart-shell">
          <canvas id="barChart"></canvas>
        </div>
        <div id="barEmpty" class="chart-empty">Seleccioná al menos una medición y un rodeo.</div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Evolución por informe</h2>
          <div class="panel-note">Cada línea representa una combinación de rodeo y medición. Conviene filtrar pocas métricas a la vez.</div>
        </div>
        <div class="chart-shell tall">
          <canvas id="lineChart"></canvas>
        </div>
        <div id="lineEmpty" class="chart-empty">No hay series para mostrar con la selección actual.</div>
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
    const REPORTS = {{reports_json}};
    const METRICS = {{metrics_json}};
    const RODEOS = {{rodeos_json}};

    const reportSelect = document.getElementById('reportSelect');
    const metricFilters = document.getElementById('metricFilters');
    const rodeoFilters = document.getElementById('rodeoFilters');
    const barEmpty = document.getElementById('barEmpty');
    const lineEmpty = document.getElementById('lineEmpty');

    const rodeoPalette = ['#0f766e', '#b45309', '#0891b2', '#7c3aed', '#dc2626', '#16a34a', '#475569', '#ea580c'];
    const metricDash = [[], [10, 4], [3, 3], [12, 3, 3, 3], [2, 4], [16, 6]];

    const barChart = new Chart(document.getElementById('barChart'), {
      type: 'bar',
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { position: 'top' },
          tooltip: { mode: 'nearest', intersect: false }
        },
        scales: {
          x: { beginAtZero: true },
          y: { beginAtZero: true }
        }
      }
    });

    const lineChart = new Chart(document.getElementById('lineChart'), {
      type: 'line',
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: false },
        plugins: {
          legend: { position: 'top' },
          tooltip: { mode: 'nearest', intersect: false }
        },
        scales: { x: { ticks: { maxRotation: 0, autoSkip: true } } }
      }
    });

    function metricColor(metricKey) {
      const metric = METRICS.find((item) => item.key === metricKey);
      return metric ? metric.color : '#0f766e';
    }

    function reportLabel(report) {
      return report.label;
    }

    function buildCheckboxes(container, items, prefix) {
      container.innerHTML = '';
      for (const item of items) {
        const id = `${prefix}-${item.value}`;
        const label = document.createElement('label');
        label.className = 'pill';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = id;
        input.value = item.value;
        input.checked = true;

        const span = document.createElement('span');
        span.textContent = item.label;

        label.appendChild(input);
        label.appendChild(span);
        container.appendChild(label);
      }
    }

    function checkedValues(container) {
      return Array.from(container.querySelectorAll('input:checked')).map((input) => input.value);
    }

    function setAll(container, checked) {
      for (const input of container.querySelectorAll('input')) {
        input.checked = checked;
      }
      renderCharts();
    }

    function buildLineScales(selectedMetrics) {
      const scales = {
        x: { ticks: { maxRotation: 0, autoSkip: true } }
      };

      selectedMetrics.forEach((metricKey, index) => {
        const metric = METRICS.find((item) => item.key === metricKey);
        scales[`metric_${metricKey}`] = {
          type: 'linear',
          position: index % 2 === 0 ? 'left' : 'right',
          beginAtZero: false,
          grid: { drawOnChartArea: index === 0 },
          title: {
            display: true,
            text: metric ? metric.label : metricKey,
            color: metric ? metric.color : '#0f766e'
          },
          ticks: {
            color: metric ? metric.color : '#0f766e'
          }
        };
      });

      return scales;
    }

    function updateBarChart(selectedMetrics, selectedRodeos) {
      const selectedReport = REPORTS[Number(reportSelect.value || REPORTS.length - 1)];
      if (!selectedReport || !selectedMetrics.length || !selectedRodeos.length) {
        barChart.data.labels = [];
        barChart.data.datasets = [];
        barEmpty.classList.add('visible');
        barChart.update();
        return;
      }

      const labels = selectedRodeos.filter((rodeo) => selectedReport.rows[rodeo]);
      barChart.data.labels = labels;
      barChart.data.datasets = selectedMetrics.map((metricKey) => ({
        label: METRICS.find((item) => item.key === metricKey)?.label || metricKey,
        data: labels.map((rodeo) => selectedReport.rows[rodeo]?.[metricKey] ?? null),
        backgroundColor: metricColor(metricKey),
        borderRadius: 8,
        borderSkipped: false
      }));

      const mode = document.querySelector('input[name="barMode"]:checked')?.value || 'grouped';
      const isStacked = mode === 'stacked';
      barChart.options.scales.x.stacked = isStacked;
      barChart.options.scales.y.stacked = isStacked;
      barEmpty.classList.toggle('visible', !labels.length || !barChart.data.datasets.length);
      barChart.update();
    }

    function updateLineChart(selectedMetrics, selectedRodeos) {
      if (!selectedMetrics.length || !selectedRodeos.length || !REPORTS.length) {
        lineChart.data.labels = [];
        lineChart.data.datasets = [];
        lineEmpty.classList.add('visible');
        lineChart.update();
        return;
      }

      const labels = REPORTS.map((report) => reportLabel(report));
      const datasets = [];

      selectedMetrics.forEach((metricKey, metricIndex) => {
        selectedRodeos.forEach((rodeo, rodeoIndex) => {
          const values = REPORTS.map((report) => report.rows[rodeo]?.[metricKey] ?? null);
          if (values.every((value) => value === null)) {
            return;
          }

          datasets.push({
            label: `${rodeo} · ${METRICS.find((item) => item.key === metricKey)?.label || metricKey}`,
            data: values,
            yAxisID: `metric_${metricKey}`,
            borderColor: rodeoPalette[rodeoIndex % rodeoPalette.length],
            backgroundColor: rodeoPalette[rodeoIndex % rodeoPalette.length],
            borderDash: metricDash[metricIndex % metricDash.length],
            pointRadius: 3,
            pointHoverRadius: 5,
            spanGaps: true,
            tension: 0.25
          });
        });
      });

      lineChart.data.labels = labels;
      lineChart.data.datasets = datasets;
      lineChart.options.scales = buildLineScales(selectedMetrics);
      lineEmpty.classList.toggle('visible', datasets.length === 0);
      lineChart.update();
    }

    function renderCharts() {
      const selectedMetrics = checkedValues(metricFilters);
      const selectedRodeos = RODEOS.filter((rodeo) => checkedValues(rodeoFilters).includes(rodeo));
      updateBarChart(selectedMetrics, selectedRodeos);
      updateLineChart(selectedMetrics, selectedRodeos);
    }

    REPORTS.forEach((report, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = reportLabel(report);
      reportSelect.appendChild(option);
    });
    if (REPORTS.length) {
      reportSelect.value = String(REPORTS.length - 1);
    }

    buildCheckboxes(metricFilters, METRICS.map((metric) => ({ value: metric.key, label: metric.label })), 'metric');
    buildCheckboxes(rodeoFilters, RODEOS.map((rodeo) => ({ value: rodeo, label: rodeo })), 'rodeo');

    reportSelect.addEventListener('change', renderCharts);
    for (const input of document.querySelectorAll('input[name="barMode"]')) {
      input.addEventListener('change', renderCharts);
    }
    metricFilters.addEventListener('change', renderCharts);
    rodeoFilters.addEventListener('change', renderCharts);
    document.getElementById('metricsAll').addEventListener('click', () => setAll(metricFilters, true));
    document.getElementById('metricsNone').addEventListener('click', () => setAll(metricFilters, false));
    document.getElementById('rodeosAll').addEventListener('click', () => setAll(rodeoFilters, true));
    document.getElementById('rodeosNone').addEventListener('click', () => setAll(rodeoFilters, false));

    renderCharts();
  </script>
</body>
</html>
"""


def build_dashboard(reports: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_rows = []
    owners = set()
    chart_reports = []
    rodeos: list[str] = []
    seen_rodeos: set[str] = set()
    available_metric_keys: set[str] = set()

    sorted_reports = sorted(
        reports,
        key=lambda item: (item.get("fecha_proceso") or item.get("fecha_ingreso") or "", item.get("protocolo") or 0),
    )

    for report in sorted_reports:
        rows = report.get("rows", [])
        owners.add(report.get("propietario") or "")
        mg_avg = _average_metric(rows, "mg")
        rcs_avg = _average_metric(rows, "rcs")
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

        chart_row_map: dict[str, dict[str, float | None]] = {}
        for row in rows:
            rodeo = row.get("identificacion") or row.get("rodeo") or "-"
            if rodeo not in seen_rodeos:
                seen_rodeos.add(rodeo)
                rodeos.append(rodeo)

            chart_row_map[rodeo] = {metric["key"]: row.get(metric["key"]) for metric in METRIC_SPECS}
            for metric in METRIC_SPECS:
                if row.get(metric["key"]) is not None:
                    available_metric_keys.add(metric["key"])

        chart_reports.append(
            {
                "label": _report_label(report),
                "protocolo": report.get("protocolo") or report.get("nro_informe") or "-",
                "fecha": report.get("fecha_proceso") or report.get("fecha_ingreso") or "-",
                "rows": chart_row_map,
            }
        )

    recent_rows_html = "\n".join(
        f"<tr><td>{escape(str(item['protocolo']))}</td><td>{escape(str(item['fecha']))}</td><td>{escape(str(item['propietario']))}</td><td>{item['filas']}</td><td>{item['mg_avg'] if item['mg_avg'] is not None else ''}</td><td>{item['rcs_avg'] if item['rcs_avg'] is not None else ''}</td></tr>"
        for item in report_rows[-12:][::-1]
    )

    available_metrics = [metric for metric in METRIC_SPECS if metric["key"] in available_metric_keys]

    html = HTML_TEMPLATE
    html = html.replace("{{total_reports}}", str(len(sorted_reports)))
    html = html.replace("{{total_rows}}", str(sum(len(r.get('rows', [])) for r in sorted_reports)))
    html = html.replace("{{last_report}}", str(report_rows[-1]["protocolo"]) if report_rows else "-")
    html = html.replace("{{owners}}", str(len({o for o in owners if o})))
    html = html.replace("{{recent_rows}}", recent_rows_html)
    html = html.replace("{{reports_json}}", json.dumps(chart_reports, ensure_ascii=False))
    html = html.replace("{{metrics_json}}", json.dumps(available_metrics, ensure_ascii=False))
    html = html.replace("{{rodeos_json}}", json.dumps(rodeos, ensure_ascii=False))

    output_path.write_text(html, encoding="utf-8")
    return output_path


def _average_metric(rows: list[dict], key: str) -> float | None:
    values = [row.get(key) for row in rows if row.get(key) is not None]
    return round(sum(values) / len(values), 3) if values else None


def _report_label(report: dict) -> str:
    date_label = report.get("fecha_proceso") or report.get("fecha_ingreso") or "Sin fecha"
    protocol_label = report.get("protocolo") or report.get("nro_informe") or "sin informe"
    return f"{date_label} · Informe {protocol_label}"
