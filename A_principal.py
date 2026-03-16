from __future__ import annotations

import pandas as pd

from A_configuracion import (
    VERSION_BOT,
    RUTA_QQQ,
    RUTA_QQQ3,
    RUTA_VIX,
    GUARDAR_RESULTADOS,
    RUTA_SALIDA_OPERACIONES,
    RUTA_SALIDA_RESUMEN,
)
from A_estrategia import preparar_datos, ejecutar_estrategia, crear_resumen_anual


def cargar_csv(ruta) -> pd.DataFrame:
    return pd.read_csv(ruta)


def ejecutar_bot():
    # 1) Carga
    df_qqq = cargar_csv(RUTA_QQQ)
    df_qqq3 = cargar_csv(RUTA_QQQ3)
    df_vix = cargar_csv(RUTA_VIX)

    # 2) Preparacion de datos
    df_base = preparar_datos(df_qqq=df_qqq, df_qqq3=df_qqq3, df_vix=df_vix)

    # 3) Ejecucion estrategia
    df_operaciones = ejecutar_estrategia(df_base)

    # 4) Resumen anual
    df_resumen_anual = crear_resumen_anual(df_operaciones)

    # 5) Guardado opcional
    if GUARDAR_RESULTADOS:
        df_operaciones.to_csv(RUTA_SALIDA_OPERACIONES, index=False, encoding="utf-8-sig")
        df_resumen_anual.to_csv(RUTA_SALIDA_RESUMEN, index=False, encoding="utf-8-sig")

    return {
        "version_bot": VERSION_BOT,
        "datos_base": df_base,
        "operaciones": df_operaciones,
        "resumen_anual": df_resumen_anual,
    }


if __name__ == "__main__":
    resultados = ejecutar_bot()

    print(f"Bot ejecutado correctamente. Version: {resultados['version_bot']}")
    print(f"Filas base: {len(resultados['datos_base'])}")
    print(f"Operaciones cerradas: {len(resultados['operaciones'])}")
    print(f"Anios en resumen: {len(resultados['resumen_anual'])}")