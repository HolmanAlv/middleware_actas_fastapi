"""actas_novedad_mid — middleware sin estado para generar PDFs de actas de novedades.

No hay base de datos ni persistencia: recibe el payload, arma el PDF al vuelo y devuelve
JSON con el archivo en base64.

    uvicorn main:app --reload --port 8080
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.actas import router as actas_router

app = FastAPI(
    title="actas_novedad_mid",
    version="1.0.0",
    description="Generación de PDFs de actas de novedades poscontractuales (stateless).",
)

# El front consume este servicio desde el navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(actas_router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "service": "actas_novedad_mid"}
