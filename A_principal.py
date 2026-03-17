from A_configuracion import RUTA_QQQ, RUTA_QQQ3, RUTA_VIX, VERSION_SISTEMA
from A_mercado import cargar_csv
from A_estrategia import preparar_datos, ejecutar_estrategia, crear_resumen_anual


def main():
    df_qqq = cargar_csv(RUTA_QQQ)
    df_qqq3 = cargar_csv(RUTA_QQQ3)
    df_vix = cargar_csv(RUTA_VIX)

    df_base = preparar_datos(df_qqq=df_qqq, df_qqq3=df_qqq3, df_vix=df_vix, modo_selector="AUTO")
    resultado = ejecutar_estrategia(df_base)

    if isinstance(resultado, tuple):
        operaciones = resultado[0]
    else:
        operaciones = resultado

    resumen_anual = crear_resumen_anual(operaciones)

    return {
        "version_sistema": VERSION_SISTEMA,
        "operaciones": operaciones,
        "resumen_anual": resumen_anual,
    }


if __name__ == "__main__":
    main()
