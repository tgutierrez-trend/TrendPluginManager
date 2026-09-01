from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form
)

from fastapi.responses import FileResponse, StreamingResponse
import json
import shutil

from pathlib import Path

import io
import zipfile

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Plugin, Task
from ..schemas import (
    TaskResponse
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)


EXECUTION_DIR = Path("execution")

def validate_parameters(
    parameters: dict,
    manifest: dict
):

    parameter_definitions = manifest.get(
        "parameters",
        {}
    )

    # Copiamos los parámetros recibidos
    validated_parameters = parameters.copy()


    # --------------------------------
    # Parámetros definidos en manifest
    # --------------------------------

    for name, definition in parameter_definitions.items():

        required = definition.get(
            "required",
            False
        )

        has_default = "default" in definition


        # --------------------------------
        # Parámetro no enviado
        # --------------------------------

        if name not in validated_parameters:

            # Tiene valor por defecto
            if has_default:

                validated_parameters[name] = (
                    definition["default"]
                )

            # Es obligatorio
            elif required:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Falta el parámetro obligatorio: "
                        f"{name}"
                    )
                )


    # --------------------------------
    # Verificar parámetros desconocidos
    # --------------------------------

    for name in validated_parameters:

        if name not in parameter_definitions:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Parámetro no reconocido: "
                    f"{name}"
                )
            )


    # --------------------------------
    # Verificar tipos
    # --------------------------------

    for name, value in validated_parameters.items():

        definition = parameter_definitions[name]

        expected_type = definition.get(
            "type"
        )


        if expected_type == "string":

            if not isinstance(value, str):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El parámetro '{name}' "
                        "debe ser de tipo string"
                    )
                )


        elif expected_type == "integer":

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El parámetro '{name}' "
                        "debe ser de tipo integer"
                    )
                )


        elif expected_type == "float":

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El parámetro '{name}' "
                        "debe ser de tipo float"
                    )
                )


        elif expected_type == "bool":

            if not isinstance(value, bool):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El parámetro '{name}' "
                        "debe ser de tipo bool"
                    )
                )

        elif expected_type == "select":
            options = definition.get(
                "options",
                []
            )

            if value not in options:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El valor '{value}' no es válido "
                        f"para el parámetro '{name}'. "
                        f"Opciones permitidas: {options}"
                    )
                )

        elif expected_type is not None:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Tipo de parámetro no soportado: "
                    f"{expected_type}"
                )
            )


    return validated_parameters

@router.post(
    "/",
    response_model=TaskResponse
)
def create_task(
    plugin_id: int = Form(...),
    parameters: str = Form("{}"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):

    # --------------------------------
    # Buscar el plugin
    # --------------------------------

    plugin = db.get(
        Plugin,
        plugin_id
    )

    if plugin is None:

        raise HTTPException(
            status_code=404,
            detail="Plugin no encontrado"
        )


    # --------------------------------
    # Verificar que esté habilitado
    # --------------------------------

    if not plugin.enabled:

        raise HTTPException(
            status_code=400,
            detail="El plugin está deshabilitado"
        )


    # --------------------------------
    # Convertir parameters
    # --------------------------------

    try:

        parameters_dict = json.loads(
            parameters
        )

    except json.JSONDecodeError:


        raise HTTPException(
            status_code=400,
            detail="parameters debe ser un JSON válido"
        )

    parameters_dict = validate_parameters(
        parameters_dict,
        plugin.manifest
    )

    # --------------------------------
    # Crear tarea
    # --------------------------------

    task = Task(
        plugin_id=plugin_id,
        parameters=parameters_dict,
        status="queued"
    )

    db.add(task)

    db.commit()

    db.refresh(task)


    # --------------------------------
    # Crear carpeta de ejecución
    # --------------------------------

    task_dir = (
        EXECUTION_DIR /
        f"task_{task.id}"
    )

    input_dir = (
        task_dir /
        "input"
    )

    input_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------
    # Guardar archivos
    # --------------------------------

    uploaded_files = []

    for file in files:

        file_path = (
            input_dir /
            file.filename
        )

        with file_path.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        uploaded_files.append(
            file.filename
        )


    return task


@router.get(
    "/",
    response_model=list[TaskResponse]
)
def get_tasks(
    db: Session = Depends(get_db)
):

    tasks = db.query(Task).all()

    return tasks

@router.get("/{task_id}/download")
def download_task_output(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if task.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"La tarea está en estado '{task.status}', no hay salidas disponibles."
        )

    output_dir = EXECUTION_DIR / f"task_{task_id}" / "output"

    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="El directorio de salida no existe")

    # Listar los archivos generados dentro de /output
    output_files = [f for f in output_dir.iterdir() if f.is_file()]

    if not output_files:
        raise HTTPException(status_code=404, detail="La tarea no generó archivos de salida")

    # CASO 1: Hay un único archivo -> Se descarga directamente con su nombre/extensión original
    if len(output_files) == 1:
        single_file = output_files[0]
        return FileResponse(
            path=single_file,
            filename=single_file.name,
            media_type="application/octet-stream"
        )

    # CASO 2: Hay múltiples archivos -> Se comprimen en un .zip en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in output_files:
            zip_file.write(file, arcname=file.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=resultado_tarea_{task_id}.zip"
        }
    )