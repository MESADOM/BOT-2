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

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from A_configuracion import (
    VERSION_SISTEMA,
    RUTA_QQQ,
    RUTA_QQQ3,
    RUTA_VIX,
    GUARDAR_RESULTADOS,
    RUTA_SALIDA_OPERACIONES,
    RUTA_SALIDA_RESUMEN,
)
from A_estrategia import preparar_datos, ejecutar_estrategia, crear_resumen_anual


def cargar_csv(ruta: Path) -> List[Dict[str, Any]]:
    with open(ruta, 'r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        return [dict(r) for r in reader]


def _guardar_csv(ruta: Path, filas: List[Dict[str, Any]]) -> None:
    if not filas:
        with open(ruta, 'w', encoding='utf-8-sig', newline='') as fh:
            fh.write('')
        return

    columnas = list(filas[0].keys())
    with open(ruta, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas)
        writer.writeheader()
        for fila in filas:
            serializada = {}
            for k, v in fila.items():
                if isinstance(v, datetime):
                    serializada[k] = v.strftime('%Y-%m-%d')
                else:
                    serializada[k] = v
            writer.writerow(serializada)


def ejecutar_bot() -> Dict[str, Any]:
    df_qqq = cargar_csv(RUTA_QQQ)
    df_qqq3 = cargar_csv(RUTA_QQQ3)
    df_vix = cargar_csv(RUTA_VIX)

    df_base = preparar_datos(df_qqq=df_qqq, df_qqq3=df_qqq3, df_vix=df_vix)
    df_operaciones = ejecutar_estrategia(df_base)
    if isinstance(df_operaciones, tuple):
        df_operaciones = df_operaciones[0]
    df_resumen_anual = crear_resumen_anual(df_operaciones)

    if GUARDAR_RESULTADOS:
        _guardar_csv(RUTA_SALIDA_OPERACIONES, df_operaciones)
        _guardar_csv(RUTA_SALIDA_RESUMEN, df_resumen_anual)

    return {
        'version_bot': VERSION_SISTEMA,
        'datos_base': df_base,
        'operaciones': df_operaciones,
        'resumen_anual': df_resumen_anual,
    }


if __name__ == '__main__':
    resultados = ejecutar_bot()

    print(f"Bot ejecutado correctamente. Version: {resultados['version_bot']}")
    print(f"Filas base: {len(resultados['datos_base'])}")
    print(f"Operaciones cerradas: {len(resultados['operaciones'])}")
    print(f"Anios en resumen: {len(resultados['resumen_anual'])}")
