# BuenaLeche

Pipeline para procesar informes LABVIMA subidos a una carpeta de Google Drive, generar un dataset histórico y publicar un dashboard HTML estático.

## Flujo

1. Un workflow de GitHub Actions se ejecuta manualmente o por schedule.
2. Lee la carpeta de Drive configurada en `DRIVE_FOLDER_URL`.
3. Descarga solo los PDFs nuevos o modificados.
4. Parsea cada informe y recompone `data/dataset.csv` y `data/reports.json`.
5. Genera `dist/index.html` con métricas y gráficos básicos.

## Ver el dashboard

Una vez activado GitHub Pages en el repositorio, el HTML publicado quedará accesible en la URL de Pages del proyecto. El workflow ya genera `dist/index.html` y lo despliega automáticamente.

Si querés probarlo en local, abrí `dist/index.html` después de correr el script de actualización.

## Configuración

Variables y secretos requeridos:

- `DRIVE_FOLDER_URL`: URL de la carpeta compartida de Google Drive.
- `GOOGLE_CREDENTIALS_JSON`: contenido JSON de una cuenta de servicio con acceso a la carpeta.

Además, en GitHub tenés que dejar Pages con source = GitHub Actions en la configuración del repo.

## Desarrollo local

Instalá dependencias y ejecutá:

```bash
python scripts/update_from_drive.py --folder-url "<url de la carpeta>" --credentials service_account.json --output-dir dist
```

El parser está en `src/buenaleche/parser.py` y el dashboard en `src/buenaleche/dashboard.py`.