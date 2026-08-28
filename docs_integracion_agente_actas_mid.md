# Integración con `actas_novedad_mid`

Middleware **sin estado** que genera el PDF de un acta de novedad poscontractual y lo devuelve
en **base64** dentro de un JSON. No tiene base de datos, no persiste nada y no consulta ÁGORA:
**el front envía todos los datos** y el servicio devuelve el archivo.

- Base URL local: `http://localhost:8080`
- OpenAPI interactivo: `http://localhost:8080/docs`
- Healthcheck: `GET /health`

Arranque:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

---

## 1. Endpoints

Todos son **POST**, reciben `Content-Type: application/json` y devuelven el mismo esquema de
respuesta. No hay endpoints GET/PUT/DELETE de negocio.

| Acta | Método | Ruta | Tipo de novedad |
|------|--------|------|-----------------|
| Suspensión | POST | `/v1/actas/suspension` | `NP_SUS` |
| Reinicio | POST | `/v1/actas/reinicio` | `NP_REI` |
| Adición y prórroga | POST | `/v1/actas/adicion-prorroga` | `NP_ADPRO` |
| Cesión | POST | `/v1/actas/cesion` | `NP_CES` |
| Terminación anticipada y liquidación bilateral | POST | `/v1/actas/terminacion-liquidacion` | — |

Códigos de estado:

| Código | Significado |
|--------|-------------|
| `200` | PDF generado. Cuerpo = `ActaResponse` (ver §4) |
| `422` | Payload inválido. Cuerpo = `{"detail": [{"loc": [...], "msg": "..."}]}` de FastAPI |
| `500` | Error inesperado al construir el PDF |

---

## 2. Bloque `contrato` (obligatorio en las 5 actas)

Son los datos maestros que hoy vienen de ÁGORA y de Financiera. **El front los reenvía tal cual**;
el middleware no los consulta.

```jsonc
{
  "contrato": {
    "numero_contrato": "1234",                 // string, requerido
    "vigencia": 2024,                          // int 1990–2100, requerido
    "tipo_contrato": "Contrato de Prestación de Servicios", // string, default el mostrado
    "objeto_contrato": "Prestar servicios profesionales de apoyo administrativo", // string, requerido
    "valor_contrato": 10000000,                // number/string decimal > 0, requerido
    "plazo": "tres (3) meses",                 // string YA EN LETRAS, requerido
    "plazo_dias": 90,                          // int opcional (solo se imprime en el acta de reinicio)
    "fecha_suscripcion": "2024-02-05",         // date ISO YYYY-MM-DD, requerido
    "fecha_inicio": "2024-03-01",              // date ISO, requerido
    "cdp_numero": "CDP-001",                   // string opcional
    "rp_numero": "RP-001",                     // string opcional
    "cdp_vigencia": 2024,                      // int opcional
    "unidad_ejecutora": 1,                     // int, default 1. 1 = Oficina de Contratación; otro = Ofex
    "contratista": { /* Persona, requerido */ },
    "supervisor":  { /* Persona, requerido en suspension, reinicio, cesion, terminacion */ },
    "ordenador":   { /* Persona, requerido en suspension, adicion-prorroga, cesion, terminacion */ }
  }
}
```

### Objeto `Persona`

```jsonc
{
  "nombre": "Juan Pérez",          // string, requerido
  "documento": "1010101010",       // string, requerido
  "tipo_documento": "C.C.",        // string, default "C.C."
  "ciudad_documento": "Bogotá",    // string, default "Bogotá"
  "apellidos": "Díaz López",       // string opcional — SOLO se usa para el cesionario
  "rol": "Director",               // string opcional — calidad/cargo que se imprime
  "resolucion": "Resolución 262-2025" // string opcional — designación del ordenador del gasto
}
```

### Personas requeridas por acta

| Acta | `contratista` | `supervisor` | `ordenador` |
|------|:---:|:---:|:---:|
| suspension | ✅ | ✅ | ✅ |
| reinicio | ✅ | ✅ | — |
| adicion-prorroga | ✅ | — | ✅ |
| cesion | ✅ | ✅ | ✅ |
| terminacion-liquidacion | ✅ | ✅ | ✅ |

