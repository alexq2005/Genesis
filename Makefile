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

.PHONY: setup run web test test-v11 test-v12 test-v13 test-v14 test-v15 test-v16 test-v17 test-v18 test-v19 test-v20 test-v21 test-v21e test-v22 test-v23 test-v24 clean help

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
	$(PYTHON_VENV) tests/test_all_improvements.py
	$(PYTHON_VENV) tests/test_v1_2.py
	$(PYTHON_VENV) tests/test_v1_3.py
	$(PYTHON_VENV) tests/test_v1_4.py
	$(PYTHON_VENV) tests/test_v1_5.py
	$(PYTHON_VENV) tests/test_v1_6.py
	$(PYTHON_VENV) tests/test_v1_7.py
	$(PYTHON_VENV) tests/test_v1_8.py
	$(PYTHON_VENV) tests/test_v1_9.py
	$(PYTHON_VENV) tests/test_v2_0.py
	$(PYTHON_VENV) tests/test_v2_1.py
	$(PYTHON_VENV) tests/test_v2_1_evolve.py
	$(PYTHON_VENV) tests/test_v2_2.py
	$(PYTHON_VENV) tests/test_v2_3.py
	$(PYTHON_VENV) tests/test_v2_4.py

test-v11:
	$(PYTHON_VENV) tests/test_all_improvements.py

test-v12:
	$(PYTHON_VENV) tests/test_v1_2.py

test-v13:
	$(PYTHON_VENV) tests/test_v1_3.py

test-v14:
	$(PYTHON_VENV) tests/test_v1_4.py

test-v15:
	$(PYTHON_VENV) tests/test_v1_5.py

test-v16:
	$(PYTHON_VENV) tests/test_v1_6.py

test-v17:
	$(PYTHON_VENV) tests/test_v1_7.py

test-v18:
	$(PYTHON_VENV) tests/test_v1_8.py

test-v19:
	$(PYTHON_VENV) tests/test_v1_9.py

test-v20:
	$(PYTHON_VENV) tests/test_v2_0.py

test-v21:
	$(PYTHON_VENV) tests/test_v2_1.py

test-v21e:
	$(PYTHON_VENV) tests/test_v2_1_evolve.py

test-v22:
	$(PYTHON_VENV) tests/test_v2_2.py

test-v23:
	$(PYTHON_VENV) tests/test_v2_3.py

test-v24:
	$(PYTHON_VENV) tests/test_v2_4.py

clean:
	@echo "Limpiando __pycache__..."
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	@echo "✅ Limpio"
