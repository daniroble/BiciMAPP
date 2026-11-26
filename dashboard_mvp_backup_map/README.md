# BiciMAPP dashboard rediseñado (MVP)

## Instalación en Windows
1. Coloca la carpeta `dashboard_mvp` dentro de la raíz del repositorio BiciMAPP.
2. Desde PowerShell, en la raíz del repositorio, activa el entorno virtual:
   `.\.venv\Scripts\Activate.ps1`
3. Instala dependencias si es necesario:
   `pip install -r .\dashboard_mvp\requirements.txt`
4. Arranca:
   `streamlit run .\dashboard_mvp\app.py`

## Nota
El dashboard busca CSV en `data/processed/` y `analysis/` desde la raíz del repositorio.
No carga el archivo bruto de viajes de cientos de MB.
Las gráficas solo se muestran cuando reconoce columnas. Los análisis y cifras de corredores
son exploratorios y deben interpretarse con sus limitaciones.
