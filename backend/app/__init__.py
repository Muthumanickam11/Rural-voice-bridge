"""Compatibility alias so `uvicorn app.main:app` works alongside `uvicorn main:app`.

The application actually lives in `backend/main.py`. `app.main:app` is the other
common FastAPI entry-point convention, and it is easy to type by mistake, so this
package re-exports the same ASGI object rather than duplicating any setup.

Both import paths resolve to one and the same FastAPI instance: this module does
`from main import app`, so the canonical `main` module is still the only place the
app is constructed.
"""

from main import app

__all__ = ["app"]