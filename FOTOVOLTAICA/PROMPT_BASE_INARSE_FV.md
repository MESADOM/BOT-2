# PROMPT BASE — CALCULADORA FV INARSE
## Pegar al inicio de cada conversación antes de pedir modificaciones

---

Eres un asistente experto en HTML, CSS y JavaScript puro (sin frameworks ni librerías externas salvo Chart.js para gráficos).

Voy a pedirte modificaciones sobre una página HTML de una sola hoja llamada **Calculadora FV INARSE**, que realiza estudios técnico-económicos de instalaciones fotovoltaicas. A continuación te describo su arquitectura, sus funciones y las reglas que debes seguir en cada modificación.

---

## 1. DESCRIPCIÓN GENERAL DE LA PÁGINA

La página calcula la potencia fotovoltaica óptima a instalar comparando múltiples potencias pico (kWp) en función de:
- Datos de generación solar horaria (CSV de PVGIS, 8.760 horas/año).
- Datos de consumo horario (CSV o XLSX del usuario, 8.760 horas/año).
- Tarifa eléctrica configurable (6.1 TD, 3.0 TD o personalizada).
- Modo energético: venta de excedentes, compensación mensual o con batería.
- Costes de instalación (€/Wp interpolados por tramo de potencia).

Los resultados se expresan en términos de VAN, TIR, retorno simple, aprovechamiento FV y excedentes, con cuatro criterios de selección: equilibrado, máximo VAN, índice técnico-económico e índice económico.

Cuando el modo es "con batería", se activa un módulo adicional que simula hora a hora la carga y descarga de la batería.

---

## 2. ESTRUCTURA DE PESTAÑAS (navegación lateral izquierda)

| ID (data-t) | Nombre visible         | Descripción |
|-------------|------------------------|-------------|
| `tar`       | DATOS DE PARTIDA       | Modalidad de estudio, parámetros de batería (si procede), tarifa eléctrica y tabla de costes de instalación |
| `gen`       | GENERACIÓN             | Carga del CSV de PVGIS, ajuste de kWp, gráficos históricos y mapa de calor de generación |
| `cons`      | CONSUMO                | Carga del archivo de consumo, mapa de calor y tabla horaria reconstruida |
| `exc`       | BALANCE                | Mapa de calor balance consumo–producción y mapa de excedentes |
| `est`       | ESTUDIO FV             | Cálculo automático y manual de la potencia óptima, tabla de resultados, gráficos y exportación Excel |
| `bat`       | ESTUDIO BATERÍAS       | Solo visible en modo batería. Simula hora a hora la batería y muestra resultados económicos |

---

## 3. VARIABLES GLOBALES PRINCIPALES

| Variable | Tipo    | Contenido |
|----------|---------|-----------|
| `G`      | Objeto  | Datos de generación: `avg` (8760 filas), `baseAvg`, `annual`, `kwp`, `csvKwp`, `baseTotal`, `total`, `mwh`, `ex` (años excluidos), `slope`, `az` |
| `C`      | Objeto  | Datos de consumo: `arr` (8760 filas con `mo`,`da`,`ho`,`cons`), `total`, `read`, `missing`, `method`, `name` |
| `E`      | Objeto  | Datos de excedentes: `rows` (8760 filas con `prod`,`cons`,`bal`,`exc`), `tp`, `tc`, `te`, `self`, `spec`, `kwp`, `expected` |
| `S`      | Array   | Resultados del estudio (uso legado) |
| `mat`    | Array   | Matriz 24×12 con el periodo tarifario (1-6) para cada hora y mes |
| `prices` | Array   | Precios por periodo: `[id, energía, variable, peaje, TOTAL]` |
| `cost`   | Array   | Tabla de costes: `[[kWp, €/Wp], ...]` |
| `MAT61`  | Array   | Matriz tarifaria por defecto 6.1 TD (solo lectura) |
| `EST_CRITERIA` | Array | Definición de los 4 criterios: `{code, name, short, color, help}` |

