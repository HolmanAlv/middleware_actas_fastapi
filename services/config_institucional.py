"""Parámetros institucionales y textos legales citados en las actas.

Todo lo que `parametros_actas.csv` marca como `fuente_recomendada = BD parámetros/config`
vive aquí, en un solo archivo, para poder actualizarlo sin tocar la lógica.

ponytail: constantes en módulo, no tabla de parámetros versionada. Migrar a BD el día
que Contratación necesite cambiar un texto sin redespliegue.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Formato:
    titulo: str
    codigo: str
    version: str
    fecha_aprobacion: str
    macroproceso: str = "Gestión de Recursos"
    proceso: str = "Gestión de Contratación"


FORMATOS: dict[str, Formato] = {
    "suspension": Formato("ACTA DE SUSPENSIÓN", "GC-PR-014-FR-054", "02", "22/09/2025"),
    "reinicio": Formato("ACTA DE REINICIO", "GC-PR-014-FR-053", "02", "22/09/2025"),
    "adicion_prorroga": Formato(
        "MODIFICACIÓN: ADICIÓN Y PRÓRROGA", "GC-PR-014", "02", "22/09/2025"
    ),
    "cesion": Formato("ACTA DE CESIÓN", "GC-PR-014-FR-052", "02", "29/09/2025"),
    "terminacion_liquidacion": Formato(
        "ACTA DE TERMINACIÓN Y LIQUIDACIÓN BILATERAL", "GC-PR-014-FR-057", "02", "22/09/2025"
    ),
}

UNIVERSIDAD = "Universidad Distrital Francisco José de Caldas"
NIT_UNIVERSIDAD = "899.999.230-7"
CIUDAD_FIRMA_DEFECTO = "Bogotá D.C."

PIE_OFICINA_CONTRATACION = (
    "UNIVERSIDAD DISTRITAL FRANCISCO JOSÉ DE CALDAS",
    "OFICINA DE CONTRATACIÓN",
    "CARRERA 7 No. 40B-53, Piso 9",
    "Teléfono 33393300, Ext. 1911 y 1912",
    "Bogotá D.C.",
)

ACUERDO_ESTATUTO = "Acuerdo 003 de 2015"
RESOLUCION_RECTORIA = "Resolución de Rectoría 262 de 2015"
CIRCULAR_COLOMBIA_COMPRA = "Circular No. 001 de 2019"

# Regla de negocio: la adición no puede superar este porcentaje del valor inicial.
LIMITE_ADICION_PORCENTAJE = Decimal("50")

TEXTO_CLAUSULA_19_SUSPENSION = (
    "Las partes contratantes podrán suspender la ejecución del contrato, mediante suscripción "
    "de un acta en donde conste tal evento, cuando medie alguna de las siguientes causales. "
    "1) por circunstancias de fuerza mayor o caso fortuito, debidamente comprobadas, que "
    "imposibiliten su ejecución. 2) por solicitud debidamente sustentada, elevada por una de "
    "las partes. El término de la suspensión no será computable para efecto del plazo de "
    "ejecución del contrato, ni dará derecho a exigir indemnización, sobre costos o reajustes, "
    "ni a reclamar gastos diferentes a los pactados en el contrato."
)

TEXTO_PARAGRAFO_19_GARANTIA = (
    "PARÁGRAFO. En caso de operar la suspensión del contrato, <b>EL CONTRATISTA</b> se "
    "compromete a presentar certificado de modificación de la garantía única, ampliando su "
    "vigencia por el término que dure la suspensión"
)

TEXTO_CLAUSULA_17_TERMINACION = (
    "Terminación. Serán causales de terminación del contrato el común acuerdo de las partes al "
    "respecto, la ocurrencia de cualquier circunstancia de fuerza mayor o caso fortuito que "
    "impida la ejecución del contrato, así como el cumplimiento del plazo pactado para su "
    "ejecución. Adicionalmente, dará lugar a la terminación anticipada del contrato el "
    "incumplimiento de sus obligaciones, por parte de EL CONTRATISTA, debidamente comprobado, "
    "que impida continuar con su ejecución"
)

TEXTO_CLAUSULA_15_CESION = (
    "El Contratista no puede ceder parcial ni totalmente sus obligaciones o derechos derivados "
    "del presente Contrato, sin la autorización previa y por escrito de <b>LA UNIVERSIDAD</b>"
)

TEXTO_CLAUSULA_16_MODIFICACION = (
    "El contrato solo podrá ser modificado, adicionado y/o prorrogado de mutuo acuerdo entre "
    "las partes, mediante OTROSI, el cual hará parte integral del presente contrato"
)

# Cargos del bloque de revisión según la unidad ejecutora (1 = Oficina de Contratación).
CARGOS_REVISION = {
    "contratacion": ("Abogado Oficina de Contratación", "Jefe Oficina de Contratación"),
    "ofex": ("CPS Coordinadora Legal - Ofex", "Jefe Oficina de Extensión y Supervisor - Ofex"),
}


def cargos_revision(unidad_ejecutora: int) -> tuple[str, str]:
    return CARGOS_REVISION["contratacion" if unidad_ejecutora == 1 else "ofex"]


# Logo institucional. Si el PNG no existe, el encabezado dibuja el nombre en texto.
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"

# Caja donde se dibuja el logo en el encabezado (puntos). Se respeta la proporción original.
LOGO_ANCHO = 60
LOGO_ALTO = 62