Si falta una persona requerida la respuesta es `422` con
`msg: "esta acta requiere contrato.ordenador"`.

### Campos comunes a nivel raíz (opcionales en todas las actas)

| Campo | Tipo | Default | Uso |
|-------|------|---------|-----|
| `fecha_expedicion_acta` | date ISO | hoy (UTC del servidor) | Fecha de firma que se imprime en el cierre |
| `elaboro` | string | `________` | Fila "Proyectó / Elaboró" |
| `jefe_juridica_nombre` | string | `________` | Fila "Revisó y Aprobó" |
| `nueva_clausula` | string | — | Si viene, se agrega como última cláusula numerada |
| `tamano_letra` | int (1-50) | `10` | Tamaño de letra del cuerpo del acta, en puntos. La cabecera institucional (membrete) no escala. |

> **Formato de fechas:** todas las fechas se envían en **ISO `YYYY-MM-DD`** y el PDF las imprime
> en letras (`10 de abril de 2024`). Los valores monetarios se envían como número o string decimal
> y el PDF imprime letras + separador de miles (`DIEZ MILLONES DE PESOS ... ($10.000.000 M/CTE)`).
> Un campo opcional ausente se imprime como `________`, igual que el aplicativo original.

---

## 3. Payload por acta

### 3.1 `POST /v1/actas/suspension`

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `fecha_inicio_suspension` | date | ✅ | No puede ser anterior a `contrato.fecha_inicio` |
| `fecha_fin_suspension` | date | ✅ | ≥ `fecha_inicio_suspension` |
| `motivo` | string | — | Default `"________"` |
| `fecha_solicitud` | date | ✅ | Escrito del contratista |
| `numero_oficio_supervisor` | string | ✅ | |
| `fecha_oficio_supervisor` | date | ✅ | |
| `numero_oficio_ordenador` | string | ✅ | |
| `fecha_oficio_ordenador` | date | ✅ | |
| `ciudad_firma` | string | — | Default `"Bogotá D.C."` |

**Calculado por el backend:** `fecha_reinicio = fecha_fin_suspension + 1 día` (viene de vuelta en el
JSON de la petición validada, y se imprime en la tabla del acta). **No lo envíes.**

```json
{
  "contrato": { "...": "ver §2" },
  "fecha_inicio_suspension": "2024-04-10",
  "fecha_fin_suspension": "2024-04-30",
  "motivo": "Fuerza mayor comprobada por cierre de sede",
  "fecha_solicitud": "2024-04-05",
  "numero_oficio_supervisor": "OF-456",
  "fecha_oficio_supervisor": "2024-04-06",
  "numero_oficio_ordenador": "OF-789",
  "fecha_oficio_ordenador": "2024-04-08",
  "fecha_expedicion_acta": "2024-04-09",
  "elaboro": "Laura Niño",
  "jefe_juridica_nombre": "Ana Torres"
}
```

### 3.2 `POST /v1/actas/reinicio`

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `suspension_previa.fecha_acta` | date | ✅ | Fecha del acta de suspensión previa |
| `suspension_previa.fecha_inicio_suspension` | date | ✅ | |
| `suspension_previa.fecha_fin_suspension` | date | ✅ | |
| `fecha_reinicio` | date | — | Si se omite: `fecha_fin_suspension + 1 día` |

```json
{
  "contrato": { "...": "ver §2" },
  "suspension_previa": {
    "fecha_acta": "2024-04-09",
    "fecha_inicio_suspension": "2024-04-10",
    "fecha_fin_suspension": "2024-04-30"
  },
  "elaboro": "Laura Niño",
  "jefe_juridica_nombre": "Ana Torres"
}
```

### 3.3 `POST /v1/actas/adicion-prorroga`

