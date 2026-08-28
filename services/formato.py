"""Formateo de fechas, valores y plazos tal como los imprime el acta.

Equivale a `format_date_letter_mongo()`, `NumeroALetras()`, `numberFormat()` y
`calculoPlazoLetras()` del cliente original.
"""

from datetime import date
from decimal import Decimal

from num2words import num2words

VACIO = "________"

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

ORDINALES = (
    "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
    "OCTAVA", "NOVENA", "DÉCIMA", "UNDÉCIMA", "DUODÉCIMA",
)


def fecha_letras(d: date | None) -> str:
    """25 de junio de 2026"""
    if d is None:
        return VACIO
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date | None) -> str:
    """25/06/2026"""
    return d.strftime("%d/%m/%Y") if d else VACIO


def moneda(v: Decimal | int | None) -> str:
    """1.234.567 (separador de miles con punto, sin decimales si son cero)."""
    if v is None:
        return VACIO
    v = Decimal(v)
    entero, centavos = divmod(v.quantize(Decimal("0.01")), 1)
    miles = f"{int(entero):,}".replace(",", ".")
    if centavos:
        return f"{miles},{int(centavos * 100):02d}"
    return miles


def moneda_letras(v: Decimal | int | None) -> str:
    """DIEZ MILLONES DE PESOS"""
    if v is None:
        return VACIO
    v = Decimal(v).quantize(Decimal("0.01"))
    entero = int(v)
    palabras = num2words(entero, lang="es")
    # "diez millones de pesos" lleva 'de'; "cien mil pesos" no.
    nexo = " DE " if palabras.endswith(("millón", "millones", "billón", "billones")) else " "
    texto = f"{palabras}{nexo}PESOS".upper()
    centavos = int((v - entero) * 100)
    if centavos:
        texto += f" CON {num2words(centavos, lang='es').upper()} CENTAVOS"
    return texto


def numero_letras(n: int | None) -> str:
    """dos (2)"""
    if n is None:
        return VACIO
    return f"{num2words(n, lang='es')} ({n})"


def plazo_letras(meses: int = 0, dias: int = 0) -> str:
    """dos (2) meses y quince (15) días"""
    partes = []
    if meses:
        partes.append(f"{numero_letras(meses)} {'mes' if meses == 1 else 'meses'}")
    if dias:
        partes.append(f"{numero_letras(dias)} {'día' if dias == 1 else 'días'}")
    return " y ".join(partes) if partes else VACIO


def o_vacio(v) -> str:
    """Fallback '________' de los campos sin dato, igual que el cliente original."""
    if v is None:
        return VACIO
    texto = str(v).strip()
    return texto or VACIO