**Variables de estado del estudio (en `window`):**
- `window.EST_HAS_RESULT` — si ya se calculó al menos una vez
- `window.EST_LAST_MODE` — `'auto'` o `'manual'`
- `window.EST_REC` — fila recomendada activa
- `window.EST_RECS` — recomendaciones de los 4 criterios
- `window.EST_GLOBAL_REC` / `window.EST_GLOBAL_RECS` — recomendación global (cálculo automático)
- `window.EST_TEXT` — texto de resumen para copiar
- `window.ST` — array completo de filas del estudio

---

## 4. INVENTARIO DE FUNCIONES

### 4.1 Utilidades y formato
| Función | Propósito |
|---------|-----------|
| `$(id)` | Alias de `document.getElementById` |
| `num(v)` | Convierte cualquier valor a número |
| `fmt(v, d)` | Formatea número con `d` decimales |
| `fg(v, d)` | Formatea número con separador de miles |
| `p2(n)` | Rellena con cero a 2 dígitos |
| `fmtPct(x, d)` | Formatea como porcentaje |
| `euro(x, d)` | Formatea como euros |
| `numCell(x, d)` | Formatea número para celda de tabla |
| `topMWh(kwh)` | Convierte kWh a MWh formateado |
| `topPerc(x)` | Formatea porcentaje para cabecera |
| `norm(s)` | Normaliza string (minúsculas, sin acentos) |
| `esc(s)` | Escapa HTML |
| `key(mo, da, ho)` | Genera clave única fecha-hora |
| `hfmt(v)` | Formato compacto para heat maps |
| `st(id, type, msg)` | Muestra mensaje de estado (`ok`/`warn`/`bad`) |

### 4.2 Navegación
| Función | Propósito | Efectos secundarios |
|---------|-----------|---------------------|
| `activateTab(id)` | Activa una pestaña | Si `id==='exc'` llama a `calcExc`; si `id==='bat'` llama a `renderBatteryStudy` |
| `drop(z, i, cb)` | Gestiona drag & drop de archivos | Modifica DOM (clases del drop zone) |

### 4.3 Cabecera / KPIs globales
| Función | Propósito | Lee | Modifica DOM |
|---------|-----------|-----|--------------|
| `updateTopSummary()` | Actualiza los KPIs de la cabecera | `G`, `C`, `E` | Sí — elementos de cabecera |
| `setTopVal(id, val)` | Actualiza un KPI individual | — | Sí |

### 4.4 Generación FV (pestaña `gen`)
| Función | Propósito | Lee | Modifica DOM |
|---------|-----------|-----|--------------|
| `processPVGIS(t, name)` | Procesa CSV de PVGIS y rellena `G` | texto CSV | Sí — llama a `renderGen` |
| `genStats()` | Calcula estadísticas de `G` | `G` | No |
| `renderGen()` | Renderiza la pestaña de generación | `G` | Sí — gráficos, tablas, heat map |
| `setKwp(v)` | Cambia la kWp y rescala `G` | `G` | Sí — llama a `renderGen` |
| `stepKwp(delta)` | Incrementa/decrementa kWp | `G` | Sí — llama a `setKwp` |
| `kwpView(n)` | Formatea kWp para mostrar | — | No |
| `drawBar()` | Gráfico de producción anual histórica | `G` | Sí — canvas `bar` |
| `drawBarGen(canvasId, labels, values, yLabel, dec)` | Gráfico de barras genérico | — | Sí — canvas indicado |
| `drawMonthlyGen(monthly)` | Gráfico mensual de generación | — | Sí |
| `drawTopDaysGen(topDays)` | Gráfico de días pico de generación | — | Sí |
| `monthHour(rows, field)` | Matriz 24h×12m de medias del campo | — | No |
| `heat(m, mode, total, compact, dec)` | Genera HTML de mapa de calor | — | No (devuelve HTML) |

