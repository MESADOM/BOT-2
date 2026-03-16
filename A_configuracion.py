# ============================================================
# SISTEMA DE VERSIONADO
# Formato: P.C.E
# P = version de A_principal.py
# C = version de A_configuracion.py
# E = version de A_estrategia.py
#
# Version actual: 1.1.2
# Fecha: 2026-03-16
# ============================================================

VERSION_SISTEMA = "1.1.2"
VERSION_PRINCIPAL = 1
VERSION_CONFIGURACION = 1
VERSION_ESTRATEGIA = 2
VERSION_BOT = VERSION_SISTEMA

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIR_DATOS = BASE_DIR / "datos"

RUTA_QQQ = DIR_DATOS / "QQQ.csv"
RUTA_QQQ3 = DIR_DATOS / "QQQ3.csv"
RUTA_VIX = DIR_DATOS / "VIX.csv"

GUARDAR_RESULTADOS = False
RUTA_SALIDA_OPERACIONES = DIR_DATOS / "operaciones_generadas.csv"
RUTA_SALIDA_RESUMEN = DIR_DATOS / "resumen_anual_generado.csv"

CAPITAL_INICIAL_EUR = 1000.0
COMISION_POR_OPERACION_EUR = 2.0

PORCENTAJE_CAPITAL_POR_ENTRADA = 0.60
MAX_UNIDADES_POR_COMPRA = 4

PERIODO_MEDIA_LARGA = 50
DIAS_CONFIRMACION_ENTRADA = 2
TRAILING_STOP_PCT = 0.12

NOMBRE_TABLA_OPERACIONES = "operaciones"
NOMBRE_TABLA_RESUMEN_ANUAL = "resumen_anual"

COLUMNAS_OPERACIONES = [
    "version_sistema",
    "fecha_entrada",
    "fecha_salida",
    "precio_entrada",
    "precio_salida",
    "unidades",
    "senal_entrada",
    "motivo_salida",
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
]
