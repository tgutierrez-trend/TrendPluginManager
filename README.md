# 🚀 Trend - WEB APP Gestora de Plugins de Automatismos

Un sistema extensible de procesamiento de tareas asíncronas basado en **FastAPI**, **SQLAlchemy** y un sistema de **Plugins dinámicos**. 

El proyecto permite ejecutar tareas aisladas a través de un worker ligero que procesa una cola basada en base de datos.

---

## 🏗️ Arquitectura del Sistema

- **FastAPI** → API principal.
- **SQLite + SQLAlchemy** → catálogo persistente de plugins y tareas.
- **Worker** → procesa tareas.
- **Cola simple basada en DB**.
- **Plugins cargados dinámicamente desde archivos `.py`**.
- Cada plugin tendrá:
    - `manifest.json`
    - `plugin.py`
    - `requirements.txt`
- Cada ejecución tendrá su propio `input/` y `output/`.
- El `manifest.json` define los parámetros que necesita el plugin.
- La API puede consultar esos parámetros y generar dinámicamente el formulario del frontend.
- El worker obtiene `plugin_id`, busca el plugin, carga su `plugin.py` dinámicamente y ejecuta `run()`.