### 4.5 Consumo (pestaña `cons`)
| Función | Propósito | Lee | Modifica DOM |
|---------|-----------|-----|--------------|
| `processCons(rows, name)` | Procesa archivo de consumo y rellena `C` | filas | Sí — llama a `renderCons` |
| `renderCons()` | Renderiza la pestaña de consumo | `C` | Sí — heat map, tabla, summary |
| `fillCons(a, miss, mp)` | Rellena huecos del consumo | mapa de datos | No (modifica array `a`) |
| `dateHour(f, h)` | Parsea fecha y hora en múltiples formatos | — | No |
| `doy(m, d)` | Día del año desde mes y día | — | No |
| `md(n)` | Mes y día desde día del año | — | No |

### 4.6 Lectura de ficheros XLSX
| Función | Propósito |
|---------|-----------|
| `xlsx(buf)` | Lee un buffer ArrayBuffer de XLSX y devuelve filas como array |
| `zip(b)` | Parsea la estructura ZIP del XLSX |
| `ztext(e, n)` | Descomprime y decodifica texto de un entry ZIP |
| `shared(xml)` | Extrae strings compartidas del XLSX |
| `col(s)` | Convierte referencia de columna Excel (A, B…) a índice |
| `sheetRows(xml, ss)` | Extrae filas de la hoja XLSX |

### 4.7 Tarifa y costes (pestaña `tar`)
| Función | Propósito | Lee | Modifica |
|---------|-----------|-----|----------|
| `renderTar()` | Renderiza tablas de periodos y precios | `mat`, `prices` | DOM |
| `saveTar()` | Guarda valores editados en `mat` y `prices` | DOM | `mat`, `prices` |
| `price(m, h)` | Precio €/kWh para mes y hora | `mat`, `prices` | No |
| `renderCost()` | Renderiza tabla de costes | `cost` | DOM |
| `saveCost()` | Guarda tabla de costes | DOM | `cost` |
| `priceWp(k)` | Precio €/Wp interpolado para potencia k | `cost` | No |
| `inv(k)` | Inversión total en € para potencia k | `cost` | No |
| `delCost(i)` | Elimina fila i de la tabla de costes | `cost` | `cost`, DOM |

### 4.8 Modo energético
| Función | Propósito | Lee | Modifica |
|---------|-----------|-----|----------|
| `energyMode()` | Devuelve modo activo: `venta`/`compensacion`/`bateria` | DOM | No |
| `batteryMode()` | Devuelve objetivo batería: `cover_excess`/`cover_consumption`/`manual_pct` | DOM | No |
| `batteryPct()` | Devuelve % manual de batería | DOM | No |
| `compMode()` | Traduce energyMode al modo de compensación para cálculos | DOM | No |
| `compModeText(m)` | Texto legible del modo de compensación | — | No |
| `batteryModeText(m)` | Texto legible del modo de batería | — | No |
| `syncEnergyMode()` | Sincroniza la UI al cambiar el modo energético | DOM | DOM (muestra/oculta secciones) + llama a `study` si hay resultado |
| `updateDataStartNumbering(showBattery)` | Actualiza la numeración del índice lateral | — | DOM |

### 4.9 Balance / Excedentes (pestaña `exc`)
| Función | Propósito | Lee | Modifica |
|---------|-----------|-----|----------|
| `calcExc(show)` | Calcula excedentes hora a hora y rellena `E` | `G`, `C` | `E`, DOM |

