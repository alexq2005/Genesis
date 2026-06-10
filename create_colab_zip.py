"""
Crea genesis_code.zip para subir a Google Colab.
Incluye solo el codigo (~5MB), excluye modelos (~13GB).

Ejecutar: python create_colab_zip.py
Resultado: genesis_code.zip en el mismo directorio
"""
import zipfile
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Directorios y archivos a excluir
EXCLUDE_DIRS = {
    "models", "model_cache", "__pycache__", ".git",
    "venv", ".venv", "env", "node_modules",
    "tools",  # scripts de build, no necesarios en runtime
}

EXCLUDE_EXTENSIONS = {
    ".gguf", ".bin", ".safetensors", ".pt", ".pth",
    ".h5", ".onnx", ".tflite", ".pkl",
    ".zip", ".tar", ".gz", ".7z",
    ".pyc", ".pyo",
}

EXCLUDE_FILES = {
    "create_colab_zip.py",  # este mismo script
    "GENESIS_Colab.ipynb",  # el notebook se sube aparte
}

def should_include(filepath, root_dir):
    """Decide si un archivo debe incluirse en el zip."""
    rel_path = os.path.relpath(filepath, root_dir)
    parts = rel_path.replace("\\", "/").split("/")

    # Excluir directorios
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False

    # Excluir por nombre
    filename = os.path.basename(filepath)
    if filename in EXCLUDE_FILES:
        return False

    # Excluir por extension
    _, ext = os.path.splitext(filename)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return False

    return True


def create_zip():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(root_dir, "genesis_code.zip")

    file_count = 0
    total_size = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Filtrar directorios para no recorrerlos
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    if should_include(filepath, root_dir):
                        arcname = os.path.relpath(filepath, root_dir)
                        zf.write(filepath, arcname)
                        size = os.path.getsize(filepath)
                        total_size += size
                        file_count += 1
                except (ValueError, OSError):
                    # Skip special files (NUL device, symlinks, etc.)
                    continue

    zip_size = os.path.getsize(zip_path)

    print("=" * 50)
    print("  genesis_code.zip creado!")
    print(f"  Archivos: {file_count}")
    print(f"  Tamano original: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Tamano zip: {zip_size / 1024 / 1024:.1f} MB")
    print(f"  Ubicacion: {zip_path}")
    print("=" * 50)
    print()
    print("Siguiente paso:")
    print("  1. Abre GENESIS_Colab.ipynb en Google Colab")
    print("  2. En la celda 2, subi este genesis_code.zip")


if __name__ == "__main__":
    create_zip()
