"""Esquemas de entrada/salida del middleware.

Los nombres de campo siguen `parametros_actas.csv`. El front envía TODO lo necesario:
el servicio no consulta ÁGORA ni Financiera ni persiste nada.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

TipoActa = Literal["suspension", "reinicio", "adicion_prorroga", "cesion", "terminacion_liquidacion"]


class Persona(BaseModel):
    """Contratista, supervisor, ordenador del gasto o cesionario."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, examples=["Juan Pérez"])
    documento: str = Field(min_length=1, examples=["1010101010"])
    tipo_documento: str = Field(default="C.C.", examples=["C.C."])
    ciudad_documento: str = Field(default="Bogotá", examples=["Bogotá"])
    apellidos: str | None = Field(default=None, description="Solo se usa para el cesionario")
    rol: str | None = Field(default=None, examples=["Director"], description="Calidad/cargo")
    resolucion: str | None = Field(
        default=None,
        examples=["Resolución 262-2025"],
        description="Resolución de designación del ordenador del gasto",
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}".strip() if self.apellidos else self.nombre


class Contrato(BaseModel):
    """Datos maestros del contrato (ÁGORA + Financiera). Idénticos en las 5 actas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    numero_contrato: str = Field(min_length=1, examples=["1234"])
    vigencia: int = Field(ge=1990, le=2100, examples=[2024])
    tipo_contrato: str = Field(
        default="Contrato de Prestación de Servicios", examples=["Contrato de Prestación de Servicios"]
    )
    objeto_contrato: str = Field(min_length=1)
    valor_contrato: Decimal = Field(gt=0, examples=[10000000])
    plazo: str = Field(min_length=1, examples=["tres (3) meses"], description="Plazo en letras")
    plazo_dias: int | None = Field(default=None, ge=0, description="Plazo en días (tabla del reinicio)")
    fecha_suscripcion: date
    fecha_inicio: date
    cdp_numero: str | None = None
    rp_numero: str | None = None
    cdp_vigencia: int | None = Field(default=None, ge=1990, le=2100)
    unidad_ejecutora: int = Field(default=1, description="1 = Oficina de Contratación; otro = Ofex")
    contratista: Persona
    supervisor: Persona | None = None
    ordenador: Persona | None = None


# --- antecedentes del contrato (activan considerandos condicionales) -------------------


class SuspensionPrevia(BaseModel):
    fecha_acta: date
    fecha_inicio_suspension: date
    fecha_fin_suspension: date


class ReinicioPrevio(BaseModel):
    fecha_acta: date


class AdicionPrevia(BaseModel):
    fecha: date
    valor_adicion: Decimal = Field(ge=0)
    prorroga_meses: int = Field(default=0, ge=0)
    prorroga_dias: int = Field(default=0, ge=0)
    numero_solicitud: str | None = None
    fecha_solicitud: date | None = None
    fecha_oficio: date | None = None


class CesionPrevia(BaseModel):
    fecha_cesion: date
    cedente_nombre: str


# --- base común de las actas -----------------------------------------------------------


class _ActaBase(BaseModel):
    """Campos y validaciones compartidos por las 5 actas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ROLES_REQUERIDOS: ClassVar[tuple[str, ...]] = ()

    contrato: Contrato
    fecha_expedicion_acta: date = Field(default_factory=date.today)
    elaboro: str | None = Field(default=None, description="Quien proyecta el acta")
    jefe_juridica_nombre: str | None = Field(default=None, description="Quien aprueba el acta")
    nueva_clausula: str | None = Field(default=None, description="Cláusula adicional opcional")
    tamano_letra: int = Field(default=10, ge=1, le=50, description="Tamaño de letra del documento, en puntos")

    @model_validator(mode="after")
    def _validar_roles_requeridos(self):
        faltantes = [r for r in self.ROLES_REQUERIDOS if getattr(self.contrato, r) is None]
        if faltantes:
            raise ValueError(
                "esta acta requiere " + ", ".join(f"contrato.{r}" for r in faltantes)
            )
        return self


