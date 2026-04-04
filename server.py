"""
server.py — Entry point for the FastAPI backend server.

Usage:
    uv run server.py
    # or directly:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Docs available at: http://localhost:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app", "src"],   # watch only source dirs, NOT .venv
        log_level="info",
    )
