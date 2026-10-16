"""Thin loader so both entry points expose the same app.

The adapter module is loaded by path (tests use shared_mvp.app.load) while the
uvicorn entry point needs plain imports. Adding this directory to sys.path here
keeps sibling modules such as c05_gemini importable without a package layout.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def create_app(db_path=None, provider=None):
    spec = importlib.util.spec_from_file_location("c05_api", HERE / "c05_api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_app(db_path, provider)


app = create_app()
