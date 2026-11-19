# actas_novedad_mid

Microservicio **FastAPI sin estado** que genera en PDF las actas de novedades poscontractuales de la Universidad Distrital (suspensión, reinicio, adición y prórroga, cesión, terminación y liquidación).

Recibe todos los datos del contrato en un JSON, valida las reglas de negocio con Pydantic, arma el PDF al vuelo con ReportLab y lo devuelve en base64. No tiene base de datos ni guarda nada.

Lo construí durante mi pasantía como servicio provisional para el microfrontend [`novedades_mf`](https://github.com/udistrital/novedades_mf) (Angular 18 + single-spa). Después la generación pasó al middleware institucional sin tocar el dominio del front.

## Stack

Python 3 · FastAPI · Pydantic v2 · ReportLab · num2words · pytest

## Endpoints

| Acta | Ruta (POST) | Código |
|---|---|---|
| Suspensión | `/v1/actas/suspension` | `NP_SUS` |
| Reinicio | `/v1/actas/reinicio` | `NP_REI` |
| Adición y prórroga | `/v1/actas/adicion-prorroga` | `NP_ADPRO` |
| Cesión | `/v1/actas/cesion` | `NP_CES` |
| Terminación y liquidación | `/v1/actas/terminacion-liquidacion` | — |

`GET /health` sirve como healthcheck y `/docs` abre el OpenAPI interactivo. Los esquemas completos de entrada y salida están en [`docs_integracion_agente_actas_mid.md`](docs_integracion_agente_actas_mid.md).

## Uso

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Para limitar los orígenes permitidos se usa `CORS_ORIGINS` (lista separada por comas; por defecto `*`).

## Pruebas y ejemplos

```bash
pip install pytest
python -m pytest test_actas.py   # 15 pruebas: las 5 actas generan un PDF válido y se rechazan los datos inválidos
python generar_ejemplos.py       # vuelve a generar los PDF de ejemplo en ejemplos_output/
```

## Estructura

```
main.py                  app, CORS y healthcheck
routers/actas.py         un endpoint por tipo de acta
models/schemas.py        contratos de entrada/salida y validaciones
services/actas.py        texto y reglas de cada acta
services/pdf_builder.py  maquetado del PDF
services/formato.py      fechas, moneda y números en letras
```
