# BiciMAPP Dashboard MVP

Streamlit MVP inicial. Copia la carpeta `dashboard_mvp` a la raíz de tu repo.

## Ejecutar en Windows / PowerShell (desde la raíz del repositorio)

```powershell
python -m pip install -r dashboard_mvp/requirements.txt
python -m streamlit run dashboard_mvp/app.py
```

La app busca CSVs recursivamente en `data/processed/` y `analysis/`, usando nombres de archivo y detección flexible de columnas. Si no reconoce un dataset, muestra una muestra para facilitar ajustes.

## Secciones
- Resumen
- Demanda
- Estaciones
- Corredores
- Datos y metodología

**Importante:** las afirmaciones de corredores son exploratorias. El balance de flujo no representa inventario ni disponibilidad de bicicletas.
