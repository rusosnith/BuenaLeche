# BuenaLeche

Pipeline para procesar informes LABVIMA en formato TXT, generar un dataset histórico y publicar un dashboard HTML estático.

## Flujo

1. Un workflow de GitHub Actions se ejecuta manualmente o por schedule.
2. Busca archivos `P*.txt` en `data/`.
3. Parsea solo los TXT que todavía no estén incorporados en `data/dataset.csv`.
4. Actualiza `data/dataset.csv` y `data/reports.json`.
5. Genera `dist/index.html` con métricas y gráficos básicos.

## Ver el dashboard

Una vez activado GitHub Pages en el repositorio con source = `GitHub Actions`, el workflow publica el dashboard automáticamente en la URL del sitio.

Si querés probarlo en local, abrí `dist/index.html` después de correr el script de actualización.

## Configuración

En GitHub Pages dejá source = `GitHub Actions`.

## Desarrollo local

Instalá dependencias y ejecutá:

```bash
python scripts/update_dataset_from_txts.py
python scripts/build_dashboard_from_reports.py --reports-json data/reports.json --output dist/index.html
```

Para integrar incrementalmente los TXT que ya estén en `data/` (sin reprocesar los ya incorporados en `dataset.csv`):

```bash
python scripts/update_dataset_from_txts.py
```

Modo prueba (no escribe cambios):

```bash
python scripts/update_dataset_from_txts.py --dry-run
```

El parser está en `src/buenaleche/parser.py` y el dashboard en `src/buenaleche/dashboard.py`.