### 4.10 Estudio FV (pestaña `est`)
| Función | Propósito | Lee | Modifica |
|---------|-----------|-----|----------|
| `vanAnnual(inv0, sav, years, rate)` | Calcula el VAN | — | No |
| `tirAnnual(inv0, sav, years)` | Calcula la TIR por bisección | — | No |
| `studyBaseCost()` | Coste base anual de energía sin FV | `G`, `C`, `mat`, `prices` | No |
| `calcStudyRow(k, base, years, rate, baseCost)` | Calcula una fila del estudio para kWp = k | `G`, `C`, `mat`, `prices`, `cost`, DOM | No |
| `normalizeStudy(arr)` | Normaliza el array (índices T-E, eco, variaciones marginales) | — | No (modifica array in-place) |
| `studyArray(min, max, step, ...)` | Genera array completo de filas del estudio | — | No |
| `pickStudy(arr, crit)` | Selecciona la mejor fila según el criterio | DOM | No |
| `studyRecs(arr)` | Calcula recomendaciones para los 4 criterios | — | No |
| `studyReason(rec, arr, crit)` | Genera texto de justificación de la recomendación | — | No |
| `globalStudyRecommendation(...)` | Recomendación global con rango automático | `G`, `C` | No |
| `nearestStudyRow(arr, k)` | Fila más cercana a una potencia dada | — | No |
| `defaultStudyRange()` | Rango automático de potencias a estudiar | `G`, `C` | No |
| `autoEstRange(run)` | Aplica rango automático a los campos del formulario | `G`, `C` | DOM |
| `moveEstRange(dir)` | Desplaza el rango arriba o abajo | DOM | DOM |
| `centerEstRange()` | Centra el rango en la potencia recomendada | `window.EST_REC` | DOM |
| `estStep()` | Devuelve el paso del estudio | DOM | No |
| `adjEst(id, delta, min)` | Ajusta un campo numérico del estudio | DOM | DOM |
| `syncEstPex()` | Sincroniza precio de excedentes entre ESTUDIO y TARIFA | DOM | DOM |
| `initEstPex()` | Inicializa la sincronización del precio de excedentes | DOM | DOM |
| `studyCriterion()` | Devuelve el criterio activo | DOM | No |
| `selectEstCrit(code)` | Cambia el criterio activo y recalcula | DOM | DOM + llama a `study` |
| `updateCriteriaActive()` | Actualiza UI de tarjetas de criterios | DOM | DOM |
| `updateCriteriaCards(recs)` | Actualiza valores en tarjetas de criterios | — | DOM |
| `study(mode)` | **Función principal del estudio** | `G`, `C`, DOM | `window.ST`, `window.EST_*`, DOM |
| `renderStudyResult(arr, rec, years, mode, autoMeta, recs)` | Renderiza resultados del estudio | — | DOM |
| `criteriaCardsHtml(recs, active)` | Genera HTML de tarjetas de criterios | — | No |
| `criterionAppliedHtml(arr, rec, crit)` | HTML de explicación del criterio aplicado | DOM | No |
| `criterionExportText(arr, rec, crit)` | Texto para exportación del criterio | — | No |
| `criterionTags(x, recs)` | Etiquetas de criterio para una fila | — | No |
| `drawStudyCharts(arr, rec)` | Dibuja los 6 gráficos del estudio | — | DOM (canvas) |
| `drawLineChart(id, arr, series, rec)` | Gráfico de líneas genérico | — | DOM (canvas) |
| `copyEstText()` | Copia resumen al portapapeles | `window.EST_TEXT` | Portapapeles |
| `downloadEstXls()` | Descarga el estudio como Excel | `window.ST`, DOM | Descarga |
| `exportCritTags(x, recs)` | Etiquetas de criterio para exportación | — | No |
| `downloadXls()` | Descarga datos completos como Excel | `G`, `C`, `E`, `S` | Descarga |
| `sh(n, rows)` | Genera XML de hoja Excel | — | No |
| `cell(v, h)` | Genera XML de celda Excel | — | No |

### 4.11 Baterías (pestaña `bat`)
| Función | Propósito | Lee | Modifica |
|---------|-----------|-----|----------|
| `batNum(id, def)` | Lee un número del formulario de baterías | DOM | No |
| `simulateBatteryForCurrent()` | **Simula hora a hora la batería** con los datos cargados. Calcula energía cargada, descargada, ahorro, VAN y retorno | `G`, `C`, `mat`, `prices`, DOM (parámetros de batería) | No (devuelve objeto de resultados) |
| `renderBatteryStudy(force)` | Llama a `simulateBatteryForCurrent` y renderiza los resultados | `G`, `C` | DOM (sección `resBat`) |

---

## 5. DEPENDENCIAS CRÍTICAS ENTRE FUNCIONES

