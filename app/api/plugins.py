from pathlib import Path
import shutil
import zipfile
import json

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException
)

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Plugin
from ..schemas import PluginResponse


router = APIRouter(
    prefix="/plugins",
    tags=["plugins"]
)


PLUGINS_DIR = Path("plugins_storage")


@router.post(
    "/",
    response_model=PluginResponse
)
def create_plugin(
    name: str = Form(...),
    description: str = Form(...),
    plugin_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # 0. Validar duplicados en la Base de Datos
    # --------------------------------------------------
    existing_plugin = db.query(Plugin).filter(Plugin.name == name).first()
    if existing_plugin:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un plugin registrado con el nombre '{name}'."
        )


    # --------------------------------------------------
    # 1. Validar que sea un ZIP
    # --------------------------------------------------

    if not plugin_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un ZIP"
        )


    # --------------------------------------------------
    # 2. Guardar temporalmente el ZIP
    # --------------------------------------------------

    temp_dir = Path("temp_plugins")
    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_zip = temp_dir / plugin_file.filename

    with open(temp_zip, "wb") as buffer:

        shutil.copyfileobj(
            plugin_file.file,
            buffer
        )


    # --------------------------------------------------
    # 3. Validar contenido del ZIP
    # --------------------------------------------------

    try:

        with zipfile.ZipFile(temp_zip, "r") as zip_file:

            files = zip_file.namelist()

            required_files = {
                "manifest.json",
                "plugin.py",
                "requirements.txt"
            }

            missing_files = (
                required_files - set(files)
            )

            if missing_files:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "El plugin no es válido. "
                        f"Faltan archivos: "
                        f"{', '.join(missing_files)}"
                    )
                )


            # --------------------------------------------------
            # 4. Leer manifest.json
            # --------------------------------------------------

            try:

                manifest_content = zip_file.read(
                    "manifest.json"
                )

                manifest = json.loads(
                    manifest_content
                )

            except json.JSONDecodeError:

                raise HTTPException(
                    status_code=400,
                    detail="manifest.json no contiene JSON válido"
                )


    finally:

        # Eliminar ZIP temporal
        if temp_zip.exists():
            temp_zip.unlink()


    # --------------------------------------------------
    # 5. Validar manifest
    # --------------------------------------------------

    required_manifest_fields = {
        "name",
        "version",
        "description",
        "entrypoint"
    }

    missing_fields = (
        required_manifest_fields
        - set(manifest.keys())
    )

    if missing_fields:

        raise HTTPException(
            status_code=400,
            detail=(
                "Faltan campos en manifest.json: "
                f"{', '.join(missing_fields)}"
            )
        )


    # --------------------------------------------------
    # 6. Crear registro en DB
    # --------------------------------------------------

    plugin = Plugin(
        name=name,
        description=description,
        path="",
        manifest=manifest
    )

    db.add(plugin)
    db.commit()
    db.refresh(plugin)


    # --------------------------------------------------
    # 7. Crear directorio del plugin
    # --------------------------------------------------

    plugin_dir = (
        PLUGINS_DIR /
        str(plugin.id)
    )

    plugin_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------------------
    # 8. Guardar ZIP
    # --------------------------------------------------

    zip_path = (
        plugin_dir /
        plugin_file.filename
    )

    plugin_file.file.seek(0)

    with open(zip_path, "wb") as buffer:

        shutil.copyfileobj(
            plugin_file.file,
            buffer
        )


    # --------------------------------------------------
    # 9. Guardar path en DB
    # --------------------------------------------------

    plugin.path = str(zip_path)

    db.commit()
    db.refresh(plugin)


    return plugin


@router.get(
    "/",
    response_model=list[PluginResponse]
)
def get_plugins(
    db: Session = Depends(get_db)
):

    plugins = db.query(Plugin).all()

    return plugins