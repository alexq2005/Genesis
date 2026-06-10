"""
GENESIS Project Scaffolder — Generador de estructuras de proyectos.
Crea proyectos completos con boilerplate: Python, Node, HTML, Flask, FastAPI, React.
"""
import os
import json
import threading
from datetime import datetime
from typing import Optional


class ProjectScaffolder:
    """Genera estructuras de proyectos con templates predefinidos."""

    TEMPLATES = {
        "python": {
            "description": "Proyecto Python básico con venv y estructura estándar",
            "files": {
                "main.py": '"""\n{name} — Punto de entrada principal.\n"""\n\n\ndef main():\n    print("{name} está funcionando!")\n\n\nif __name__ == "__main__":\n    main()\n',
                "requirements.txt": "# Dependencias del proyecto\n",
                "README.md": "# {name}\n\n{description}\n\n## Instalación\n\n```bash\npython -m venv venv\nvenv\\Scripts\\activate  # Windows\npip install -r requirements.txt\n```\n\n## Uso\n\n```bash\npython main.py\n```\n",
                ".gitignore": "venv/\n__pycache__/\n*.pyc\n.env\n*.egg-info/\ndist/\nbuild/\n.idea/\n.vscode/\n",
                "src/__init__.py": "",
                "tests/__init__.py": "",
                "tests/test_main.py": 'import unittest\n\n\nclass TestMain(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
            }
        },
        "flask": {
            "description": "Aplicación web Flask con estructura MVC",
            "files": {
                "app.py": 'from flask import Flask, render_template, jsonify\n\napp = Flask(__name__)\n\n\n@app.route("/")\ndef index():\n    return render_template("index.html", title="{name}")\n\n\n@app.route("/api/status")\ndef api_status():\n    return jsonify({{"status": "ok", "app": "{name}"}})\n\n\nif __name__ == "__main__":\n    app.run(debug=True)\n',
                "requirements.txt": "flask>=3.0\n",
                "templates/index.html": '<!DOCTYPE html>\n<html>\n<head>\n    <title>{{{{ title }}}}</title>\n    <style>\n        body {{ font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}\n    </style>\n</head>\n<body>\n    <h1>{name}</h1>\n    <p>{description}</p>\n</body>\n</html>\n',
                "static/style.css": "/* Estilos de {name} */\nbody {{ font-family: sans-serif; }}\n",
                ".gitignore": "venv/\n__pycache__/\n*.pyc\n.env\ninstance/\n",
                "README.md": "# {name}\n\n{description}\n\n## Setup\n\n```bash\npip install -r requirements.txt\npython app.py\n```\n",
            }
        },
        "fastapi": {
            "description": "API REST con FastAPI y estructura moderna",
            "files": {
                "main.py": 'from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI(title="{name}", description="{description}")\n\n\nclass HealthResponse(BaseModel):\n    status: str\n    app: str\n\n\n@app.get("/")\nasync def root():\n    return {{"message": "Bienvenido a {name}"}}\n\n\n@app.get("/health", response_model=HealthResponse)\nasync def health():\n    return HealthResponse(status="ok", app="{name}")\n',
                "requirements.txt": "fastapi>=0.100\nuvicorn[standard]>=0.20\npydantic>=2.0\n",
                "routers/__init__.py": "",
                "models/__init__.py": "",
                "schemas/__init__.py": "",
                ".gitignore": "venv/\n__pycache__/\n*.pyc\n.env\n",
                "README.md": "# {name}\n\n{description}\n\n## Setup\n\n```bash\npip install -r requirements.txt\nuvicorn main:app --reload\n```\n\nDocs: http://localhost:8000/docs\n",
            }
        },
        "node": {
            "description": "Proyecto Node.js con Express",
            "files": {
                "index.js": 'const express = require("express");\nconst app = express();\nconst PORT = process.env.PORT || 3000;\n\napp.use(express.json());\n\napp.get("/", (req, res) => {{\n    res.json({{ message: "Bienvenido a {name}" }});\n}});\n\napp.listen(PORT, () => {{\n    console.log(`{name} corriendo en http://localhost:${{PORT}}`);\n}});\n',
                "package.json": '{{\n  "name": "{name_slug}",\n  "version": "1.0.0",\n  "description": "{description}",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "dev": "nodemon index.js"\n  }},\n  "dependencies": {{\n    "express": "^4.18.0"\n  }},\n  "devDependencies": {{\n    "nodemon": "^3.0.0"\n  }}\n}}\n',
                ".gitignore": "node_modules/\n.env\ndist/\n",
                "README.md": "# {name}\n\n{description}\n\n## Setup\n\n```bash\nnpm install\nnpm start\n```\n",
            }
        },
        "html": {
            "description": "Página web HTML/CSS/JS estática",
            "files": {
                "index.html": '<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{name}</title>\n    <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n    <header>\n        <h1>{name}</h1>\n    </header>\n    <main>\n        <p>{description}</p>\n    </main>\n    <script src="js/main.js"></script>\n</body>\n</html>\n',
                "css/style.css": "/* {name} — Estilos */\n* {{ margin: 0; padding: 0; box-sizing: border-box; }}\nbody {{\n    font-family: system-ui, sans-serif;\n    max-width: 1200px;\n    margin: 0 auto;\n    padding: 2rem;\n    background: #f5f5f5;\n    color: #333;\n}}\nh1 {{ color: #2c3e50; margin-bottom: 1rem; }}\n",
                "js/main.js": '// {name} — JavaScript\nconsole.log("{name} cargado");\n',
                "img/.gitkeep": "",
            }
        },
        "react": {
            "description": "Aplicación React con Vite",
            "files": {
                "index.html": '<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n    <title>{name}</title>\n</head>\n<body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.jsx"></script>\n</body>\n</html>\n',
                "src/main.jsx": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\n\nReactDOM.createRoot(document.getElementById('root')).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n",
                "src/App.jsx": "function App() {{\n  return (\n    <div className=\"app\">\n      <h1>{name}</h1>\n      <p>{description}</p>\n    </div>\n  );\n}}\n\nexport default App;\n",
                "src/index.css": "body {{\n  font-family: system-ui, sans-serif;\n  margin: 0;\n  padding: 2rem;\n}}\n.app {{ max-width: 800px; margin: 0 auto; }}\n",
                "package.json": '{{\n  "name": "{name_slug}",\n  "version": "1.0.0",\n  "scripts": {{\n    "dev": "vite",\n    "build": "vite build"\n  }},\n  "dependencies": {{\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  }},\n  "devDependencies": {{\n    "@vitejs/plugin-react": "^4.0.0",\n    "vite": "^5.0.0"\n  }}\n}}\n',
                "vite.config.js": "import {{ defineConfig }} from 'vite';\nimport react from '@vitejs/plugin-react';\n\nexport default defineConfig({{\n  plugins: [react()],\n}});\n",
                ".gitignore": "node_modules/\ndist/\n.env\n",
                "README.md": "# {name}\n\n{description}\n\n## Setup\n\n```bash\nnpm install\nnpm run dev\n```\n",
            }
        },
    }

    def __init__(self):
        self._history: list[dict] = []
        self._lock = threading.RLock()

    # ── Generar proyecto ─────────────────────────────
    def create(self, name: str, template: str = "python",
               path: str = "", description: str = "") -> str:
        """Crea un proyecto completo con la estructura del template."""
        if not name or not name.strip():
            return "🏗️ Necesita un nombre para el proyecto."

        name = name.strip()
        template = template.strip().lower()

        if template not in self.TEMPLATES:
            available = ", ".join(self.TEMPLATES.keys())
            return f"🏗️ Template '{template}' no existe. Disponibles: {available}"

        # Determinar ruta
        if not path:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            path = os.path.join(desktop, name)
        else:
            path = os.path.expandvars(os.path.expanduser(path))
            path = os.path.join(path, name)

        if os.path.exists(path):
            return f"🏗️ Ya existe un directorio en '{path}'."

        # Crear estructura
        tmpl = self.TEMPLATES[template]
        name_slug = name.lower().replace(" ", "-").replace("_", "-")
        desc = description or f"Proyecto {name} generado por Genesis"

        created_files = []
        try:
            for filepath, content in tmpl["files"].items():
                full_path = os.path.join(path, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # Reemplazar variables
                rendered = content.format(
                    name=name,
                    name_slug=name_slug,
                    description=desc
                )

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(rendered)
                created_files.append(filepath)

        except Exception as e:
            return f"🏗️ Error creando proyecto: {e}"

        # Registrar en historial
        with self._lock:
            self._history.append({
                "name": name,
                "template": template,
                "path": path,
                "created": datetime.now().isoformat(),
                "files": len(created_files)
            })

        lines = [
            f"🏗️ **Proyecto '{name}' creado** ({template})",
            f"  📁 Ruta: `{path}`",
            f"  📄 {len(created_files)} archivos generados:",
        ]
        for f in created_files:
            lines.append(f"     • {f}")

        lines.append(f"\n  💡 {tmpl['description']}")
        return "\n".join(lines)

    def list_templates(self) -> str:
        """Lista todos los templates disponibles."""
        lines = ["🏗️ **TEMPLATES DISPONIBLES**\n"]
        for name, tmpl in self.TEMPLATES.items():
            file_count = len(tmpl["files"])
            lines.append(f"  📦 **{name}** — {tmpl['description']} ({file_count} archivos)")

        lines.append("\n  💡 Ejemplo: 'crea proyecto mi-app con flask'")
        return "\n".join(lines)

    def history(self) -> str:
        """Muestra proyectos generados."""
        with self._lock:
            if not self._history:
                return "🏗️ No hay proyectos generados aún."

            lines = [f"🏗️ **PROYECTOS GENERADOS** — {len(self._history)}\n"]
            for p in reversed(self._history[-10:]):
                ts = p["created"][:16].replace("T", " ")
                lines.append(f"  [{ts}] **{p['name']}** ({p['template']}) — {p['files']} archivos")
                lines.append(f"     📁 {p['path']}")

            return "\n".join(lines)

    def status(self) -> dict:
        """Estado del scaffolder."""
        return {
            "templates_count": len(self.TEMPLATES),
            "projects_generated": len(self._history)
        }


# Singleton
project_scaffolder = ProjectScaffolder()