> El acta es **adición Y prórroga**: siempre incluye ambas. No existen los casos "solo adición"
> ni "solo prórroga", así que **no hay flags** `adicion` / `prorroga` — si el front los envía se
> ignoran. El acta imprime siempre las cláusulas PRIMERA a SÉPTIMA (adición, modificación de la
> cláusula tercera, prórroga, modificación de la cláusula sexta, vigencia, perfeccionamiento y
> publicación).

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `valor_adicion` | number | ✅ | > 0 y **no puede superar el 50 % de `contrato.valor_contrato`** |
| `prorroga_meses` | int | ✅* | Se combinan meses + días |
| `prorroga_dias` | int | ✅* | *Al menos uno de los dos debe ser > 0 |
| `nuevo_plazo_contrato` | string | — | Plazo total en letras. Si se omite: `"{plazo} más {prórroga}"` |
| `numero_oficio` | string | ✅ | Oficio de solicitud |
| `fecha_oficio` | date | ✅ | |
| `numero_solicitud` | string | ✅ | Solicitud de Necesidad |
| `fecha_solicitud` | date | ✅ | |
| `cesion_previa` | objeto | — | `{ "fecha_cesion": date, "cedente_nombre": string }` → activa el considerando de cesión previa |

**Calculado por el backend:** `nuevo_valor_total = valor_contrato + valor_adicion`.

```json
{
  "contrato": { "...": "ver §2" },
  "valor_adicion": 2000000,
  "prorroga_meses": 2,
  "prorroga_dias": 15,
  "numero_oficio": "OF-321",
  "fecha_oficio": "2024-05-15",
  "numero_solicitud": "SN-123",
  "fecha_solicitud": "2024-05-14",
  "elaboro": "Laura Niño",
  "jefe_juridica_nombre": "Ana Torres"
}
```

Errores típicos (`422`):

```json
{ "detail": [{ "loc": ["body"],
  "msg": "Value error, la adición (6000000) supera el 50% del valor inicial (tope 5000000)",
  "type": "value_error" }] }
```

```json
{ "detail": [{ "loc": ["body"],
  "msg": "Value error, la prórroga es obligatoria: indique prorroga_meses y/o prorroga_dias",
  "type": "value_error" }] }
```

### 3.4 `POST /v1/actas/cesion`

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `cesionario` | Persona | ✅ | Usa `nombre` + `apellidos` |
| `fecha_cesion` | date | ✅ | Efectos legales de la cesión |
| `fecha_terminacion_cedente` | date | ✅ | Hasta cuándo ejecutó el cedente |
| `valor_desembolsado` | number | ✅ | Reconocido al cedente |
| `valor_a_favor` | number | ✅ | Saldo pendiente por pagar al cedente |
| `plazo_cedente` | string | ✅ | En letras, ej. `"un (1) mes"` |
| `dias_pago_cedente` | string | ✅ | En letras, ej. `"quince (15) días"` |
| `plazo_cesionario` | string | ✅ | En letras |
| `numero_oficio_supervisor` | string | ✅ | |
| `fecha_oficio_supervisor` | date | ✅ | |
| `numero_solicitud` | string | — | Solicitud de necesidad |
| `fecha_solicitud` | date | ✅ | |
| `suspension_previa` | objeto | — | `{fecha_acta, fecha_inicio_suspension, fecha_fin_suspension}` → considerando condicional |
| `reinicio_previo` | objeto | — | `{fecha_acta}` → considerando condicional |
| `adicion_previa` | objeto | — | `{fecha, valor_adicion, prorroga_meses, prorroga_dias, numero_solicitud, fecha_solicitud, fecha_oficio}` → considerando condicional |
| `nuevo_considerando` | string | — | Considerando adicional libre |

**Calculado por el backend:** `valor_cesionario = valor_contrato − (valor_desembolsado + valor_a_favor)`.
Se rechaza (`422`) si `valor_desembolsado + valor_a_favor > valor_contrato`.

