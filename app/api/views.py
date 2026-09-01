from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Plugin, Task

router = APIRouter(tags=["UI Views"])
templates = Jinja2Templates(directory="templates")

@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    plugins_db = db.query(Plugin).all()
    
    plugins = []
    for p in plugins_db:
        manifest = p.manifest if isinstance(p.manifest, dict) else {}
        plugins.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "version": manifest.get("version", "1.0.0"),
            "manifest": manifest
        })

    return templates.TemplateResponse(
        request=request, 
        name="plugins.html", 
        context={"plugins": plugins}
    )


@router.get("/tasks-view")
def tasks_view(request: Request, db: Session = Depends(get_db)):
    plugins_db = db.query(Plugin).all()
    tasks_db = db.query(Task).all()

    plugins = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "manifest": p.manifest if isinstance(p.manifest, dict) else {}
        }
        for p in plugins_db
    ]

    tasks = [
        {
            "id": t.id,
            "plugin_id": t.plugin_id,
            "status": getattr(t, "status", "PENDING"),
            "parameters": getattr(t, "parameters", {}),
            "result": getattr(t, "result", None),
            "created_at": getattr(t, "created_at", None)
        }
        for t in tasks_db
    ]

    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={
            "plugins": plugins,
            "tasks": tasks
        }
    )