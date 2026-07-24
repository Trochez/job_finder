"""Run job_finder dashboard server."""
from job_finder.web.app import create_app
import uvicorn

uvicorn.run(create_app(), host="127.0.0.1", port=8000)
