# ============================================================
# SISTEMA DE VERSIONADO
# Formato: P.C.E
# P = version de A_principal.py
# C = version de A_configuracion.py
# E = version de A_estrategia.py
#
# Version actual: 1.3.1
# Fecha: 2026-03-18
#
# Cambios en esta version:
# - Se incorpora selector de regimen de mercado semanal
# - Se mantiene logica base de señal/entrada/salida
# - El sizing pasa a ser dinamico por regimen AGRESIVO/DEFENSIVO
# ============================================================

from pathlib import Path

VERSION_SISTEMA = "1.3.1"
VERSION_PRINCIPAL = 1
VERSION_CONFIGURACION = 3
VERSION_ESTRATEGIA = 1

# ============================================================
# RUTAS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DIR_DATOS = BASE_DIR / "datos"

RUTA_QQQ = DIR_DATOS / "QQQ.csv"
RUTA_QQQ3 = DIR_DATOS / "QQQ3.csv"
RUTA_VIX = DIR_DATOS / "VIX.csv"

# Guardado opcional de resultados internos
GUARDAR_RESULTADOS = False
RUTA_SALIDA_OPERACIONES = DIR_DATOS / "operaciones_generadas.csv"
RUTA_SALIDA_RESUMEN = DIR_DATOS / "resumen_anual_generado.csv"

# ============================================================
# CAPITAL Y COSTES
# ============================================================
CAPITAL_INICIAL_EUR = 1000.0
COMISION_POR_OPERACION_EUR = 2.0

# ============================================================
# PARAMETROS - BLOQUE 1 (logica base)
# ============================================================
PERIODO_MEDIA_LARGA = 50
DIAS_CONFIRMACION_ENTRADA = 1
TRAILING_STOP_PCT = 0.12

# ============================================================
# REGIMEN DE MERCADO Y SIZING DINAMICO
# ============================================================
REGIMEN_AGRESIVO = "AGRESIVO"
REGIMEN_DEFENSIVO = "DEFENSIVO"

FRECUENCIA_REVISION_REGIMEN = "SEMANAL"

PERIODO_SMA200_REGIMEN = 200
VENTANA_RETORNO_63_REGIMEN = 63
VENTANA_CRUCES_SMA50_REGIMEN = 20
UMBRAL_CRUCES_SERRUCHO = 4

SIZING_AGRESIVO_PORCENTAJE_CAPITAL = 0.90
SIZING_AGRESIVO_MAX_UNIDADES = 50

SIZING_DEFENSIVO_PORCENTAJE_CAPITAL = 0.70
SIZING_DEFENSIVO_MAX_UNIDADES = 10

# ============================================================
# NOMBRES INTERNOS DE TABLAS
# ============================================================
NOMBRE_TABLA_OPERACIONES = "operaciones"
NOMBRE_TABLA_RESUMEN_ANUAL = "resumen_anual"

# ============================================================
# COLUMNAS INTERNAS MAESTRAS
# ============================================================
COLUMNAS_OPERACIONES = [
    "version_sistema",
    "fecha_entrada",
    "fecha_salida",
    "precio_entrada",
    "precio_salida",
    "unidades",
    "senal_entrada",
    "motivo_salida",
    "regimen_entrada",
    "regimen_vigente",
    "porcentaje_objetivo_entrada",
    "max_unidades_entrada",
    "capital_objetivo_entrada_eur",
    "capital_invertido_entrada_eur",
    "porcentaje_real_invertido",
    "entrada_capada_por_unidades",
    "beneficio_neto_eur",
    "beneficio_acumulado_eur",
    "rentabilidad_pct",
    "capital_antes_eur",
    "capital_acumulado_eur",
    "maximo_desde_entrada",
    "stop_trailing",
]

COLUMNAS_RESUMEN_ANUAL = [
    "version_sistema",
    "anio",
    "operaciones",
    "ganadoras",
    "perdedoras",
    "win_rate_pct",
    "beneficio_neto_eur",
    "rentabilidad_pct",
    "drawdown_max_pct",
    "operaciones_agresivo",
    "operaciones_defensivo",
    "beneficio_neto_agresivo_eur",
    "beneficio_neto_defensivo_eur",
    "capital_acumulado_eur",
]