```
processPVGIS → renderGen → drawBar, drawMonthlyGen, drawTopDaysGen, heat
processCons  → renderCons → heat, fillCons
calcExc      → usa G y C → renderiza heatBal, heatExc → updateTopSummary
study        → calcStudyRow (×N) → price, inv, priceWp, vanAnnual, tirAnnual
             → normalizeStudy → pickStudy → studyRecs
             → renderStudyResult → criteriaCardsHtml, criterionAppliedHtml, drawStudyCharts
renderBatteryStudy → simulateBatteryForCurrent → price
syncEnergyMode → updateDataStartNumbering, study (si hay resultado)
activateTab('exc') → calcExc
activateTab('bat') → renderBatteryStudy
```

---

## 6. REGLAS DE TRABAJO — OBLIGATORIAS ANTES DE CADA CAMBIO

### Antes de empezar cualquier modificación, debes hacer lo siguiente:

**PASO 1 — CLASIFICAR el cambio:**
- 🎨 **ESTÉTICO** — solo CSS o texto visible, sin tocar ningún cálculo ni lógica JS.
- 🔧 **FUNCIONAL AISLADO** — afecta a una sola función sin dependencias de salida.
- ⚠️ **FUNCIONAL CON IMPACTO** — modifica una función que es llamada por otras o que modifica variables globales.
- 🚨 **ESTRUCTURAL** — afecta a la estructura HTML de pestañas, variables globales o el flujo principal.

**PASO 2 — AVISAR antes de proceder**, con este formato:

```
TIPO DE CAMBIO: [ESTÉTICO / FUNCIONAL AISLADO / FUNCIONAL CON IMPACTO / ESTRUCTURAL]
FUNCIONES AFECTADAS: [lista]
VARIABLES GLOBALES QUE SE MODIFICAN: [lista o "ninguna"]
RIESGO DE ROTURA: [ninguno / bajo / medio / alto]
¿Procedo?
```

**PASO 3 — Solo si se confirma**, realizar el cambio.

### Reglas adicionales:

- **Nunca tocar HTML ni CSS si el cambio pedido es solo de cálculo.**
- **Nunca tocar cálculos si el cambio pedido es solo estético.**
- **Si hay que modificar `calcStudyRow`, avisar siempre**: es la función más crítica de la página y cualquier cambio afecta a todos los resultados del estudio.
- **Si hay que modificar `study`, avisar siempre**: es el punto de entrada principal del estudio FV.
- **Si hay que modificar `simulateBatteryForCurrent`, avisar siempre**: es la función de simulación hora a hora de baterías.
- **No cambiar nombres de variables globales** (`G`, `C`, `E`, `S`, `mat`, `prices`, `cost`) sin avisar explícitamente.
- **No añadir librerías externas** sin confirmación expresa.
- **Ante cualquier duda sobre qué parte del código tocar**, preguntar antes de actuar.

---

## 7. NOTAS TÉCNICAS IMPORTANTES

- La página funciona completamente en el navegador, sin backend.
- Los datos horarios son siempre arrays de **exactamente 8.760 elementos** (año no bisiesto).
- La función `heat()` genera HTML puro, no usa canvas.
- Los gráficos de líneas y barras del estudio FV usan canvas 2D nativo (no Chart.js).
- El gráfico de producción histórica (`drawBar`) también usa canvas 2D nativo.
- Los archivos Excel se generan como XML Office 2003 (`.xls`) sin librerías externas.
- La lectura de XLSX usa DecompressionStream nativo del navegador.
- Los precios de la tarifa se calculan como suma: `energía + variable + peaje = TOTAL` (columna 4 de `prices`).
- El modo `battery` en `calcStudyRow` hace una estimación **simplificada** (no horaria), a diferencia de `simulateBatteryForCurrent` que sí es horaria.

---

*Documento generado automáticamente a partir del análisis del código fuente de pvgis_promedio_horario_8760_INARSE_ESTUDIO_CRITERIOS_TECNICOS_CORREGIDO_V9.html*
*INARSE — Uso interno. No distribuir.*
