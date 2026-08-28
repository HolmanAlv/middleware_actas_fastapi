"""Contenido de las 5 actas: texto legal, considerandos, cláusulas y firmas.

El texto fijo se transcribió literalmente de la documentación de la carpeta
`documentacion_actas` (que a su vez viene de los controladores de `novedades_cliente`).
Los marcadores `{campo}` se resuelven contra un contexto ya formateado y escapado; un
campo ausente se imprime como `________`, igual que el cliente original.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone

from models.schemas import (
    ActaMetadata,
    ActaResponse,
    AdicionProrrogaIn,
    CesionIn,
    Persona,
    ReinicioIn,
    SuspensionIn,
    TerminacionLiquidacionIn,
)
from services import config_institucional as cfg
from services.formato import (
    ORDINALES,
    fecha_letras,
    moneda,
    moneda_letras,
    o_vacio,
    plazo_letras,
)
from services.pdf_builder import (
    Crudo,
    bloque_firmas,
    bloque_revision,
    cuerpo_sangria,
    ctx_escapado,
    espacio,
    p,
    render,
    seccion,
    t,
    tabla_datos,
    tabla_info,
    titulo,
    usar_tamano_letra,
)

CIERRE_ACUERDO = "Por lo anterior las partes acuerdan las siguientes <b>CLÁUSULAS:</b>"


# --- helpers ---------------------------------------------------------------------------


def _persona_ctx(prefijo: str, per: Persona | None) -> dict:
    if per is None:
        return {}
    return {
        f"{prefijo}_nombre": per.nombre_completo,
        f"{prefijo}_documento": per.documento,
        f"{prefijo}_tipo_doc": per.tipo_documento,
        f"{prefijo}_ciudad": per.ciudad_documento,
        f"{prefijo}_rol": o_vacio(per.rol),
        f"{prefijo}_resolucion": o_vacio(per.resolucion),
    }


def _ctx_comun(d) -> dict:
    k = d.contrato
    datos = {
        "numero_contrato": k.numero_contrato,
        "vigencia": k.vigencia,
        "tipo_contrato": k.tipo_contrato,
        "objeto_contrato": k.objeto_contrato,
        "valor": moneda(k.valor_contrato),
        "valor_letras": moneda_letras(k.valor_contrato),
        "plazo": k.plazo,
        "plazo_dias": o_vacio(k.plazo_dias),
        "fecha_suscripcion": fecha_letras(k.fecha_suscripcion),
        "fecha_inicio": fecha_letras(k.fecha_inicio),
        "cdp_numero": o_vacio(k.cdp_numero),
        "rp_numero": o_vacio(k.rp_numero),
        "cdp_vigencia": o_vacio(k.cdp_vigencia),
        "universidad": cfg.UNIVERSIDAD,
        "nit": cfg.NIT_UNIVERSIDAD,
        "acuerdo": cfg.ACUERDO_ESTATUTO,
        "resolucion_rectoria": cfg.RESOLUCION_RECTORIA,
        "fecha_expedicion_acta": fecha_letras(d.fecha_expedicion_acta),
        "elaboro": o_vacio(d.elaboro),
        "jefe_juridica_nombre": o_vacio(d.jefe_juridica_nombre),
    }
    datos |= _persona_ctx("contratista", k.contratista)
    datos |= _persona_ctx("supervisor", k.supervisor)
    datos |= _persona_ctx("ordenador", k.ordenador)
    return datos


def _considerandos(items: list[str], c) -> list:
    return [p(f"<b>{i}.</b> {t(texto, c)}") for i, texto in enumerate(items, 1)]


def _clausulas(items: list[tuple[str | None, str]], c, desde: int = 0) -> list:
    """Numera las cláusulas en orden; `desde` permite continuar una numeración ya iniciada."""
    salida = []
    for i, (encabezado, cuerpo) in enumerate(items, start=desde):
        prefijo = (
            f"<b>CLÁUSULA {ORDINALES[i]}: {encabezado}</b>"
            if encabezado
            else f"<b>CLÁUSULA {ORDINALES[i]}.</b>"
        )
        salida.append(p(f"{prefijo} {t(cuerpo, c)}"))
    return salida


def _revision(d, c) -> list:
    cargo_proyecto, cargo_aprobo = cfg.cargos_revision(d.contrato.unidad_ejecutora)
    aprobo = c["jefe_juridica_nombre"]
    if aprobo == "________" and d.contrato.unidad_ejecutora != 1:
        aprobo = c["ordenador_nombre"]
    return [espacio(10), bloque_revision(c["elaboro"], cargo_proyecto, aprobo, cargo_aprobo)]


# --- ACTA DE SUSPENSIÓN ----------------------------------------------------------------


def _suspension(d: SuspensionIn):
    c = ctx_escapado(
        _ctx_comun(d)
        | {
            "fecha_inicio_suspension": fecha_letras(d.fecha_inicio_suspension),
            "fecha_fin_suspension": fecha_letras(d.fecha_fin_suspension),
            "fecha_reinicio": fecha_letras(d.fecha_reinicio),
            "motivo": o_vacio(d.motivo),
            "fecha_solicitud": fecha_letras(d.fecha_solicitud),
            "numero_oficio_supervisor": o_vacio(d.numero_oficio_supervisor),
            "fecha_oficio_supervisor": fecha_letras(d.fecha_oficio_supervisor),
            "numero_oficio_ordenador": o_vacio(d.numero_oficio_ordenador),
            "fecha_oficio_ordenador": fecha_letras(d.fecha_oficio_ordenador),
            "ciudad_firma": o_vacio(d.ciudad_firma),
            "texto_clausula_19": Crudo(cfg.TEXTO_CLAUSULA_19_SUSPENSION),
        }
    )

    story = [
        titulo("ACTA DE SUSPENSIÓN"),
        tabla_info([
            ("CONTRATO", t("{tipo_contrato}", c)),
            ("No. CONTRATO", t("{numero_contrato}, suscrito el {fecha_suscripcion}", c)),
            ("CONTRATANTE", cfg.UNIVERSIDAD),
            ("CONTRATISTA", t(
                "{contratista_nombre}, mayor de edad, identificado(a) con {contratista_tipo_doc} "
                "No. {contratista_documento} Expedida en {contratista_ciudad}", c)),
            ("OBJETO", t("{objeto_contrato}", c)),
            ("VALOR", t("{valor_letras} MONEDA CORRIENTE (${valor} M/CTE)", c)),
            ("CDP", t("{cdp_numero}", c)),
            ("CRP", t("{rp_numero}", c)),
            ("FECHA DE INICIO", t("{fecha_inicio}", c)),
            ("PERIODO SUSPENSIÓN", t("Del día {fecha_inicio_suspension} al {fecha_fin_suspension}", c)),
            ("FECHA DE REINICIO", t("{fecha_reinicio}", c)),
        ]),
        espacio(12),
        p(t(
            "Entre los suscritos, de una parte, <b>{ordenador_nombre}</b>, identificado(a) con "
            "{ordenador_tipo_doc} No. {ordenador_documento} de {ordenador_ciudad} quien actúa en "
            "calidad de {ordenador_rol} y ordenador del gasto, de otra, <b>{contratista_nombre}</b> "
            "mayor de edad, identificado(a) con {contratista_tipo_doc} No. {contratista_documento} "
            "de {contratista_ciudad}, en su calidad de contratista, hemos acordado "
            "<b>SUSPENDER</b> el Contrato {tipo_contrato} No. {numero_contrato} del año {vigencia} "
            "durante el período comprendido entre el día {fecha_inicio_suspension} y el día "
            "{fecha_fin_suspension}, previas las siguientes consideraciones:", c)),
        espacio(),
    ]

    story += _considerandos([
        'Que entre la {universidad} y {contratista_nombre}, se suscribió el Contrato '
        '{tipo_contrato} No. {numero_contrato} del año {vigencia}, cuyo objeto es '
        '"{objeto_contrato}."',

        "Que el plazo de ejecución del contrato se estableció por {plazo} contados a partir de la "
        "suscripción de la correspondiente Acta de inicio, lo cual tuvo lugar el día {fecha_inicio}.",

        "Que la cláusula 19 - Suspensión del Contrato {tipo_contrato} No. {numero_contrato} del año "
        '{vigencia}, establece que <i>"{texto_clausula_19}"</i>.',

        "Que, mediante escrito de fecha {fecha_solicitud}, el Contratista {contratista_nombre}, "
        "solicita a {supervisor_nombre}, quien cumple la función de supervisor, la autorización "
        "para realizar la Suspensión del Contrato {tipo_contrato} No. {numero_contrato} de "
        "{vigencia} durante el período comprendido entre el día {fecha_inicio_suspension} y el día "
        "{fecha_fin_suspension}.<br/><br/><b>MOTIVO DE LA SUSPENSIÓN:</b> {motivo}",

        "Que mediante oficio No. {numero_oficio_supervisor} de fecha {fecha_oficio_supervisor}, el "
        "supervisor del contrato {tipo_contrato} No. {numero_contrato} del año {vigencia}, le "
        "comunicó a {ordenador_nombre} en calidad de Ordenador del Gasto del citado contrato, la "
        "autorización para suspender el mismo, durante el período comprendido entre el día "
        "{fecha_inicio_suspension} y el día {fecha_fin_suspension}.",

        "Que por medio del oficio No. {numero_oficio_ordenador} de fecha {fecha_oficio_ordenador}, "
        "recibido por la Oficina de Contratación, {ordenador_nombre}, como Ordenador del Gasto, "
        "solicitó la elaboración del acta de suspensión del contrato {tipo_contrato} No. "
        "{numero_contrato} del año {vigencia}, durante el período comprendido entre el día "
        "{fecha_inicio_suspension} y el día {fecha_fin_suspension}.",
    ], c)

    clausulas = [
        ("SUSPENDER",
         "el Contrato {tipo_contrato} No. {numero_contrato} del año {vigencia}, durante el periodo "
         "comprendido entre el día {fecha_inicio_suspension} y el día {fecha_fin_suspension}."),
        ("GARANTÍAS Y MECANISMO DE COBERTURA DE RIESGO -",
         "EL CONTRATISTA una vez se reinicie el contrato, deberá aportar una póliza de garantías "
         "donde se amplía el plazo de ejecución."),
        ("PUBLICACIÓN. -",
         "En virtud de lo dispuesto en el Estatuto de Contratación – {acuerdo} y las normas "
         "vigentes, se procederá a la publicación del presente documento en el SECOP II que "
         "administra la Agencia Nacional de Contratación Pública – Colombia Compra Eficiente."),
    ]
    if d.nueva_clausula:
        clausulas.append((None, ctx_escapado({"x": d.nueva_clausula})["x"]))

    story += [espacio(), seccion(CIERRE_ACUERDO), espacio()]
    story += _clausulas(clausulas, c)
    story += [
        espacio(12),
        p(t(
            "En constancia de lo consignado en el presente documento, se firma en la ciudad de "
            "{ciudad_firma}, el día {fecha_expedicion_acta}.", c)),
        bloque_firmas([
            (c["ordenador_nombre"], "Ordenador del Gasto"),
            (c["supervisor_nombre"], "Supervisor"),
            (c["contratista_nombre"], "Contratista"),
        ]),
    ]
    story += _revision(d, c)
    return story, ()


# --- ACTA DE REINICIO ------------------------------------------------------------------


def _reinicio(d: ReinicioIn):
    s = d.suspension_previa
    c = ctx_escapado(
        _ctx_comun(d)
        | {
            "fecha_acta_suspension": fecha_letras(s.fecha_acta),
            "fecha_inicio_suspension": fecha_letras(s.fecha_inicio_suspension),
            "fecha_fin_suspension": fecha_letras(s.fecha_fin_suspension),
            "fecha_reinicio": fecha_letras(d.fecha_reinicio),
            "texto_paragrafo_19": Crudo(cfg.TEXTO_PARAGRAFO_19_GARANTIA),
        }
    )

    story = [
        titulo("ACTA DE REINICIO"),
        tabla_info([
            ("CONTRATO", t("{tipo_contrato}", c)),
            ("No. CONTRATO", t("{numero_contrato}, suscrito el {fecha_suscripcion}", c)),
            ("CONTRATANTE", cfg.UNIVERSIDAD),
            ("CONTRATISTA", t(
                "{contratista_nombre}, mayor de edad, identificado(a) con {contratista_tipo_doc} "
                "No. {contratista_documento} Expedida en {contratista_ciudad}", c)),
            ("OBJETO", t("{objeto_contrato}", c)),
            ("VALOR", t("{valor_letras} MONEDA CORRIENTE (${valor} M/CTE)", c)),
            ("PLAZO", t("{plazo_dias} Días", c) if d.contrato.plazo_dias else t("{plazo}", c)),
            ("FECHA DE INICIO", t("{fecha_inicio}", c)),
            ("PERIODO SUSPENSIÓN", t("Del día {fecha_inicio_suspension} al {fecha_fin_suspension}", c)),
            ("FECHA DE REINICIO", t("{fecha_reinicio}", c)),
        ]),
        espacio(12),
        p(t(
            "Entre los suscritos, a saber, <b>{supervisor_nombre}</b>, identificado con "
            "{supervisor_tipo_doc} No. {supervisor_documento} de {supervisor_ciudad}, en su calidad "
            "de {supervisor_rol}, y <b>{contratista_nombre}</b>, identificado con "
            "{contratista_tipo_doc} No. {contratista_documento} de {contratista_ciudad}, en su "
            "calidad de contratista, se ha determinado <b>REINICIAR</b> el Contrato de "
            "{tipo_contrato} No. {numero_contrato} del año {vigencia}, previas las siguientes "
            "consideraciones:", c)),
        espacio(),
    ]

    story += _considerandos([
        'Que entre la {universidad} y {contratista_nombre}, se suscribió el CPS No. '
        '{numero_contrato} del año {vigencia}, cuyo objeto es "{objeto_contrato}".',

        "Que mediante acta de fecha {fecha_acta_suspension}, se suspendió el Contrato No. "
        "{numero_contrato} del año {vigencia}, durante el periodo comprendido entre el día "
        "{fecha_inicio_suspension} y el día {fecha_fin_suspension} del año {vigencia}.",

        "Que de conformidad con el parágrafo de la cláusula 19 - Suspensión. del CPS No. "
        '{numero_contrato} del año {vigencia}, la cual establece que: "{texto_paragrafo_19}", se '
        "hace necesario que el contratista amplíe las garantías requeridas con la suscripción del "
        "contrato por el término de duración de la suspensión.",
    ], c)

    clausulas = [
        ("REINICIAR.",
         "El Contrato No. {numero_contrato} del año {vigencia} suscrito con {contratista_nombre}, "
         "a partir del día {fecha_reinicio}."),
        ("GARANTÍA.",
         "<b>EL CONTRATISTA</b> se compromete a modificar la Póliza de Cumplimiento expedida en "
         "virtud del Contrato {tipo_contrato} No. {numero_contrato} del año {vigencia}, de "
         "conformidad con la suscripción del presente documento."),
        ("PUBLICACIÓN.",
         "En virtud de lo dispuesto en el Estatuto de Contratación – {acuerdo} y en concordancia "
         "con la normatividad vigente, por medio de la cual se reglamenta el uso del SECOP II en "
         "la Universidad, se procederá a la publicación del presente documento de reinicio en el "
         "SECOP II que administra la Agencia Nacional de Contratación Pública – Colombia Compra "
         "Eficiente."),
    ]
    if d.nueva_clausula:
        clausulas.append((None, ctx_escapado({"x": d.nueva_clausula})["x"]))

    fecha = d.fecha_expedicion_acta
    story += [espacio(), seccion(CIERRE_ACUERDO), espacio()]
    story += _clausulas(clausulas, c)
    story += [
        espacio(12),
        p(f"Para constancia, firman las partes a los {fecha.day} días del mes "
          f"{fecha_letras(fecha).split(' de ')[1]} del año {fecha.year}."),
        bloque_firmas([
            (c["supervisor_nombre"], t("C.C. {supervisor_documento} – {supervisor_rol}", c)),
            (c["contratista_nombre"], t("C.C. {contratista_documento} – Contratista", c)),
        ]),
        espacio(10),
        tabla_datos(["Acción", "Nombre", "Cargo"], [
            ["Elaboró", c["elaboro"], "Abogado Oficina de Contratación"],
            ["Revisó y Aprobó", c["jefe_juridica_nombre"], "Jefe Oficina de Contratación"],
        ]),
    ]
    return story, ()


# --- MODIFICACIÓN: ADICIÓN Y/O PRÓRROGA ------------------------------------------------


def _adicion_prorroga(d: AdicionProrrogaIn):
    prorroga_txt = plazo_letras(d.prorroga_meses, d.prorroga_dias)
    extra = {
        "valor_adicion": moneda(d.valor_adicion),
        "valor_adicion_letras": moneda_letras(d.valor_adicion),
        "nuevo_valor_total": moneda(d.nuevo_valor_total),
        "nuevo_valor_total_letras": moneda_letras(d.nuevo_valor_total),
        "tiempo_prorroga_letras": prorroga_txt,
        "nuevo_plazo_contrato": d.nuevo_plazo_contrato or f"{d.contrato.plazo} más {prorroga_txt}",
        "numero_oficio": o_vacio(d.numero_oficio),
        "fecha_oficio": fecha_letras(d.fecha_oficio),
        "numero_solicitud": o_vacio(d.numero_solicitud),
        "fecha_solicitud": fecha_letras(d.fecha_solicitud),
        "texto_clausula_16": Crudo(cfg.TEXTO_CLAUSULA_16_MODIFICACION),
        "circular": cfg.CIRCULAR_COLOMBIA_COMPRA,
        "limite_adicion": f"{cfg.LIMITE_ADICION_PORCENTAJE:g}",
    }
    if d.cesion_previa:
        extra |= {
            "fecha_cesion": fecha_letras(d.cesion_previa.fecha_cesion),
            "cedente_nombre": d.cesion_previa.cedente_nombre,
        }
    c = ctx_escapado(_ctx_comun(d) | extra)

    story = [
        titulo(t(
            "MODIFICACIÓN: PRÓRROGA Y ADICIÓN No. 1 AL {tipo_contrato} No. {numero_contrato} DE "
            "{vigencia} CELEBRADO ENTRE LA UNIVERSIDAD DISTRITAL FRANCISCO JOSÉ DE CALDAS Y "
            "{contratista_nombre}", c).upper()),
        p(t(
            "Entre los suscritos, de una parte, <b>{ordenador_nombre}</b>, mayor de edad, "
            "vecino(a) de esta ciudad, identificado(a) con {ordenador_tipo_doc} No. "
            "{ordenador_documento} expedida en {ordenador_ciudad}, quien actúa en calidad de "
            "{ordenador_rol}, según {ordenador_resolucion}, debidamente autorizado para contratar, "
            "según Acuerdo No. 003 de 2015 del Consejo Superior Universitario, quien en lo sucesivo "
            "se denominará <b>LA UNIVERSIDAD</b>, con NIT {nit}, ente universitario autónomo, de "
            "conformidad con la Ley 30 de 1992, y, de otra, <b>{contratista_nombre}</b>, "
            "identificado(a) con {contratista_tipo_doc} No. {contratista_documento} expedida en "
            "{contratista_ciudad}, y quien para los efectos del presente documento, se denominará "
            "<b>EL CONTRATISTA</b>, acordamos <b>prorrogar el plazo y adicionar el valor</b> del "
            "{tipo_contrato} No. "
            "{numero_contrato} de {vigencia}, teniendo en cuenta los siguientes documentos y "
            "consideraciones:", c)),
        espacio(),
    ]

    considerandos = [
        "El día {fecha_suscripcion}, LA UNIVERSIDAD y EL CONTRATISTA suscribieron el "
        '{tipo_contrato} No. {numero_contrato} de {vigencia}, cuyo objeto es "{objeto_contrato}".',

        "Que el plazo de ejecución del contrato se estableció por {plazo}, contados a partir de la "
        "suscripción de la correspondiente Acta de inicio, lo cual tuvo lugar el día {fecha_inicio}.",

        "Que se pactó como valor del citado contrato, la suma de {valor_letras} MONEDA CORRIENTE "
        "(${valor} M/Cte.).",

        "Que la CLÁUSULA DIECISEIS del {tipo_contrato} No. {numero_contrato} de {vigencia}, "
        'establece que: "{texto_clausula_16}".',

        "Que mediante oficio {numero_oficio} recibido por la Oficina de Contratación el día "
        "{fecha_oficio}, el {ordenador_rol}, solicitó la adición y prórroga del {tipo_contrato} "
        "No. {numero_contrato} de {vigencia}, en su orden, por un valor de {valor_adicion_letras} "
        "MONEDA CORRIENTE (${valor_adicion} M/Cte.), y prórroga de {tiempo_prorroga_letras}, cuya "
        "justificación se encuentra descrita en la Solicitud de Necesidad No. {numero_solicitud} "
        "del día {fecha_solicitud}.",

        "Que la presente adición no supera el {limite_adicion}% del valor inicialmente pactado, "
        "por lo que la solicitud se ajusta a lo consagrado en el inciso 2º del artículo 86 de la "
        "Resolución de Rectoría 262 de 2015 (Procedimiento para Adición, Prórroga o Modificación "
        "del Contrato), resultando procedente suscribir el presente documento.",

        "Que quienes suscriben el presente documento son plenamente capaces para hacerlo y "
        "obligarse, además de que la Oficina de Contratación de LA UNIVERSIDAD verificó la "
        "ausencia de antecedentes disciplinarios, judiciales y fiscales.",

        "Que se cuenta con disponibilidad presupuestal para atender la presente adición, como se "
        "desprende del Certificado de Disponibilidad Presupuestal No. {cdp_numero} de "
        "{cdp_vigencia}, expedido por la Unidad de Presupuesto.",

        "Que el acto aquí planteado es jurídicamente viable, de acuerdo con lo establecido en las "
        "normas civiles y comerciales pertinentes, y, en especial, en el Estatuto de Contratación "
        "de la Universidad Distrital Francisco José de Caldas y demás normas reglamentarias "
        "pertinentes y vigentes.",
    ]
    if d.cesion_previa:
        considerandos.append(
            "Que, mediante Acta de Cesión con efectos legales a partir del día {fecha_cesion}, "
            "el(la) contratista {cedente_nombre} cede el {tipo_contrato} No. {numero_contrato} de "
            "{vigencia}, en todas las obligaciones, términos y condiciones pactadas en el contrato "
            "a {contratista_nombre}, quien ha venido ejecutando el desarrollo de actividades hasta "
            "el momento."
        )
    story += _considerandos(considerandos, c)

    clausulas: list[tuple[str | None, str]] = [
        ("ADICIONAR",
         "al valor del {tipo_contrato} No. {numero_contrato} de {vigencia}, la suma de "
         "{valor_adicion_letras} MONEDA CORRIENTE (${valor_adicion} M/Cte.)."),
        (None,
         "Como consecuencia de lo anterior, MODIFICAR LA CLAUSULA TERCERA del citado contrato, "
         'la cual quedará así: "...El valor del presente contrato corresponde a la suma de '
         "{nuevo_valor_total_letras} MONEDA CORRIENTE (${nuevo_valor_total} M/Cte.), incluido "
         'IVA, así como todos los impuestos y retenciones legalmente establecidos…".'),
        ("PRORROGAR",
         "el plazo de ejecución del {tipo_contrato} No. {numero_contrato} de {vigencia} en "
         "{tiempo_prorroga_letras}."),
        (None,
         "Como consecuencia de lo anterior, MODIFICAR la CLAUSULA SEXTA del citado contrato, "
         'la cual quedará así: "...El plazo de ejecución del contrato será de '
         '{nuevo_plazo_contrato}, contados a partir de los requisitos de ejecución…".'),
        (None,
         "Las cláusulas y condiciones no modificadas por el presente instrumento continúan "
         "vigentes en los términos del contrato primigenio."),
        (None,
         "La presente adición y prórroga requiere para su perfeccionamiento y legalización, la "
         "suscripción de la misma por las partes, la actualización y aprobación de la garantía "
         "única y la expedición del Registro Presupuestal."),
        (None,
         "De conformidad con lo establecido en la {circular}, proferida por Colombia Compra "
         "Eficiente, y en atención a lo establecido en el {acuerdo} -Estatuto de Contratación de "
         "la Universidad Distrital- la presente Adición y Prórroga se deberá publicar en el portal "
         "SECOP II, una vez esté suscrita por las partes, y sea devuelta a la Oficina de "
         "Contratación para el archivo correspondiente."),
    ]
    if d.nueva_clausula:
        clausulas.append((None, ctx_escapado({"x": d.nueva_clausula})["x"]))

    story += [espacio(), seccion("En consecuencia de lo anterior, las partes acuerdan:"), espacio()]
    story += _clausulas(clausulas, c)
    story += [
        espacio(12),
        p(t(
            "En constancia de lo consignado en el presente documento, se firma en "
            f"{cfg.CIUDAD_FIRMA_DEFECTO}, el día {{fecha_expedicion_acta}}.", c)),
        bloque_firmas([
            (c["ordenador_nombre"], t("{ordenador_rol} – LA UNIVERSIDAD", c)),
            (c["contratista_nombre"], "EL CONTRATISTA"),
        ]),
    ]
    story += _revision(d, c)
    return story, cfg.PIE_OFICINA_CONTRATACION


# --- ACTA DE CESIÓN --------------------------------------------------------------------


def _cesion(d: CesionIn):
    extra = {
        "fecha_cesion": fecha_letras(d.fecha_cesion),
        "fecha_terminacion_cedente": fecha_letras(d.fecha_terminacion_cedente),
        "valor_desembolsado": moneda(d.valor_desembolsado),
        "valor_desembolsado_letras": moneda_letras(d.valor_desembolsado),
        "valor_a_favor": moneda(d.valor_a_favor),
        "valor_a_favor_letras": moneda_letras(d.valor_a_favor),
        "valor_cesionario": moneda(d.valor_cesionario),
        "valor_cesionario_letras": moneda_letras(d.valor_cesionario),
        "plazo_cedente_letras": o_vacio(d.plazo_cedente),
        "dias_pago_cedente_letras": o_vacio(d.dias_pago_cedente),
        "plazo_cesionario": o_vacio(d.plazo_cesionario),
        "plazo_cesionario_letras": o_vacio(d.plazo_cesionario),
        "numero_oficio_supervisor": o_vacio(d.numero_oficio_supervisor),
        "fecha_oficio_supervisor": fecha_letras(d.fecha_oficio_supervisor),
        "numero_solicitud": o_vacio(d.numero_solicitud),
        "fecha_solicitud": fecha_letras(d.fecha_solicitud),
        "texto_clausula_15": Crudo(cfg.TEXTO_CLAUSULA_15_CESION),
    } | _persona_ctx("cesionario", d.cesionario)
    c = ctx_escapado(_ctx_comun(d) | extra)

    story = [
        titulo("ACTA DE CESIÓN"),
        tabla_info([
            ("CONTRATO", t("{tipo_contrato}", c)),
            ("No. CONTRATO", t("{numero_contrato}, suscrito el {fecha_suscripcion}", c)),
            ("PLAZO", t("{plazo}", c)),
            ("FECHA DE SUSCRIPCIÓN", t("{fecha_suscripcion}", c)),
            ("FECHA DE INICIO", t("{fecha_inicio}", c)),
            ("ORDENADOR DEL GASTO", t(
                "{ordenador_nombre}, mayor de edad, identificado(a) con {ordenador_tipo_doc} No. "
                "{ordenador_documento} expedida en {ordenador_ciudad}", c)),
            ("SUPERVISOR", t(
                "{supervisor_nombre}, mayor de edad, identificado(a) con {supervisor_tipo_doc} No. "
                "{supervisor_documento} expedida en {supervisor_ciudad}", c)),
            ("CDP", t("{cdp_numero}", c)),
            ("CRP", t("{rp_numero}", c)),
            ("CEDENTE", t(
                "{contratista_nombre}, mayor de edad, identificado(a) con {contratista_tipo_doc} "
                "No. {contratista_documento} expedida en {contratista_ciudad}", c)),
            ("CESIONARIO", t(
                "{cesionario_nombre}, mayor de edad, identificado(a) con {cesionario_tipo_doc} No. "
                "{cesionario_documento} expedida en {cesionario_ciudad}", c)),
        ]),
        espacio(12),
        p(t(
            "Entre los suscritos a saber, <b>{ordenador_nombre}</b>, mayor de edad, "
            "identificado(a) con {ordenador_tipo_doc} No. {ordenador_documento} de "
            "{ordenador_ciudad}, quien actúa en calidad de {ordenador_rol} según "
            "{ordenador_resolucion}, debidamente autorizado para contratar según Acuerdo Nro. 03 "
            "de 2015 (Estatuto de Contratación de la Universidad Distrital Francisco José de "
            "Caldas), {resolucion_rectoria}, y, de otra <b>{contratista_nombre}</b>, mayor de "
            "edad, e identificado(a) con {contratista_tipo_doc} No. {contratista_documento} de "
            "{contratista_ciudad} quien actúa en calidad de <b>CONTRATISTA CEDENTE</b>, y "
            "<b>{cesionario_nombre}</b> con {cesionario_tipo_doc} No. {cesionario_documento}, como "
            '<b>CONTRATISTA CESIONARIO</b>, acordamos suscribir la presente "acta de cesión de '
            'contrato", previas las siguientes consideraciones:', c)),
        espacio(),
    ]

    considerandos = [
        "Que entre la {universidad} y el señor(a) {contratista_nombre}, se suscribió el "
        '{tipo_contrato} No. {numero_contrato} de {vigencia}, cuyo objeto es "{objeto_contrato}".',

        "Que la cláusula 3 del {tipo_contrato} No. {numero_contrato} de {vigencia}, establece como "
        'valor del contrato "(...) El valor del presente Contrato corresponde a la suma de '
        "{valor_letras} MONEDA CORRIENTE (${valor} M/CTE) incluido IVA, así como todos los "
        'impuestos y retenciones legalmente (...)".',

        "Que la cláusula 6 del {tipo_contrato} No. {numero_contrato} de {vigencia}, establece como "
        'plazo del contrato "El plazo de ejecución del Contrato es {plazo}, contados a partir del '
        'cumplimiento de los requisitos de ejecución", esto es, según el acta de inicio el '
        "{fecha_inicio}.",

        "Que la cláusula 15 del {tipo_contrato} No. {numero_contrato} de {vigencia}, establece que "
        '"{texto_clausula_15}".',
    ]
    if d.suspension_previa:
        c["fecha_acta_suspension_previa"] = fecha_letras(d.suspension_previa.fecha_acta)
        c["fecha_inicio_suspension"] = fecha_letras(d.suspension_previa.fecha_inicio_suspension)
        c["fecha_fin_suspension"] = fecha_letras(d.suspension_previa.fecha_fin_suspension)
        considerandos.append(
            "Que, mediante acta con fecha de suscripción del {fecha_acta_suspension_previa}, se "
            "suspendió el {tipo_contrato} No. {numero_contrato} de {vigencia} durante el periodo "
            "comprendido entre el {fecha_inicio_suspension} y el día {fecha_fin_suspension}."
        )
    if d.reinicio_previo:
        c["fecha_acta_reinicio_previo"] = fecha_letras(d.reinicio_previo.fecha_acta)
        considerandos.append(
            "Que, mediante acta con fecha de suscripción del {fecha_acta_reinicio_previo}, se "
            "reinició el {tipo_contrato} No. {numero_contrato} de {vigencia}."
        )
    if d.adicion_previa:
        a = d.adicion_previa
        c |= ctx_escapado({
            "fecha_prorroga": fecha_letras(a.fecha),
            "valor_adicion": moneda(a.valor_adicion),
            "valor_adicion_letras": moneda_letras(a.valor_adicion),
            "plazo_prorroga_letras": plazo_letras(a.prorroga_meses, a.prorroga_dias),
            "fecha_oficio_adicion": fecha_letras(a.fecha_oficio),
            "numero_solicitud_adicion": o_vacio(a.numero_solicitud),
            "fecha_solicitud_adicion": fecha_letras(a.fecha_solicitud),
        })
        considerandos.append(
            "Que el día {fecha_prorroga}, se realizó la modificación en adición y prórroga, al "
            "{tipo_contrato} No. {numero_contrato} de {vigencia}, en su orden por la suma de "
            "{valor_adicion_letras} MONEDA CORRIENTE (${valor_adicion} M/CTE), y prórroga en "
            "tiempo por {plazo_prorroga_letras}, en atención a la solicitud recibida por correo "
            "electrónico, de fecha {fecha_oficio_adicion}, por medio de la cual, el "
            "{ordenador_rol}, solicitó la citada modificación; cuya justificación se encuentra "
            "descrita en la solicitud de necesidad No. {numero_solicitud_adicion} del "
            "{fecha_solicitud_adicion}, con respaldo del CDP {cdp_numero} de {cdp_vigencia}."
        )
    considerandos += [
        "Que, mediante escrito de fecha {fecha_solicitud}, el(la) Contratista "
        "{contratista_nombre} (cedente), solicita a {supervisor_nombre} quien cumple la función de "
        "supervisor, la autorización para realizar la Cesión del {tipo_contrato} a partir del día "
        "{fecha_cesion}.",

        "Que mediante oficio {numero_oficio_supervisor} de fecha {fecha_oficio_supervisor}, el "
        "supervisor del {tipo_contrato} No. {numero_contrato} de {vigencia}, le comunicó al "
        "señor(a) {ordenador_nombre} en calidad de Ordenador del Gasto del citado contrato, la "
        "autorización para ceder el mismo, a partir del día {fecha_cesion} a {cesionario_nombre} "
        "quien cumple con las calidades y competencias para desarrollar el objeto del Contrato.",

        "Que por medio del oficio {numero_oficio_supervisor} de fecha {fecha_oficio_supervisor}, "
        "recibido por la Oficina de Contratación, {ordenador_nombre}, como Ordenador del Gasto, "
        "solicitó la elaboración del acta de cesión del {tipo_contrato} No. {numero_contrato} de "
        "{vigencia} a partir del día {fecha_cesion}, a nombre de {cesionario_nombre} (CESIONARIO), "
        "y aportó un estado financiero expedido por la Unidad de Presupuesto, en donde informa lo "
        "siguiente:",
    ]
    if d.nuevo_considerando:
        considerandos.append(ctx_escapado({"x": d.nuevo_considerando})["x"])

    # El detalle financiero va inmediatamente después del considerando 10.
    flow_considerandos = _considerandos(considerandos, c)
    detalle = [
        p(t(
            "– Por los servicios prestados por el señor(a) {contratista_nombre} (CONTRATISTA "
            "CEDENTE), hasta el día {fecha_terminacion_cedente}, se reconoció un valor total de "
            "{valor_desembolsado_letras} MONEDA CORRIENTE (${valor_desembolsado} M/CTE), y ejecutó "
            "del contrato un plazo de {plazo_cedente_letras}.", c), cuerpo_sangria()),
        p(t(
            "– Existe un valor pendiente por cancelar al señor(a) {contratista_nombre} "
            "<b>(CEDENTE)</b>, por valor de {valor_a_favor_letras} MONEDA CORRIENTE "
            "(${valor_a_favor} M/CTE), correspondiente al plazo ejecutado de "
            "{dias_pago_cedente_letras}.", c), cuerpo_sangria()),
        p(t(
            "– La suma a ceder al señor(a) {cesionario_nombre} <b>(CESIONARIO)</b> es de "
            "{valor_cesionario_letras} MONEDA CORRIENTE (${valor_cesionario} M/CTE), por un plazo "
            "de {plazo_cesionario_letras}.", c), cuerpo_sangria()),
    ]
    corte = len(considerandos) - (1 if d.nuevo_considerando else 0)
    story += flow_considerandos[:corte] + detalle + flow_considerandos[corte:]

    clausulas = [
        ("EL CEDENTE.",
         "{contratista_nombre} cede el {tipo_contrato} No. {numero_contrato}, suscrito el día "
         "{fecha_suscripcion}, a nombre de {cesionario_nombre} <b>(CESIONARIO)</b>, en todas las "
         "obligaciones, términos y condiciones pactadas en el contrato, con efectos legales a "
         "partir del día {fecha_cesion}."),
        (None,
         "El valor a ceder del contrato corresponde a la suma de {valor_cesionario_letras} MONEDA "
         "CORRIENTE (${valor_cesionario} M/CTE)."),
        ("EL CESIONARIO",
         "acepta todos los derechos y obligaciones que se desprenden del {tipo_contrato} No. "
         "{numero_contrato} de {vigencia} a partir de la fecha {fecha_cesion} por un plazo de "
         "{plazo_cesionario}."),
        ("GARANTÍA.",
         "<b>EL CESIONARIO</b> se compromete a modificar la Póliza de Cumplimiento con sus "
         "amparos, expedida en virtud del {tipo_contrato} No. {numero_contrato} de {vigencia} o a "
         "expedir una nueva de conformidad con la suscripción del presente documento."),
        ("PUBLICACIÓN.",
         "En virtud de lo dispuesto en el Estatuto de Contratación – {acuerdo} y las normas "
         "vigentes, se procederá a la publicación del presente documento de cesión en el SECOP II "
         "que administra la Agencia Nacional de Contratación Pública – Colombia Compra Eficiente."),
    ]
    if d.nueva_clausula:
        clausulas.append((None, ctx_escapado({"x": d.nueva_clausula})["x"]))

    story += [espacio(), seccion(CIERRE_ACUERDO), espacio()]
    story += _clausulas(clausulas, c)
    story += [
        espacio(12),
        p(t(
            "En constancia de lo consignado en el presente documento, se firma en "
            f"{cfg.CIUDAD_FIRMA_DEFECTO}, el día {{fecha_expedicion_acta}}.", c)),
        bloque_firmas([
            (c["ordenador_nombre"], "Ordenador del Gasto"),
            (c["supervisor_nombre"], "Supervisor"),
            (c["contratista_nombre"], "Cedente"),
            (c["cesionario_nombre"], "Cesionario"),
        ]),
    ]
    story += _revision(d, c)
    return story, ()


# --- ACTA DE TERMINACIÓN ANTICIPADA Y LIQUIDACIÓN BILATERAL ----------------------------


def _terminacion_liquidacion(d: TerminacionLiquidacionIn):
    extra = {
        "fecha_terminacion_anticipada": fecha_letras(d.fecha_terminacion_anticipada),
        "valor_desembolsado": moneda(d.valor_desembolsado),
        "valor_desembolsado_letras": moneda_letras(d.valor_desembolsado),
        "saldo_contratista": moneda(d.saldo_contratista),
        "saldo_contratista_letras": moneda_letras(d.saldo_contratista),
        "saldo_universidad": moneda(d.saldo_universidad),
        "saldo_universidad_letras": moneda_letras(d.saldo_universidad),
        "fecha_certificacion": fecha_letras(d.fecha_certificacion),
        "numero_oficio_supervisor": o_vacio(d.numero_oficio_supervisor),
        "fecha_oficio_supervisor": fecha_letras(d.fecha_oficio_supervisor),
        "numero_oficio_ordenador": o_vacio(d.numero_oficio_ordenador),
        "fecha_oficio_ordenador": fecha_letras(d.fecha_oficio_ordenador),
        "fecha_efectos_legales": fecha_letras(d.fecha_efectos_legales),
        "texto_clausula_17": Crudo(cfg.TEXTO_CLAUSULA_17_TERMINACION),
    }
    c = ctx_escapado(_ctx_comun(d) | extra)

    story = [
        titulo("ACTA DE TERMINACIÓN Y LIQUIDACIÓN BILATERAL"),
        tabla_info([
            ("CONTRATO", t("{tipo_contrato}", c)),
            ("CONTRATO No.", t("{numero_contrato}, suscrito el {fecha_suscripcion}", c)),
            ("CONTRATANTE", cfg.UNIVERSIDAD),
            ("CONTRATISTA", t(
                "{contratista_nombre}, mayor de edad, identificado(a) con {contratista_tipo_doc} "
                "No. {contratista_documento} Expedida en {contratista_ciudad}", c)),
            ("SUPERVISOR", t(
                "{supervisor_nombre}, mayor de edad, identificado(a) con {supervisor_tipo_doc} No. "
                "{supervisor_documento} Expedida en {supervisor_ciudad}", c)),
            ("PLAZO", t("{plazo}", c)),
            ("VALOR", t("{valor_letras} MONEDA CORRIENTE (${valor} M/CTE)", c)),
            ("CDP", t("{cdp_numero}", c)),
            ("CRP", t("{rp_numero}", c)),
            ("FECHA DE INICIO", t("{fecha_inicio}", c)),
        ]),
        espacio(12),
        p(t(
            "Entre los suscritos a saber, <b>{ordenador_nombre}</b>, mayor de edad, "
            "identificado(a) con {ordenador_tipo_doc} No. {ordenador_documento} de "
            "{ordenador_ciudad} quien actúa en calidad de {ordenador_rol} según "
            "{ordenador_resolucion} y ordenador del gasto, y por la otra "
            "<b>{contratista_nombre}</b>, mayor de edad, e identificado(a) con "
            "{contratista_tipo_doc} No. {contratista_documento} de {contratista_ciudad} quien "
            "actúa en calidad de contratista, hemos convenido en <b>TERMINAR ANTICIPADAMENTE Y POR "
            "MUTUO ACUERDO</b> y en consecuencia, <b>LIQUIDAR BILATERALMENTE</b> el "
            "{tipo_contrato} No. {numero_contrato} del año {vigencia} suscrito el día "
            "{fecha_suscripcion}, previas las siguientes <b>CONSIDERACIONES:</b>", c)),
        espacio(),
    ]

    considerandos = [
        "El día {fecha_suscripcion}, LA UNIVERSIDAD y EL CONTRATISTA suscribieron el "
        '{tipo_contrato} No. {numero_contrato} de {vigencia}, cuyo objeto es: "{objeto_contrato}".',

        "Que el plazo de ejecución del contrato se estableció por {plazo} contados a partir de la "
        "suscripción de la correspondiente Acta de inicio, lo cual tuvo lugar el día {fecha_inicio}.",

        "Que se pactó como valor del citado contrato, la suma de {valor_letras} MONEDA CORRIENTE "
        "(${valor} M/Cte.).",

        "Que la cláusula 17 del {tipo_contrato} No. {numero_contrato} de {vigencia}, establece que "
        '<b>"{texto_clausula_17}"</b>.',

        "Que el contratista mediante oficio de fecha {fecha_oficio_supervisor}, solicita la "
        "Terminación Anticipada y Liquidación Bilateral del {tipo_contrato} No. {numero_contrato} "
        "de {vigencia} al supervisor a partir del día {fecha_terminacion_anticipada}.",

        "Que según certificación de fecha {fecha_certificacion}, expedida por el Líder de la Unidad "
        "de Presupuesto, el {tipo_contrato} No. {numero_contrato} de {vigencia} presenta un saldo a "
        "la fecha de {saldo_contratista_letras} MONEDA CORRIENTE (${saldo_contratista} M/CTE).",

        "Que mediante oficio No. {numero_oficio_supervisor} de fecha {fecha_oficio_supervisor} el "
        "supervisor del {tipo_contrato} No. {numero_contrato} de {vigencia}, le comunicó a "
        "{ordenador_nombre} en calidad de Ordenador del Gasto, la autorización para la terminación "
        "anticipada del mismo, a partir del {fecha_terminacion_anticipada}.",

        "Que por medio del oficio No. {numero_oficio_ordenador} de fecha {fecha_oficio_ordenador}, "
        "recibido por la Oficina de Contratación, {ordenador_nombre} como Ordenador del Gasto, "
        "solicitó la elaboración del acta de terminación anticipada y liquidación bilateral del "
        "{tipo_contrato} No. {numero_contrato} de {vigencia} a partir del "
        "{fecha_terminacion_anticipada}.",
    ]
    if d.adicion_previa:
        a = d.adicion_previa
        c |= ctx_escapado({
            "fecha_prorroga": fecha_letras(a.fecha),
            "valor_adicion_letras": moneda_letras(a.valor_adicion),
            "valor_adicion": moneda(a.valor_adicion),
            "plazo_prorroga_letras": plazo_letras(a.prorroga_meses, a.prorroga_dias),
        })
        considerandos.append(
            "Que el día {fecha_prorroga} se realizó la modificación en adición y prórroga al "
            "{tipo_contrato} No. {numero_contrato} de {vigencia}, en su orden por la suma de "
            "{valor_adicion_letras} MONEDA CORRIENTE (${valor_adicion} M/CTE), y prórroga en "
            "tiempo por {plazo_prorroga_letras}."
        )
    story += _considerandos(considerandos, c)

    story += [espacio(), seccion(CIERRE_ACUERDO), espacio()]
    story += [
        p(t(
            "<b>CLÁUSULA PRIMERA: TERMINAR DE MANERA ANTICIPADA Y LIQUIDAR BILATERALMENTE</b> el "
            "contrato No. {numero_contrato} de {vigencia}, a partir del "
            "{fecha_terminacion_anticipada}, de la siguiente manera:", c)),
        tabla_datos(["Concepto", "Valor"], [
            ["Valor del contrato", t("${valor}", c)],
            ["Valor desembolsado", t("${valor_desembolsado}", c)],
            ["Saldo a favor del contratista", t("${saldo_contratista}", c)],
            ["Saldo a favor de la Universidad", t("${saldo_universidad}", c)],
        ]),
        espacio(),
    ]

    # La CLÁUSULA PRIMERA ya se imprimió junto con su tabla de balance; seguimos en la SEGUNDA.
    clausulas: list[tuple[str | None, str]] = [
        (None,
         "Teniendo en cuenta que el Contratista ejecutó los servicios hasta el día "
         "{fecha_terminacion_anticipada}, queda un saldo pendiente a su favor, por la suma de "
         "{saldo_contratista_letras} <b>M/CTE (${saldo_contratista} M/CTE)</b>, en atención a que "
         "es un valor no ejecutado en el contrato."),
        ("ORDENAR",
         "liberar el saldo a favor de la <b>UNIVERSIDAD DISTRITAL FRANCISCO JOSÉ DE CALDAS</b> por "
         "valor de {saldo_universidad_letras} <b>M/CTE (${saldo_universidad} M/CTE)</b>, en "
         "atención a que es un valor no ejecutado en el contrato."),
        (None,
         "Las partes manifiestan que aceptan la Terminación Anticipada y Liquidación Bilateral del "
         "{tipo_contrato} No. {numero_contrato} del día {fecha_suscripcion}, con efectos legales a "
         'partir del "{fecha_efectos_legales}" y se liberan mutuamente de cualquier otra '
         "obligación que pueda derivarse del mismo, declarándose a paz y salvo por todo concepto "
         "una vez se compruebe el pago de la cláusula segunda de la presente Acta."),
        ("PUBLICACIÓN.",
         "En virtud de lo dispuesto en el Estatuto de Contratación – {acuerdo} y las normas "
         "vigentes, se procederá a la publicación del presente documento en el SECOP II que "
         "administra la Agencia Nacional de Contratación Pública – Colombia Compra Eficiente."),
    ]
    if d.nueva_clausula:
        clausulas.append((None, ctx_escapado({"x": d.nueva_clausula})["x"]))

    story += _clausulas(clausulas, c, desde=1)
    story += [
        espacio(12),
        p(t(
            "En constancia de lo consignado en el presente documento, se firma en "
            f"{cfg.CIUDAD_FIRMA_DEFECTO}, el día {{fecha_expedicion_acta}}.", c)),
        bloque_firmas([
            (c["ordenador_nombre"], "Ordenador del Gasto"),
            (c["supervisor_nombre"], "Supervisor"),
            (c["contratista_nombre"], "Contratista"),
        ]),
    ]
    story += _revision(d, c)
    return story, ()


# --- API interna -----------------------------------------------------------------------

GENERADORES = {
    "suspension": _suspension,
    "reinicio": _reinicio,
    "adicion_prorroga": _adicion_prorroga,
    "cesion": _cesion,
    "terminacion_liquidacion": _terminacion_liquidacion,
}


def generar_pdf(tipo_acta: str, payload) -> bytes:
    """Devuelve los bytes del PDF del acta indicada."""
    usar_tamano_letra(payload.tamano_letra)
    story, pie = GENERADORES[tipo_acta](payload)
    return render(cfg.FORMATOS[tipo_acta], story, pie)


def _slug(valor: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", valor).strip("_").lower() or "sn"


def generar_acta(tipo_acta: str, payload) -> ActaResponse:
    """Genera el PDF y lo empaqueta en la respuesta JSON del middleware."""
    pdf = generar_pdf(tipo_acta, payload)
    formato = cfg.FORMATOS[tipo_acta]
    k = payload.contrato
    return ActaResponse(
        success=True,
        filename=f"acta_{tipo_acta}_contrato_{_slug(k.numero_contrato)}_{k.vigencia}.pdf",
        file_base64=base64.b64encode(pdf).decode("ascii"),
        metadata=ActaMetadata(
            tipo_acta=tipo_acta,
            codigo_formato=formato.codigo,
            version_formato=formato.version,
            numero_contrato=k.numero_contrato,
            vigencia=k.vigencia,
            fecha_generacion=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            size_bytes=len(pdf),
        ),
    )
