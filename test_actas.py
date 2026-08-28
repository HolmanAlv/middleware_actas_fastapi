"""Check mínimo: las 5 actas generan un PDF válido y las reglas de negocio rechazan lo inválido.

    python -m pytest test_actas.py

Los payloads de ejemplo viven en `generar_ejemplos.py` (mismo fixture que el volcado a
`ejemplos_output/`), así no hay dos copias del mismo contrato de prueba.
"""

import base64
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from generar_ejemplos import (
    CONTRATO,
    payload_adicion_prorroga,
    payload_cesion,
    payload_reinicio,
    payload_suspension,
    payload_terminacion,
)
from models.schemas import AdicionProrrogaIn, CesionIn, SuspensionIn, TerminacionLiquidacionIn
from services.actas import generar_acta
from services.formato import moneda, moneda_letras, plazo_letras


def _pdf(tipo, payload) -> bytes:
    r = generar_acta(tipo, payload)
    assert r.success and r.filename.endswith(".pdf")
    crudo = base64.b64decode(r.file_base64)
    assert crudo.startswith(b"%PDF-"), "el base64 no decodifica a un PDF"
    assert r.metadata.size_bytes == len(crudo) > 2000
    return crudo


def test_suspension():
    d = payload_suspension()
    assert d.fecha_reinicio == date(2024, 5, 1)  # fin de suspensión + 1 día
    _pdf("suspension", d)


def test_reinicio():
    d = payload_reinicio()
    assert d.fecha_reinicio == date(2024, 5, 1)
    _pdf("reinicio", d)


def test_adicion_y_prorroga():
    d = payload_adicion_prorroga()
    assert d.nuevo_valor_total == Decimal("12000000")
    _pdf("adicion_prorroga", d)


def test_adicion_supera_el_50_por_ciento_es_rechazada():
    with pytest.raises(ValidationError, match="supera el"):
        payload_adicion_prorroga(valor_adicion="5000001")


def test_modificacion_sin_prorroga_es_rechazada():
    """El acta es adición Y prórroga: sin tiempo de prórroga no se puede emitir."""
    with pytest.raises(ValidationError, match="prórroga es obligatoria"):
        payload_adicion_prorroga(prorroga_meses=0, prorroga_dias=0)


def test_modificacion_sin_adicion_es_rechazada():
    with pytest.raises(ValidationError, match="valor_adicion"):
        payload_adicion_prorroga(valor_adicion=None)


def test_cesion():
    d = payload_cesion()
    assert d.valor_cesionario == Decimal("4000000")  # 10M − (5M + 1M)
    _pdf("cesion", d)


def test_cesion_con_liquidacion_mayor_al_contrato_es_rechazada():
    with pytest.raises(ValidationError, match="no puede superar"):
        payload_cesion(valor_desembolsado="9000000", valor_a_favor="2000000")


def test_terminacion_liquidacion_calcula_saldo_universidad():
    d = payload_terminacion()
    assert d.saldo_universidad == Decimal("2000000")  # 10M − 5M − 3M
    _pdf("terminacion_liquidacion", d)


def test_terminacion_con_balance_descuadrado_es_rechazada():
    with pytest.raises(ValidationError, match="no cuadra"):
        payload_terminacion(saldo_universidad="9999999")


def test_periodo_de_suspension_invertido_es_rechazado():
    with pytest.raises(ValidationError, match="no puede ser anterior"):
        payload_suspension(fecha_inicio_suspension="2024-04-30", fecha_fin_suspension="2024-04-10")


def test_acta_sin_ordenador_es_rechazada():
    with pytest.raises(ValidationError, match="contrato.ordenador"):
        payload_suspension(contrato={**CONTRATO, "ordenador": None})


def test_el_logo_queda_embebido_sin_inflar_el_pdf():
    """El PNG institucional pesa ~1 MB: debe entrar reescalado, no en crudo."""
    from services.pdf_builder import _logo_png

    png = _logo_png()
    assert png is not None, "falta assets/logo.png"
    assert len(png) < 120_000, f"el logo reescalado pesa {len(png)} bytes"
    assert len(_pdf("suspension", payload_suspension())) < 250_000


def test_los_textos_legales_conservan_su_marcado_y_el_payload_se_escapa():
    """El `<b>` de los textos legales debe imprimirse en negrita, no como literal."""
    from services.pdf_builder import Crudo, ctx_escapado

    c = ctx_escapado({"legal": Crudo("<b>LA UNIVERSIDAD</b>"), "usuario": "A & B <script>"})
    assert c["legal"] == "<b>LA UNIVERSIDAD</b>"
    assert c["usuario"] == "A &amp; B &lt;script&gt;"
    assert c["campo_ausente"] == "________"


def test_formateo():
    assert moneda(Decimal("10000000")) == "10.000.000"
    assert moneda(Decimal("1234567.50")) == "1.234.567,50"
    assert moneda_letras(Decimal("10000000")) == "DIEZ MILLONES DE PESOS"
    assert moneda_letras(Decimal("100000")) == "CIEN MIL PESOS"
    assert plazo_letras(2, 15) == "dos (2) meses y quince (15) días"
    assert plazo_letras(1, 0) == "uno (1) mes"


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", __file__]))
