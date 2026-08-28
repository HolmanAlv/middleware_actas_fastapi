"""Construcción del PDF con ReportLab Platypus.

Aquí vive solo el *layout* (encabezado institucional, tablas, firmas, pie). El texto de
cada acta está en `services/actas.py`.

ponytail: ReportLab en vez de WeasyPrint — cero dependencias nativas (WeasyPrint exige
GTK/Pango, que no instala con pip en Windows).
"""

from __future__ import annotations

import contextvars
from functools import lru_cache, partial
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.config_institucional import LOGO_ALTO, LOGO_ANCHO, LOGO_PATH, Formato

ANCHO_UTIL = LETTER[0] - 100  # márgenes izquierdo/derecho de 50

# Tamaño de letra del documento en construcción (payload.tamano_letra, 1-50). ContextVar en vez
# de un global simple: FastAPI corre los endpoints sync en threads del threadpool, y cada uno
# necesita su propio valor sin pisar el de una petición concurrente.
_TAMANO_LETRA: contextvars.ContextVar[int] = contextvars.ContextVar("tamano_letra", default=10)


def usar_tamano_letra(tamano: int) -> None:
    """Fija el tamaño de letra para el acta que se está construyendo (llamar antes del story)."""
    _TAMANO_LETRA.set(tamano)


@lru_cache(maxsize=50)
def _construir_estilos(tamano: int) -> dict[str, ParagraphStyle]:
    """Estilos del cuerpo del acta, escalados sobre el tamaño base de diseño (10 pt = factor 1.0)."""
    f = tamano / 10
    cuerpo = ParagraphStyle(
        "cuerpo", fontName="Helvetica", fontSize=tamano, leading=13.5 * f, alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    celda = ParagraphStyle(
        "celda", parent=cuerpo, fontSize=8.5 * f, leading=11 * f, spaceAfter=0, alignment=TA_LEFT
    )
    celda_bold = ParagraphStyle("celda_bold", parent=celda, fontName="Helvetica-Bold")
    return {
        "cuerpo": cuerpo,
        "cuerpo_sangria": ParagraphStyle("cuerpo_sangria", parent=cuerpo, leftIndent=18),
        "titulo": ParagraphStyle(
            "titulo", parent=cuerpo, fontName="Helvetica-Bold", fontSize=11 * f,
            alignment=TA_CENTER, spaceAfter=12,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=cuerpo, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceBefore=8,
        ),
        "celda": celda,
        "celda_bold": celda_bold,
        "celda_centro": ParagraphStyle("celda_centro", parent=celda, alignment=TA_CENTER),
        "celda_centro_bold": ParagraphStyle("celda_centro_bold", parent=celda_bold, alignment=TA_CENTER),
    }


def _e() -> dict[str, ParagraphStyle]:
    return _construir_estilos(_TAMANO_LETRA.get())


def cuerpo_sangria() -> ParagraphStyle:
    return _e()["cuerpo_sangria"]


# ponytail: la cabecera institucional (macroproceso/código/versión) va a tamaño fijo, no escala
# con tamano_letra — sus columnas son angostas y un texto grande la desborda; "tamaño de letra
# del documento" se refiere al cuerpo del acta, no al membrete de formato.
_CABECERA_CELDA = ParagraphStyle(
    "cabecera_celda", fontName="Helvetica", fontSize=8.5, leading=11, alignment=TA_LEFT, spaceAfter=0,
)
_CABECERA_CELDA_CENTRO = ParagraphStyle(
    "cabecera_celda_centro", parent=_CABECERA_CELDA, alignment=TA_CENTER
)
_CABECERA_CELDA_LOGO = ParagraphStyle(
    "cabecera_celda_logo", parent=_CABECERA_CELDA_CENTRO, fontName="Helvetica-Bold", fontSize=6.5,
    leading=8,
)


class Ctx(dict):
    """Contexto de sustitución: los campos ausentes se imprimen como '________'."""

    def __missing__(self, clave: str) -> str:  # noqa: D105
        return "________"


class Crudo(str):
    """Texto de confianza que ya trae marcado ReportLab (`<b>`, `<i>`) y NO debe escaparse.

    Solo para los textos legales de `config_institucional`; nunca para datos del payload.
    """


def ctx_escapado(datos: dict) -> Ctx:
    """Escapa los valores para que ReportLab no rompa con '&' o '<' del usuario."""
    return Ctx({
        k: v if isinstance(v, Crudo) else escape(str(v)) for k, v in datos.items()
    })


def t(plantilla: str, c: Ctx) -> str:
    """Interpola la plantilla de texto con el contexto ya escapado."""
    return plantilla.format_map(c)


def p(texto: str, style: ParagraphStyle | None = None) -> Paragraph:
    return Paragraph(texto, style or _e()["cuerpo"])


def titulo(texto: str) -> Paragraph:
    return Paragraph(texto, _e()["titulo"])


def seccion(texto: str) -> Paragraph:
    return Paragraph(texto, _e()["seccion"])


def espacio(alto: float = 8) -> Spacer:
    return Spacer(1, alto)


def tabla_info(filas: list[tuple[str, str]]) -> Table:
    """Tabla de dos columnas 'CAMPO | contenido' del encabezado de datos del contrato."""
    e = _e()
    data = [[Paragraph(k, e["celda_bold"]), Paragraph(v, e["celda"])] for k, v in filas]
    tabla = Table(data, colWidths=[135, ANCHO_UTIL - 135], hAlign="CENTER")
    tabla.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.92, 0.92, 0.92)),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    return tabla


