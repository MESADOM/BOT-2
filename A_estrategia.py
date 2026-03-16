from pathlib import Path

# ============================================================
# VERSION INTERNA DEL BOT
# ============================================================
VERSION_BOT = "1.1.0"

# ============================================================
# RUTAS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DIR_DATOS = BASE_DIR / "datos"

RUTA_QQQ = DIR_DATOS / "QQQ.csv"
RUTA_QQQ3 = DIR_DATOS / "QQQ3.csv"
RUTA_VIX = DIR_DATOS / "VIX.csv"

GUARDAR_RESULTADOS = False
RUTA_SALIDA_OPERACIONES = DIR_DATOS / "operaciones_generadas.csv"
RUTA_SALIDA_RESUMEN = DIR_DATOS / "resumen_anual_generado.csv"

# ============================================================
# CAPITAL Y COSTES
# ============================================================
CAPITAL_INICIAL_EUR = 10000.0
COMISION_POR_OPERACION_EUR = 2.0

# ============================================================
# PARAMETROS - BLOQUE 1
# Estrategia base:
# - Señal en QQQ
# - Ejecución en QQQ3
# - Confirmación sobre media larga
# - Salida por trailing o señal OFF
# ============================================================
PERIODO_MEDIA_LARGA = 200
DIAS_CONFIRMACION_ENTRADA = 2
TRAILING_STOP_PCT = 0.12

# Sizing simple pero real
PORCENTAJE_CAPITAL_POR_ENTRADA = 0.95
MAX_UNIDADES_POR_COMPRA = 999999

# ============================================================
# TABLAS / COLUMNAS
# ============================================================
NOMBRE_TABLA_OPERACIONES = "operaciones"
NOMBRE_TABLA_RESUMEN_ANUAL = "resumen_anual"

COLUMNAS_OPERACIONES = [
    "version_bot",
    "fecha_entrada",
    "fecha_salida",
    "precio_entrada",
    "precio_salida",
    "unidades",
    "senal_entrada",
    "motivo_salida",
    "beneficio_neto_eur",
    "rentabilidad_pct",
    "capital_antes_eur",
    "capital_acumulado_eur",
    "maximo_desde_entrada",
    "stop_trailing",
]

COLUMNAS_RESUMEN_ANUAL = [
    "version_bot",
    "anio",
    "operaciones",
    "ganadoras",
    "perdedoras",
    "win_rate_pct",
    "beneficio_neto_eur",
    "rentabilidad_pct",
    "drawdown_max_pct",
]