```json
{
  "contrato": { "...": "ver §2" },
  "cesionario": {
    "nombre": "Pedro", "apellidos": "Díaz López",
    "documento": "4040404040", "tipo_documento": "C.C.", "ciudad_documento": "Bogotá"
  },
  "fecha_cesion": "2024-06-25",
  "fecha_terminacion_cedente": "2024-06-24",
  "valor_desembolsado": 5000000,
  "valor_a_favor": 1000000,
  "plazo_cedente": "un (1) mes",
  "dias_pago_cedente": "quince (15) días",
  "plazo_cesionario": "dos (2) meses",
  "numero_oficio_supervisor": "OF-456",
  "fecha_oficio_supervisor": "2024-06-20",
  "numero_solicitud": "SN-123",
  "fecha_solicitud": "2024-06-18",
  "suspension_previa": {
    "fecha_acta": "2024-04-09",
    "fecha_inicio_suspension": "2024-04-10",
    "fecha_fin_suspension": "2024-04-30"
  },
  "elaboro": "Laura Niño",
  "jefe_juridica_nombre": "Ana Torres"
}
```

### 3.5 `POST /v1/actas/terminacion-liquidacion`

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `fecha_terminacion_anticipada` | date | ✅ | |
| `valor_desembolsado` | number | ✅ | Ejecutado y pagado |
| `saldo_contratista` | number | ✅ | Valor no ejecutado a favor del contratista |
| `saldo_universidad` | number | — | Si se omite: `valor_contrato − valor_desembolsado − saldo_contratista` |
| `fecha_certificacion` | date | ✅ | Certificación de la Unidad de Presupuesto |
| `numero_oficio_supervisor` | string | ✅ | |
| `fecha_oficio_supervisor` | date | ✅ | |
| `numero_oficio_ordenador` | string | ✅ | |
| `fecha_oficio_ordenador` | date | ✅ | |
| `fecha_efectos_legales` | date | ✅ | |
| `adicion_previa` | objeto | — | Igual que en cesión → considerando condicional |

**Regla del balance:** `valor_desembolsado + saldo_contratista + saldo_universidad` debe ser
**exactamente igual** a `contrato.valor_contrato`. Si no cuadra → `422` con
`"el balance no cuadra: ..."`. Lo más simple es **omitir `saldo_universidad`** y dejar que el
backend lo calcule.

```json
{
  "contrato": { "...": "ver §2" },
  "fecha_terminacion_anticipada": "2024-06-30",
  "valor_desembolsado": 5000000,
  "saldo_contratista": 3000000,
  "fecha_certificacion": "2024-06-28",
  "numero_oficio_supervisor": "OF-456",
  "fecha_oficio_supervisor": "2024-06-20",
  "numero_oficio_ordenador": "OF-789",
  "fecha_oficio_ordenador": "2024-06-22",
  "fecha_efectos_legales": "2024-07-01",
  "elaboro": "Laura Niño",
  "jefe_juridica_nombre": "Ana Torres"
}
```

---

## 4. Respuesta

Idéntica en los 5 endpoints:

```json
{
  "success": true,
  "filename": "acta_suspension_contrato_1234_2024.pdf",
  "file_base64": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoIDMgMCB... (truncado)",
  "metadata": {
    "tipo_acta": "suspension",
    "codigo_formato": "GC-PR-014-FR-054",
    "version_formato": "02",
    "numero_contrato": "1234",
    "vigencia": 2024,
    "fecha_generacion": "2026-08-03T10:00:00Z",
    "size_bytes": 6951
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `success` | bool | Siempre `true` en un `200` |
| `filename` | string | Nombre sugerido: `acta_{tipo}_contrato_{numero}_{vigencia}.pdf` |
| `file_base64` | string | PDF completo en base64 **sin prefijo** `data:` |
| `metadata.tipo_acta` | enum | `suspension` \| `reinicio` \| `adicion_prorroga` \| `cesion` \| `terminacion_liquidacion` |
| `metadata.codigo_formato` | string | Código institucional del formato (`GC-PR-014-FR-0xx`) |
| `metadata.version_formato` | string | Versión del formato |
| `metadata.fecha_generacion` | string | ISO-8601 UTC con `Z` |
| `metadata.size_bytes` | int | Tamaño del PDF decodificado; sirve para validar la descarga |

> `file_base64` **no** trae el prefijo `data:application/pdf;base64,`. Si lo necesitas para un
> `<iframe>` o un `<a href>`, concaténalo tú.

---

## 5. Ejemplo de consumo (TypeScript / fetch)

Cubre los 4 pasos: enviar, recibir, guardar el base64 en BD y forzar la descarga en el PC del
usuario.

```ts
// ---------- tipos ----------
const BASE_URL = "http://localhost:8080";