# --- SUSPENSIÓN (NP_SUS) ---------------------------------------------------------------


class SuspensionIn(_ActaBase):
    ROLES_REQUERIDOS = ("supervisor", "ordenador")

    fecha_inicio_suspension: date
    fecha_fin_suspension: date
    motivo: str = Field(default="________", description="Motivo de la suspensión")
    fecha_solicitud: date = Field(description="Fecha del escrito del contratista")
    numero_oficio_supervisor: str
    fecha_oficio_supervisor: date
    numero_oficio_ordenador: str
    fecha_oficio_ordenador: date
    ciudad_firma: str = "Bogotá D.C."

    @model_validator(mode="after")
    def _validar_periodo(self):
        if self.fecha_fin_suspension < self.fecha_inicio_suspension:
            raise ValueError("fecha_fin_suspension no puede ser anterior a fecha_inicio_suspension")
        if self.fecha_inicio_suspension < self.contrato.fecha_inicio:
            raise ValueError("la suspensión no puede iniciar antes del inicio del contrato")
        return self

    @computed_field
    @property
    def fecha_reinicio(self) -> date:
        """Día siguiente al fin de la suspensión."""
        return self.fecha_fin_suspension + timedelta(days=1)


# --- REINICIO (NP_REI) -----------------------------------------------------------------


class ReinicioIn(_ActaBase):
    ROLES_REQUERIDOS = ("supervisor",)

    suspension_previa: SuspensionPrevia
    fecha_reinicio: date | None = Field(
        default=None, description="Si se omite, se calcula como fin de suspensión + 1 día"
    )

    @model_validator(mode="after")
    def _calcular_reinicio(self):
        if self.fecha_reinicio is None:
            self.fecha_reinicio = self.suspension_previa.fecha_fin_suspension + timedelta(days=1)
        elif self.fecha_reinicio <= self.suspension_previa.fecha_inicio_suspension:
            raise ValueError("fecha_reinicio debe ser posterior al inicio de la suspensión")
        return self


# --- ADICIÓN Y PRÓRROGA (NP_ADPRO) -----------------------------------------------------


class AdicionProrrogaIn(_ActaBase):
    """Modificación por adición **y** prórroga: el acta siempre incluye ambas."""

    ROLES_REQUERIDOS = ("ordenador",)

    valor_adicion: Decimal = Field(gt=0, description="Valor a adicionar; obligatorio")
    prorroga_meses: int = Field(default=0, ge=0)
    prorroga_dias: int = Field(default=0, ge=0)
    nuevo_plazo_contrato: str | None = Field(
        default=None, description="Plazo total resultante en letras; si se omite se compone del original + prórroga"
    )
    numero_oficio: str
    fecha_oficio: date
    numero_solicitud: str
    fecha_solicitud: date
    cesion_previa: CesionPrevia | None = None

    @model_validator(mode="after")
    def _validar_modificacion(self):
        from services.config_institucional import LIMITE_ADICION_PORCENTAJE

        tope = self.contrato.valor_contrato * LIMITE_ADICION_PORCENTAJE / 100
        if self.valor_adicion > tope:
            raise ValueError(
                f"la adición ({self.valor_adicion}) supera el "
                f"{LIMITE_ADICION_PORCENTAJE}% del valor inicial (tope {tope})"
            )
        if not (self.prorroga_meses or self.prorroga_dias):
            raise ValueError(
                "la prórroga es obligatoria: indique prorroga_meses y/o prorroga_dias"
            )
        return self

    @computed_field
    @property
    def nuevo_valor_total(self) -> Decimal:
        return self.contrato.valor_contrato + self.valor_adicion


# --- CESIÓN (NP_CES) -------------------------------------------------------------------


