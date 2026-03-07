# ============================================================
# GENESIS — Makefile
# ============================================================
# Uso:
#   make setup     — Crea venv e instala dependencias
#   make run       — Ejecuta Genesis en terminal
#   make web       — Ejecuta la Web UI (http://localhost:5000)
#   make test      — Corre todos los tests
#   make test-v14  — Corre solo tests de v1.4
#   make clean     — Limpia __pycache__ y archivos temporales
# ============================================================

PYTHON = python
VENV = venv
PIP = $(VENV)/Scripts/pip
PYTEST = $(VENV)/Scripts/pytest
PYTHON_VENV = $(VENV)/Scripts/python

.PHONY: setup run web test test-v11 test-v12 test-v13 test-v14 clean help

help:
	@echo "=== GENESIS Makefile ==="
	@echo "  make setup     - Crea venv e instala dependencias"
	@echo "  make run       - Ejecuta Genesis en terminal"
	@echo "  make web       - Ejecuta la Web UI"
	@echo "  make test      - Corre todos los tests"
	@echo "  make test-v14  - Corre solo tests de v1.4"
	@echo "  make clean     - Limpia __pycache__"

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Entorno listo. Activa con: $(VENV)\Scripts\activate"

run:
	$(PYTHON_VENV) genesis.py

web:
	$(PYTHON_VENV) web_ui.py

test:
	$(PYTEST) tests/ -v --tb=short

test-v11:
	$(PYTEST) tests/test_all_improvements.py -v --tb=short

test-v12:
	$(PYTEST) tests/test_v1_2.py -v --tb=short

test-v13:
	$(PYTEST) tests/test_v1_3.py -v --tb=short

test-v14:
	$(PYTEST) tests/test_v1_4.py -v --tb=short

clean:
	@echo "Limpiando __pycache__..."
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	@echo "✅ Limpio"