type TipoActa =
  | "suspension"
  | "reinicio"
  | "adicion_prorroga"
  | "cesion"
  | "terminacion_liquidacion";

const RUTA: Record<TipoActa, string> = {
  suspension: "/v1/actas/suspension",
  reinicio: "/v1/actas/reinicio",
  adicion_prorroga: "/v1/actas/adicion-prorroga",
  cesion: "/v1/actas/cesion",
  terminacion_liquidacion: "/v1/actas/terminacion-liquidacion",
};

interface ActaResponse {
  success: boolean;
  filename: string;
  file_base64: string;
  metadata: {
    tipo_acta: TipoActa;
    codigo_formato: string;
    version_formato: string;
    numero_contrato: string;
    vigencia: number;
    fecha_generacion: string;
    size_bytes: number;
  };
}

// ---------- 1. enviar la petición al middleware ----------
async function generarActa(tipo: TipoActa, payload: unknown): Promise<ActaResponse> {
  const res = await fetch(`${BASE_URL}${RUTA[tipo]}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    // 422 de FastAPI: { detail: [{ loc, msg, type }] }
    const err = await res.json().catch(() => ({}));
    const detalle = Array.isArray(err.detail)
      ? err.detail.map((d: any) => `${d.loc?.join(".")}: ${d.msg}`).join(" | ")
      : JSON.stringify(err);
    throw new Error(`El acta no se pudo generar (${res.status}): ${detalle}`);
  }

  // ---------- 2. recibir el JSON ----------
  return (await res.json()) as ActaResponse;
}

// ---------- 3. persistir el base64 (gestor documental / BD de novedades) ----------
async function guardarEnGestorDocumental(acta: ActaResponse, novedadId: string) {
  const res = await fetch("/api/novedades/documentos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      novedad_id: novedadId,
      nombre: acta.filename,
      // el base64 va tal cual, sin prefijo data:
      contenido_base64: acta.file_base64,
      tipo_acta: acta.metadata.tipo_acta,
      codigo_formato: acta.metadata.codigo_formato,
      generado_en: acta.metadata.fecha_generacion,
    }),
  });
  if (!res.ok) throw new Error("No se pudo guardar el acta en el gestor documental");
  return res.json(); // p. ej. { id, url } para asociar a la novedad
}

// ---------- 4. base64 -> Blob -> descarga en el PC del usuario ----------
function base64ToBlob(base64: string, mime = "application/pdf"): Blob {
  const binario = atob(base64);            // string con los bytes crudos
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

function descargarPdf(acta: ActaResponse) {
  const blob = base64ToBlob(acta.file_base64);

  // sanity check contra metadata.size_bytes
  if (blob.size !== acta.metadata.size_bytes) {
    console.warn(`Tamaño inesperado: ${blob.size} vs ${acta.metadata.size_bytes}`);
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = acta.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url); // liberar memoria
}

// ---------- flujo completo ----------
async function onClickGenerarSuspension(contrato: unknown, novedadId: string) {
  const acta = await generarActa("suspension", {
    contrato,
    fecha_inicio_suspension: "2024-04-10",
    fecha_fin_suspension: "2024-04-30",
    motivo: "Fuerza mayor comprobada por cierre de sede",
    fecha_solicitud: "2024-04-05",
    numero_oficio_supervisor: "OF-456",
    fecha_oficio_supervisor: "2024-04-06",
    numero_oficio_ordenador: "OF-789",
    fecha_oficio_ordenador: "2024-04-08",
    elaboro: "Laura Niño",
    jefe_juridica_nombre: "Ana Torres",
  });

  await guardarEnGestorDocumental(acta, novedadId); // persistencia
  descargarPdf(acta);                                // descarga local
}
```

### Variante con axios

```ts
import axios from "axios";

const api = axios.create({ baseURL: BASE_URL, headers: { "Content-Type": "application/json" } });

async function generarActaAxios(tipo: TipoActa, payload: unknown): Promise<ActaResponse> {
  try {
    const { data } = await api.post<ActaResponse>(RUTA[tipo], payload);
    return data;
  } catch (e: any) {
    const detalle = e.response?.data?.detail;
    throw new Error(`El acta no se pudo generar: ${JSON.stringify(detalle ?? e.message)}`);
  }
}
```

### Previsualizar en lugar de descargar

```ts
const url = URL.createObjectURL(base64ToBlob(acta.file_base64));
document.querySelector<HTMLIFrameElement>("#visor")!.src = url;
// o: window.open(url, "_blank");
// recuerda URL.revokeObjectURL(url) al cerrar el visor
```

> Para archivos grandes, `atob` + bucle es suficiente (un acta pesa ~6–10 KB). Si algún día un
> acta creciera a varios MB, cambia `base64ToBlob` por
> `await (await fetch(`data:application/pdf;base64,${b64}`)).blob()`.

---

## 6. Notas de implementación (para el que mantenga esto)

| Tema | Estado |
|------|--------|
| **Logo institucional** | `assets/logo.png` (escudo UD). Se reescala a 300 px una sola vez en memoria: el original pesa ~1 MB y ReportLab lo embebería en crudo en cada PDF. Ruta y tamaño de la caja en `services/config_institucional.py`. Si el archivo falta, el encabezado imprime "UNIVERSIDAD DISTRITAL" como texto. |
| **Tamaño del PDF** | ~103 KB por acta con el logo embebido (~137 KB al pasarlo a base64). Sin logo son ~7 KB. |
| **PDFs de muestra** | `python generar_ejemplos.py` escribe las 5 actas de ejemplo en `ejemplos_output/`. Los mismos payloads son el fixture de `test_actas.py`. |
| **Marcado en textos legales** | Los textos de `config_institucional.py` pueden traer `<b>`/`<i>` y se inyectan envueltos en `Crudo(...)` para no escaparse. **Todo dato del payload sí se escapa** (un `&` o `<` del usuario no rompe el PDF ni inyecta marcado). |
| **Parámetros institucionales** | Códigos `GC-PR-014-FR-0xx`, versiones, NIT, Acuerdo 003 de 2015, Resolución de Rectoría, tope del 50 %, textos legales citados y dirección de la oficina viven en `services/config_institucional.py`. Cambiarlos no toca la lógica. |
| **Plazos en letras** | `contrato.plazo`, `plazo_cedente`, `dias_pago_cedente` y `plazo_cesionario` se reciben **ya en letras**. El backend solo compone en letras la prórroga (`prorroga_meses` / `prorroga_dias`) y los valores monetarios. |
| **CORS** | Abierto (`*`) por defecto. Restringir en producción con la variable de entorno `CORS_ORIGINS` (lista separada por comas). |
| **Autenticación** | El servicio **no valida token**. Si se expone fuera de la red interna, ponerlo detrás del gateway WSO2/OAuth2 existente. |
| **Texto duplicado** | Frases como "el Contrato {tipo_contrato} No. 1234" quedan como "el Contrato Contrato de Prestación de Servicios No. 1234" si `tipo_contrato` ya incluye la palabra "Contrato". El texto legal se transcribió literalmente del aplicativo original; envía `tipo_contrato` como lo hace ÁGORA (p. ej. `"CPS"`) o ajusta la plantilla. |
| **Tests** | `python -m pytest test_actas.py` — genera las 5 actas y verifica las reglas de negocio (tope 50 %, valor a ceder, balance de liquidación, personas requeridas). |
