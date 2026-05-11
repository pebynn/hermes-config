#!/usr/bin/env python3
"""
project_scaffold.py -- Interactive project scaffold generator.

Supports three project templates:
  fullstack  -- FastAPI + React (Vite) with Docker Compose
  cli        -- Python CLI tool (click + argparse-style)
  data       -- Python data analysis project (pandas, numpy, jupyter)

Usage:
  python project_scaffold.py --type fullstack --name myapp
  python project_scaffold.py --type cli --name mycli
  python project_scaffold.py --type data --name myanalysis
"""

import argparse
import os
import sys
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────

def mkdir(path: Path):
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def write(path: Path, content: str):
    """Write file ensuring parent directory exists."""
    mkdir(path.parent)
    path.write_text(content, encoding="utf-8")
    print(f"  /u2713  {path}")


def print_tree(base: Path, prefix: str = "", is_last: bool = True):
    """Print a directory tree rooted at *base*."""
    entries = sorted(
        [e for e in base.iterdir() if e.name != "__pycache__"],
        key=lambda x: (not x.is_dir(), x.name.lower()),
    )
    for i, entry in enumerate(entries):
        last = i == len(entries) - 1
        connector = "/u2514/u2500/u2500 " if last else "/u251c/u2500/u2500 "
        print(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if last else "/u2502   "
            print_tree(entry, prefix + extension, last)


# ── Templates ────────────────────────────────────────────────────────────

def scaffold_fullstack(name: str, base: Path):
    """FastAPI + React (Vite) fullstack project."""

    # ── Backend ──────────────────────────────────────────────────────

    write(base / "backend" / "app" / "__init__.py", "")

    write(
        base / "backend" / "app" / "main.py",
        f'''\
"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="{name}", version="0.1.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy", "service": "{name}"}}
''',
    )

    write(
        base / "backend" / "app" / "models.py",
        '''\
"""SQLAlchemy ORM models."""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
''',
    )

    write(
        base / "backend" / "app" / "schemas.py",
        '''\
"""Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel


class ItemBase(BaseModel):
    name: str
    description: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemRead(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
''',
    )

    write(
        base / "backend" / "app" / "database.py",
        f'''\
"""Database connection and session configuration."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./{name}.db"

engine = create_engine(DATABASE_URL, connect_args={{"check_same_thread": False}})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
    )

    write(base / "backend" / "app" / "routers" / "__init__.py", "")

    write(
        base / "backend" / "requirements.txt",
        '''\
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
''',
    )

    write(
        base / "backend" / "Dockerfile",
        '''\
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
''',
    )

    # ── Frontend ─────────────────────────────────────────────────────

    write(
        base / "frontend" / "src" / "App.tsx",
        f'''\
import {{ useState, useEffect }} from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

interface HealthResponse {{
  status: string;
  service: string;
}}

function App() {{
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {{
    fetch(`${{API_BASE}}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setError(err.message));
  }}, []);

  return (
    <div style={{{{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}}}>
      <h1>{{import.meta.env.VITE_APP_NAME || "{name}"}}</h1>
      {{error && <p style={{{{ color: "red" }}}}>Backend error: {{error}}</p>}}
      {{health && (
        <p style={{{{ color: "green" }}}}>
          Backend is <strong>{{health.status}}</strong> &mdash; {{health.service}}
        </p>
      )}}
    </div>
  );
}}

export default App;
''',
    )

    write(
        base / "frontend" / "src" / "main.tsx",
        '''\
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
''',
    )

    write(base / "frontend" / "src" / "components" / ".gitkeep", "")

    write(base / "frontend" / "src" / "pages" / ".gitkeep", "")

    write(
        base / "frontend" / "package.json",
        f'''\
{{
  "name": "{name}-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  }},
  "devDependencies": {{
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.4.0"
  }}
}}
''',
    )

    write(
        base / "frontend" / "tsconfig.json",
        f'''\
{{
  "compilerOptions": {{
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  }},
  "include": ["src"]
}}
''',
    )

    write(
        base / "frontend" / "vite.config.ts",
        f'''\
import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({{
  plugins: [react()],
  server: {{
    port: 5173,
    proxy: {{
      "/api": {{
        target: "http://backend:8000",
        changeOrigin: true,
      }},
    }},
  }},
}});
''',
    )

    write(
        base / "frontend" / "index.html",
        f'''\
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
''',
    )

    # ── Root files ───────────────────────────────────────────────────

    write(
        base / "docker-compose.yml",
        f'''\
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./{name}.db
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    environment:
      - VITE_API_BASE=http://localhost:8000

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: {name}
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: {name}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
''',
    )

    write(
        base / ".env.example",
        f'''\
DATABASE_URL=sqlite:///./{name}.db
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME={name}
''',
    )

    write(
        base / "README.md",
        f'''\
# {name}

A fullstack FastAPI + React project.

## Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Docker

```bash
docker compose up --build
```

The API will be available at http://localhost:8000 and the frontend at
http://localhost:5173.
''',
    )


def scaffold_cli(name: str, base: Path):
    """Python CLI tool project."""

    write(
        base / "src" / "__init__.py",
        f'''\
"""Top-level package for {name}."""

__version__ = "0.1.0"
''',
    )

    write(
        base / "src" / "main.py",
        f'''\
"""CLI entry point for {name}.

Usage:
  python -m src.main hello --name World
"""

import argparse
import sys


def hello(name: str, greeting: str = "Hello") -> None:
    """Print a greeting."""
    print(f"{{greeting}}, {{name}}!")


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch commands."""
    parser = argparse.ArgumentParser(
        prog="{name}",
        description="A friendly CLI tool.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hello subcommand
    hello_parser = subparsers.add_parser("hello", help="Greet someone")
    hello_parser.add_argument(
        "--name", default="World", help="Who to greet (default: World)"
    )
    hello_parser.add_argument(
        "--greeting",
        default="Hello",
        help="Greeting prefix (default: Hello)",
    )

    args = parser.parse_args(argv)

    if args.command == "hello":
        hello(name=args.name, greeting=args.greeting)

    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    )

    write(base / "tests" / "__init__.py", "")

    write(
        base / "tests" / "test_main.py",
        f'''\
"""Tests for {name} CLI."""

from src.main import hello, main


def test_hello_default(capsys):
    hello(name="World")
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, World!"


def test_hello_custom(capsys):
    hello(name="Alice", greeting="Hi")
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hi, Alice!"


def test_main_hello(capsys):
    main(["--help"])
    captured = capsys.readouterr()
    assert "--name" in captured.out
''',
    )

    write(
        base / "requirements.txt",
        '''\
click>=8.1.0
requests>=2.31.0
''',
    )

    write(
        base / "setup.py",
        f'''\
"""Setup script for {name}."""

from setuptools import find_packages, setup

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
    entry_points={{"console_scripts": ["{name}=main:main"]}},
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
    ],
)
''',
    )

    write(
        base / "README.md",
        f'''\
# {name}

A Python CLI tool.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# With the installed command
{name} hello --name Alice

# Or directly with Python
python -m src.main hello --name Alice
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
''',
    )


def scaffold_data(name: str, base: Path):
    """Python data analysis project."""

    write(base / "data" / ".gitkeep", "")

    write(
        base / "notebooks" / "analysis.ipynb",
        f'''\
{{
 "cells": [
  {{
   "cell_type": "markdown",
   "metadata": {{}},
   "source": [
    "# {name}\\n",
    "\\n",
    "Initial exploratory data analysis notebook."
   ]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [
    "import pandas as pd\\n",
    "import numpy as np\\n",
    "import matplotlib.pyplot as plt\\n",
    "\\n",
    "print(\\"Libraries loaded successfully.\\")"
   ]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [
    "# Load data\\n",
    "# df = pd.read_csv('data/dataset.csv')\\n",
    "# df.head()"
   ]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [
    "# Summary statistics\\n",
    "# df.describe()"
   ]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [
    "# Quick visualization\\n",
    "# df.hist(bins=30, figsize=(12, 8))\\n",
    "# plt.tight_layout()\\n",
    "# plt.show()"
   ]
  }}
 ],
 "metadata": {{
  "kernelspec": {{
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }},
  "language_info": {{
   "name": "python",
   "version": "3.12.0"
  }}
 }},
 "nbformat": 4,
 "nbformat_minor": 5
}}
''',
    )

    write(base / "scripts" / "__init__.py", "")

    write(
        base / "scripts" / "fetch.py",
        f'''\
"""Fetch data from a remote source and store it locally."""

import argparse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_data(url: str, output: str | None = None) -> Path:
    """Download data from *url* and save to *data/*."""
    import requests

    output_path = DATA_DIR / (output or url.split("/")[-1])
    print(f"Downloading {{url}} ...")
    resp = requests.get(url, stream=True)
    resp.raise_for_status()

    output_path.write_bytes(resp.content)
    print(f"Saved to {{output_path}}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Fetch data for {name}.")
    parser.add_argument("url", help="URL of the data file to download")
    parser.add_argument(
        "-o", "--output", help="Output filename (default: derived from URL)"
    )
    args = parser.parse_args()
    fetch_data(args.url, args.output)


if __name__ == "__main__":
    main()
''',
    )

    write(
        base / "scripts" / "analyze.py",
        f'''\
"""Run data analysis and produce summary figures."""

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def analyze(csv_path: str) -> None:
    """Load CSV, print summary, and save a correlation heatmap."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(csv_path)
    print(f"Shape: {{df.shape}}")
    print(f"Columns: {{list(df.columns)}}")
    print(df.describe())

    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] > 1:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(numeric.corr(), annot=True, cmap="coolwarm", ax=ax)
        ax.set_title("Correlation Matrix")
        out = OUTPUT_DIR / "correlation.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Saved correlation heatmap to {{out}}")
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Analyze data for {name}.")
    parser.add_argument("csv", help="Path to the CSV file to analyze")
    args = parser.parse_args()
    analyze(args.csv)


if __name__ == "__main__":
    main()
''',
    )

    write(
        base / "requirements.txt",
        '''\
pandas>=2.2.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
jupyter>=1.0.0
requests>=2.31.0
''',
    )

    write(
        base / "README.md",
        f'''\
# {name}

A data analysis project.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

1. Place raw data files in the `data/` directory.
2. Use `scripts/fetch.py` to download remote data:
   ```bash
   python scripts/fetch.py https://example.com/data.csv
   ```
3. Run analysis:
   ```bash
   python scripts/analyze.py data/dataset.csv
   ```
4. Explore interactively in Jupyter:
   ```bash
   jupyter notebook notebooks/analysis.ipynb
   ```

## Structure

```
{name}/
├── data/          Raw datasets
├── notebooks/     Jupyter notebooks
├── scripts/       Reusable analysis scripts
└── output/        Generated figures and reports
```
''',
    )


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive project scaffold generator.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["fullstack", "cli", "data"],
        help="Project template type",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Project name (used as directory name)",
    )
    parser.add_argument(
        "--dest",
        default=".",
        help="Parent directory to create the project in (default: current dir)",
    )

    args = parser.parse_args()
    base = Path(args.dest).resolve() / args.name

    if base.exists():
        print(f"Error: directory '{base}' already exists.", file=sys.stderr)
        sys.exit(1)

    print(f"\nScaffolding project '{args.name}' ({args.type}) in {base} ...\n")

    if args.type == "fullstack":
        scaffold_fullstack(args.name, base)
    elif args.type == "cli":
        scaffold_cli(args.name, base)
    elif args.type == "data":
        scaffold_data(args.name, base)

    print(f"\nProject tree:\n")
    print(f"{base.name}/")
    print_tree(base)

    print(f"\nDone. Project created at {base}\n")


if __name__ == "__main__":
    main()
