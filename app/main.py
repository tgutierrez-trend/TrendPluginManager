from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .api.plugins import router
from .api.tasks import router as tasks_router
from .api.views import router as views_router  # Router para las vistas HTML

Base.metadata.create_all(
    bind=engine
)

app = FastAPI(
    title="Plugin Platform"
)

# Servir archivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir tus routers API existentes
app.include_router(router)
app.include_router(tasks_router)

# Incluir el router para la interfaz web (Jinja2)
app.include_router(views_router)