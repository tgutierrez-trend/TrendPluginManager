import time
import zipfile
import importlib.util
import shutil

from pathlib import Path

from app.database import SessionLocal
from app.models import Task, Plugin


EXECUTION_DIR = Path("execution")
TEMP_DIR = Path("temp")


def get_next_task():

    db = SessionLocal()

    try:

        task = (
            db.query(Task)
            .filter(Task.status == "queued")
            .first()
        )

        if task is None:
            return None

        task.status = "running"

        db.commit()

        db.refresh(task)

        return task

    finally:

        db.close()


def get_plugin(plugin_id):

    db = SessionLocal()

    try:

        plugin = db.get(
            Plugin,
            plugin_id
        )

        return plugin

    finally:

        db.close()


def execute_plugin(task, plugin):

    # ----------------------------------------
    # Directorio de ejecución
    # ----------------------------------------

    task_dir = (
        EXECUTION_DIR /
        f"task_{task.id}"
    )

    input_dir = task_dir / "input"
    output_dir = task_dir / "output"

    input_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # ----------------------------------------
    # Directorio temporal del plugin
    # ----------------------------------------

    temp_plugin_dir = (
        TEMP_DIR /
        f"task_{task.id}"
    )

    temp_plugin_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    try:

        # ----------------------------------------
        # Extraer ZIP temporalmente
        # ----------------------------------------

        with zipfile.ZipFile(
            plugin.path,
            "r"
        ) as zip_file:

            zip_file.extractall(
                temp_plugin_dir
            )


        # ----------------------------------------
        # Obtener entrypoint
        # ----------------------------------------

        entrypoint = plugin.manifest[
            "entrypoint"
        ]

        module_name, function_name = (
            entrypoint.split(":")
        )


        # ----------------------------------------
        # Localizar módulo
        # ----------------------------------------

        module_path = (
            temp_plugin_dir /
            f"{module_name}.py"
        )


        # ----------------------------------------
        # Cargar módulo dinámicamente
        # ----------------------------------------

        spec = (
            importlib.util
            .spec_from_file_location(
                module_name,
                module_path
            )
        )

        module = (
            importlib.util
            .module_from_spec(spec)
        )

        spec.loader.exec_module(
            module
        )


        # ----------------------------------------
        # Obtener función
        # ----------------------------------------

        function = getattr(
            module,
            function_name
        )


        # ----------------------------------------
        # Ejecutar plugin
        # ----------------------------------------

        function(
            task.parameters,
            input_dir,
            output_dir
        )


    finally:

        # ----------------------------------------
        # Eliminar archivos temporales
        # ----------------------------------------

        if temp_plugin_dir.exists():

            shutil.rmtree(
                temp_plugin_dir
            )


def main():

    print("Worker iniciado")

    while True:

        task = get_next_task()

        if task is None:

            time.sleep(2)

            continue

        print(
            f"Tarea encontrada: "
            f"{task.id}"
        )

        plugin = get_plugin(
            task.plugin_id
        )

        if plugin is None:

            print(
                f"Plugin {task.plugin_id} "
                f"no encontrado"
            )

            continue

        print(
            f"Plugin encontrado: "
            f"{plugin.name}"
        )

        try:

            execute_plugin(
                task,
                plugin
            )

            # Si llegamos acá,
            # el plugin terminó correctamente.

            db = SessionLocal()

            try:

                task_db = db.get(
                    Task,
                    task.id
                )

                task_db.status = "completed"
                task_db.error = None

                db.commit()

            finally:

                db.close()


        except Exception as e:

            print(
                f"Error ejecutando tarea "
                f"{task.id}: {e}"
            )

            db = SessionLocal()

            try:

                task_db = db.get(
                    Task,
                    task.id
                )

                task_db.status = "failed"
                task_db.error = str(e)

                db.commit()

            finally:

                db.close()


if __name__ == "__main__":
    main()