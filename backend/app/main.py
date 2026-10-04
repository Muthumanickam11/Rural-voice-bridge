"""Alias module: the real application object is defined in `backend/main.py`.

Importing `app.main:app` (uvicorn) returns exactly the same object as
`main:app`, because both ultimately import the canonical `main` module.
"""

from main import app

__all__ = ["app"]