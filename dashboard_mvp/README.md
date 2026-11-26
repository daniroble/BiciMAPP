# BiciMAPP dashboard con mapa interactivo

Reemplaza la carpeta `dashboard_mvp` de la raíz del repositorio por esta carpeta.

Instalación/actualización de dependencias en PowerShell (desde la raíz del repo y con `.venv` activado):
`pip install -r .\dashboard_mvp\requirements.txt`

Ejecución:
`streamlit run .\dashboard_mvp\app.py`

Incluye una página **Mapa de movilidad** que busca CSV con coordenadas reales en `data/processed/` y `analysis/`, preferentemente archivos validados/CRTM. Las estaciones se enlazan con métricas por nombre normalizado exacto. No inventa coordenadas. El mapa de corredores está pendiente como siguiente capa.