class CesionIn(_ActaBase):
    ROLES_REQUERIDOS = ("supervisor", "ordenador")

    cesionario: Persona
    fecha_cesion: date
    fecha_terminacion_cedente: date
    valor_desembolsado: Decimal = Field(ge=0, description="Reconocido al cedente")
    valor_a_favor: Decimal = Field(ge=0, description="Saldo pendiente por pagar al cedente")
    plazo_cedente: str = Field(description="Plazo ejecutado por el cedente, en letras")
    dias_pago_cedente: str = Field(description="Plazo pendiente de pago al cedente, en letras")
    plazo_cesionario: str = Field(description="Plazo restante para el cesionario, en letras")
    numero_oficio_supervisor: str
    fecha_oficio_supervisor: date
    numero_solicitud: str | None = None
    fecha_solicitud: date
    suspension_previa: SuspensionPrevia | None = None
    reinicio_previo: ReinicioPrevio | None = None
    adicion_previa: AdicionPrevia | None = None
    nuevo_considerando: str | None = None

    @model_validator(mode="after")
    def _validar_liquidacion(self):
        if self.valor_desembolsado + self.valor_a_favor > self.contrato.valor_contrato:
            raise ValueError(
                "valor_desembolsado + valor_a_favor no puede superar el valor del contrato"
            )
        return self

    @computed_field
    @property
    def valor_cesionario(self) -> Decimal:
        """Valor a ceder = valor del contrato − (desembolsado + a favor del cedente)."""
        return self.contrato.valor_contrato - (self.valor_desembolsado + self.valor_a_favor)


# --- TERMINACIÓN ANTICIPADA Y LIQUIDACIÓN BILATERAL ------------------------------------


class TerminacionLiquidacionIn(_ActaBase):
    ROLES_REQUERIDOS = ("supervisor", "ordenador")

    fecha_terminacion_anticipada: date
    valor_desembolsado: Decimal = Field(ge=0)
    saldo_contratista: Decimal = Field(ge=0, description="Valor no ejecutado a favor del contratista")
    saldo_universidad: Decimal | None = Field(
        default=None, description="Si se omite: valor − desembolsado − saldo_contratista"
    )
    fecha_certificacion: date
    numero_oficio_supervisor: str
    fecha_oficio_supervisor: date
    numero_oficio_ordenador: str
    fecha_oficio_ordenador: date
    fecha_efectos_legales: date
    adicion_previa: AdicionPrevia | None = None

    @model_validator(mode="after")
    def _validar_balance(self):
        total = self.contrato.valor_contrato
        if self.saldo_universidad is None:
            self.saldo_universidad = total - self.valor_desembolsado - self.saldo_contratista
        if self.saldo_universidad < 0:
            raise ValueError("el balance no cuadra: desembolsado + saldo_contratista supera el valor del contrato")
        suma = self.valor_desembolsado + self.saldo_contratista + self.saldo_universidad
        if suma != total:
            raise ValueError(
                f"el balance no cuadra: desembolsado + saldos = {suma}, valor del contrato = {total}"
            )
        return self


# --- respuesta -------------------------------------------------------------------------


class ActaMetadata(BaseModel):
    tipo_acta: TipoActa
    codigo_formato: str
    version_formato: str
    numero_contrato: str
    vigencia: int
    fecha_generacion: str = Field(examples=["2026-08-03T10:00:00Z"])
    size_bytes: int


class ActaResponse(BaseModel):
    success: bool = True
    filename: str = Field(examples=["acta_suspension_contrato_1234_2024.pdf"])
    file_base64: str = Field(examples=["JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3Ro..."])
    metadata: ActaMetadata


PAYLOAD_POR_TIPO: dict[str, type[_ActaBase]] = {
    "suspension": SuspensionIn,
    "reinicio": ReinicioIn,
    "adicion_prorroga": AdicionProrrogaIn,
    "cesion": CesionIn,
    "terminacion_liquidacion": TerminacionLiquidacionIn,
}
