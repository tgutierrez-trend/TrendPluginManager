from fastapi import FastAPI

from .database import Base, engine
from .api.plugins import router
from .api.tasks import router as tasks_router


Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title="Plugin Platform"
)


app.include_router(router)
app.include_router(tasks_router)