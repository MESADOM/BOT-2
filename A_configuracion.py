from pathlib import Path

# ============================================================
# VERSION INTERNA DEL BOT
# Formato: P.C.E
# P = 00_principal.py
# C = 00_configuracion.py
# E = 00_estrategia.py
# ============================================================
VERSION_BOT = "1.0.0"

# ============================================================
# RUTAS
# Ajusta estos nombres si tus CSV tienen otro nombre o ubicación
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
CAPITAL_INICIAL_EUR = 10000.0
COMISION_POR_OPERACION_EUR = 2.0

# ============================================================
# PARAMETROS DE ESTRATEGIA
# IMPORTANTE:
# Estos son valores base para dejar la estructura hecha.
# Aquí es donde luego ajustaremos tu estrategia real.
# ============================================================
UMBRAL_SCORE_ENTRADA = 6
STOP_LOSS_PCT = 0.07
TAKE_PROFIT_PCT = 0.12
MAX_DIAS_EN_OPERACION = 20

# Filtros base
USAR_FILTRO_VIX = True
VIX_MAXIMO_PERMITIDO = 28.0

USAR_FILTRO_TENDENCIA_QQQ = True
PERIODO_MEDIA_CORTA = 20
PERIODO_MEDIA_LARGA = 50

# ============================================================
# NOMBRES INTERNOS DE TABLAS
# ============================================================
NOMBRE_TABLA_OPERACIONES = "operaciones"
NOMBRE_TABLA_RESUMEN_ANUAL = "resumen_anual"

# ============================================================
# COLUMNAS INTERNAS MAESTRAS
# ============================================================
COLUMNAS_OPERACIONES = [
    "version_bot",
    "fecha_entrada",
    "fecha_salida",
    "precio_entrada",
    "precio_salida",
    "score_entrada",
    "estado_mercado",
    "regimen",
    "motivo_salida",
    "beneficio_neto_eur",
    "rentabilidad_pct",
    "capital_acumulado_eur",
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