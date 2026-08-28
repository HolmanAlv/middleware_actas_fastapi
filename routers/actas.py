"""Endpoints POST: reciben el payload completo y devuelven el PDF en base64."""

from fastapi import APIRouter

from models.schemas import (
    ActaResponse,
    AdicionProrrogaIn,
    CesionIn,
    ReinicioIn,
    SuspensionIn,
    TerminacionLiquidacionIn,
)
from services.actas import generar_acta

router = APIRouter(prefix="/v1/actas", tags=["actas"])


@router.post("/suspension", response_model=ActaResponse, summary="Acta de suspensión (NP_SUS)")
def acta_suspension(payload: SuspensionIn) -> ActaResponse:
    return generar_acta("suspension", payload)


@router.post("/reinicio", response_model=ActaResponse, summary="Acta de reinicio (NP_REI)")
def acta_reinicio(payload: ReinicioIn) -> ActaResponse:
    return generar_acta("reinicio", payload)


@router.post(
    "/adicion-prorroga",
    response_model=ActaResponse,
    summary="Modificación: adición y prórroga (NP_ADPRO) — ambas obligatorias",
)
def acta_adicion_prorroga(payload: AdicionProrrogaIn) -> ActaResponse:
    return generar_acta("adicion_prorroga", payload)


@router.post("/cesion", response_model=ActaResponse, summary="Acta de cesión (NP_CES)")
def acta_cesion(payload: CesionIn) -> ActaResponse:
    return generar_acta("cesion", payload)


@router.post(
    "/terminacion-liquidacion",
    response_model=ActaResponse,
    summary="Acta de terminación anticipada y liquidación bilateral",
)
def acta_terminacion_liquidacion(payload: TerminacionLiquidacionIn) -> ActaResponse:
    return generar_acta("terminacion_liquidacion", payload)