def tabla_datos(encabezados: list[str], filas: list[list[str]]) -> Table:
    """Tabla genérica con fila de encabezado (balance de liquidación, revisión, etc.)."""
    e = _e()
    data = [[Paragraph(h, e["celda_centro_bold"]) for h in encabezados]]
    data += [[Paragraph(celda, e["celda"]) for celda in fila] for fila in filas]
    ancho = ANCHO_UTIL / len(encabezados)
    tabla = Table(data, colWidths=[ancho] * len(encabezados), hAlign="CENTER", repeatRows=1)
    tabla.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.92, 0.92, 0.92)),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    return tabla


def bloque_firmas(firmas: list[tuple[str, str]]) -> KeepTogether:
    """Pares (nombre, cargo) con línea de firma, en dos columnas."""
    celda_centro = _e()["celda_centro"]
    celdas = []
    for nombre, cargo in firmas:
        celdas.append(
            Paragraph(
                f"<br/><br/>_______________________________<br/>"
                f"<b>{nombre}</b><br/>{cargo}",
                celda_centro,
            )
        )
    if len(celdas) % 2:
        celdas.append(Paragraph("", celda_centro))
    filas = [celdas[i:i + 2] for i in range(0, len(celdas), 2)]
    tabla = Table(filas, colWidths=[ANCHO_UTIL / 2] * 2, hAlign="CENTER")
    tabla.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    return KeepTogether([tabla])


def bloque_revision(proyecto: str, cargo_proyecto: str, aprobo: str, cargo_aprobo: str) -> Table:
    filas = [["Proyectó", proyecto, cargo_proyecto], ["Revisó y Aprobó", aprobo, cargo_aprobo]]
    return tabla_datos(["Acción", "Nombre", "Cargo"], filas)


@lru_cache(maxsize=1)
def _logo_png() -> bytes | None:
    """Reescala el logo una sola vez a la resolución de impresión.

    El PNG institucional viene a ~1500 px / 1 MB y ReportLab embebe el original tal cual: eso
    sumaría ~1 MB a cada PDF (y un 33 % más al pasarlo a base64). A 60 pt de ancho, 300 px
    sobran incluso para impresión.
    """
    if not LOGO_PATH.exists():
        return None
    from PIL import Image as Pil

    with Pil.open(LOGO_PATH) as im:
        im = im.convert("RGBA")
        im.thumbnail((300, 300), Pil.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _logo():
    """Logo institucional; si no está el PNG, se dibuja el nombre como marca de posición."""
    png = _logo_png()
    if png is None:
        return Paragraph("<b>UNIVERSIDAD<br/>DISTRITAL</b>", _CABECERA_CELDA_LOGO)
    # BytesIO nuevo en cada llamada: el stream se consume al construir la página.
    return Image(BytesIO(png), width=LOGO_ANCHO, height=LOGO_ALTO, kind="proportional")


def _cabecera(formato: Formato) -> Table:
    data = [
        [_logo(), Paragraph(f"<b>Macroproceso:</b> {formato.macroproceso}", _CABECERA_CELDA),
         Paragraph(f"<b>Código:</b> {formato.codigo}", _CABECERA_CELDA)],
        ["", Paragraph(f"<b>Proceso:</b> {formato.proceso}", _CABECERA_CELDA),
         Paragraph(f"<b>Versión:</b> {formato.version}", _CABECERA_CELDA)],
        ["", Paragraph(f"<b>{formato.titulo}</b>", _CABECERA_CELDA_CENTRO),
         Paragraph(f"<b>Fecha de aprobación:</b> {formato.fecha_aprobacion}", _CABECERA_CELDA)],
    ]
    tabla = Table(data, colWidths=[70, ANCHO_UTIL - 70 - 140, 140], rowHeights=[20, 20, 26])
    tabla.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("SPAN", (0, 0), (0, 2)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ])
    )
    return tabla


def _dibujar_marco(canvas, doc, formato: Formato, pie: tuple[str, ...]):
    canvas.saveState()
    cabecera = _cabecera(formato)
    _, alto = cabecera.wrap(ANCHO_UTIL, doc.topMargin)
    cabecera.drawOn(canvas, 50, LETTER[1] - 30 - alto)

    canvas.setFont("Helvetica", 7)
    y = 34
    for linea in pie:
        canvas.drawCentredString(LETTER[0] / 2, y, linea)
        y -= 8
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(LETTER[0] - 50, 20, f"Página {doc.page}")
    canvas.restoreState()


def render(formato: Formato, flowables: list, pie: tuple[str, ...] = ()) -> bytes:
    """Arma el PDF y devuelve sus bytes. Página LETTER, márgenes [50, 110, 50, 45]."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=50,
        rightMargin=50,
        topMargin=110,
        bottomMargin=45 + 8 * len(pie),
        title=formato.titulo,
        author="Universidad Distrital Francisco José de Caldas",
        subject=formato.codigo,
    )
    marco = partial(_dibujar_marco, formato=formato, pie=pie)
    doc.build(list(flowables), onFirstPage=marco, onLaterPages=marco)
    return buffer.getvalue()
