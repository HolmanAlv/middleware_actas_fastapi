"""Payloads de ejemplo de las 5 actas + volcado a `ejemplos_output/`.

    python generar_ejemplos.py

Los mismos payloads los reutiliza `test_actas.py`, así que sirven a la vez como ejemplo
para el front y como fixture de pruebas.
"""

import base64
import pathlib

from models.schemas import (
    AdicionProrrogaIn,
    CesionIn,
    ReinicioIn,
    SuspensionIn,
    SuspensionPrevia,
    TerminacionLiquidacionIn,
)
from services.actas import generar_acta

SALIDA = pathlib.Path(__file__).resolve().parent / "ejemplos_output"

CONTRATO = {
    "numero_contrato": "1234",
    "vigencia": 2024,
    "tipo_contrato": "Contrato de Prestación de Servicios",
    "objeto_contrato": "Prestar servicios profesionales de apoyo <jurídico> & administrativo "
                      "a la Oficina de Contratación de la Universidad",
    "valor_contrato": "10000000",
    "plazo": "tres (3) meses",
    "plazo_dias": 90,
    "fecha_suscripcion": "2024-02-05",
    "fecha_inicio": "2024-03-01",
    "cdp_numero": "CDP-001",
    "rp_numero": "RP-001",
    "cdp_vigencia": 2024,
    "unidad_ejecutora": 1,
    "contratista": {
        "nombre": "Juan Pérez", "documento": "1010101010",
        "tipo_documento": "C.C.", "ciudad_documento": "Bogotá",
    },
    "supervisor": {
        "nombre": "María Gómez", "documento": "2020202020",
        "tipo_documento": "C.C.", "ciudad_documento": "Bogotá", "rol": "Supervisor",
    },
    "ordenador": {
        "nombre": "Carlos Ruiz", "documento": "3030303030",
        "tipo_documento": "C.C.", "ciudad_documento": "Bogotá",
        "rol": "Director", "resolucion": "Resolución 262-2025",
    },
}

SUSPENSION_PREVIA = SuspensionPrevia(
    fecha_acta="2024-04-09",
    fecha_inicio_suspension="2024-04-10",
    fecha_fin_suspension="2024-04-30",
)


def payload_suspension(**over) -> SuspensionIn:
    return SuspensionIn(**{
        "contrato": CONTRATO,
        "fecha_inicio_suspension": "2024-04-10",
        "fecha_fin_suspension": "2024-04-30",
        "motivo": "Fuerza mayor comprobada por cierre temporal de la sede",
        "fecha_solicitud": "2024-04-05",
        "numero_oficio_supervisor": "OF-456",
        "fecha_oficio_supervisor": "2024-04-06",
        "numero_oficio_ordenador": "OF-789",
        "fecha_oficio_ordenador": "2024-04-08",
        "fecha_expedicion_acta": "2024-04-09",
        "elaboro": "Laura Niño",
        "jefe_juridica_nombre": "Ana Torres",
        "nueva_clausula": "El contratista deberá reportar el estado de los entregables "
                          "parciales antes del reinicio.",
        **over,
    })


def payload_reinicio(**over) -> ReinicioIn:
    return ReinicioIn(**{
        "contrato": CONTRATO,
        "suspension_previa": SUSPENSION_PREVIA,
        "fecha_expedicion_acta": "2024-05-01",
        "elaboro": "Laura Niño",
        "jefe_juridica_nombre": "Ana Torres",
        **over,
    })


def payload_adicion_prorroga(**over) -> AdicionProrrogaIn:
    return AdicionProrrogaIn(**{
        "contrato": CONTRATO,
        "valor_adicion": "2000000",
        "prorroga_meses": 2,
        "prorroga_dias": 15,
        "numero_oficio": "OF-321",
        "fecha_oficio": "2024-05-15",
        "numero_solicitud": "SN-123",
        "fecha_solicitud": "2024-05-14",
        "fecha_expedicion_acta": "2024-05-20",
        "elaboro": "Laura Niño",
        "jefe_juridica_nombre": "Ana Torres",
        **over,
    })


def payload_cesion(**over) -> CesionIn:
    return CesionIn(**{
        "contrato": CONTRATO,
        "cesionario": {
            "nombre": "Pedro", "apellidos": "Díaz López", "documento": "4040404040",
            "tipo_documento": "C.C.", "ciudad_documento": "Bogotá",
        },
        "fecha_cesion": "2024-06-25",
        "fecha_terminacion_cedente": "2024-06-24",
        "valor_desembolsado": "5000000",
        "valor_a_favor": "1000000",
        "plazo_cedente": "un (1) mes",
        "dias_pago_cedente": "quince (15) días",
        "plazo_cesionario": "dos (2) meses",
        "numero_oficio_supervisor": "OF-456",
        "fecha_oficio_supervisor": "2024-06-20",
        "numero_solicitud": "SN-123",
        "fecha_solicitud": "2024-06-18",
        "suspension_previa": SUSPENSION_PREVIA,
        "nuevo_considerando": "Que el cesionario acredita la experiencia exigida en los "
                              "estudios previos del contrato.",
        "fecha_expedicion_acta": "2024-06-25",
        "elaboro": "Laura Niño",
        "jefe_juridica_nombre": "Ana Torres",
        **over,
    })


def payload_terminacion(**over) -> TerminacionLiquidacionIn:
    return TerminacionLiquidacionIn(**{
        "contrato": CONTRATO,
        "fecha_terminacion_anticipada": "2024-06-30",
        "valor_desembolsado": "5000000",
        "saldo_contratista": "3000000",
        "fecha_certificacion": "2024-06-28",
        "numero_oficio_supervisor": "OF-456",
        "fecha_oficio_supervisor": "2024-06-20",
        "numero_oficio_ordenador": "OF-789",
        "fecha_oficio_ordenador": "2024-06-22",
        "fecha_efectos_legales": "2024-07-01",
        "fecha_expedicion_acta": "2024-06-30",
        "elaboro": "Laura Niño",
        "jefe_juridica_nombre": "Ana Torres",
        **over,
    })


EJEMPLOS = {
    "suspension": payload_suspension,
    "reinicio": payload_reinicio,
    "adicion_prorroga": payload_adicion_prorroga,
    "cesion": payload_cesion,
    "terminacion_liquidacion": payload_terminacion,
}


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    for tipo, construir in EJEMPLOS.items():
        acta = generar_acta(tipo, construir())
        destino = SALIDA / acta.filename
        destino.write_bytes(base64.b64decode(acta.file_base64))
        print(f"{destino.name:52} {acta.metadata.size_bytes:>8,} bytes")

    print(f"\n{len(list(SALIDA.glob('*.pdf')))} PDFs en {SALIDA}")


if __name__ == "__main__":
    main()
