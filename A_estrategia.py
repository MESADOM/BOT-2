from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import pandas as pd

from A_configuracion import (
    VERSION_BOT,
    CAPITAL_INICIAL_EUR,
    COMISION_POR_OPERACION_EUR,
    UMBRAL_SCORE_ENTRADA,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    MAX_DIAS_EN_OPERACION,
    USAR_FILTRO_VIX,
    VIX_MAXIMO_PERMITIDO,
    USAR_FILTRO_TENDENCIA_QQQ,
    PERIODO_MEDIA_CORTA,
    PERIODO_MEDIA_LARGA,
)


@dataclass
class OperacionAbierta:
    fecha_entrada: pd.Timestamp
    precio_entrada: float
    score_entrada: int
    estado_mercado: str
    regimen: str


def preparar_datos(df_qqq: pd.DataFrame, df_qqq3: pd.DataFrame, df_vix: pd.DataFrame) -> pd.DataFrame:
    """
    Unifica y prepara los datos para la estrategia.
    """

    qqq = df_qqq.copy()
    qqq3 = df_qqq3.copy()
    vix = df_vix.copy()

    qqq = _normalizar_columnas(qqq, prefijo="qqq")
    qqq3 = _normalizar_columnas(qqq3, prefijo="qqq3")
    vix = _normalizar_columnas(vix, prefijo="vix")

    df = qqq.merge(qqq3, on="fecha", how="left")
    df = df.merge(vix, on="fecha", how="left")
    df = df.sort_values("fecha").reset_index(drop=True)

    # Indicadores mínimos
    df["qqq_media_corta"] = df["qqq_close"].rolling(PERIODO_MEDIA_CORTA).mean()
    df["qqq_media_larga"] = df["qqq_close"].rolling(PERIODO_MEDIA_LARGA).mean()
    df["qqq_ret_1d"] = df["qqq_close"].pct_change()
    df["qqq_ret_3d"] = df["qqq_close"].pct_change(3)
    df["qqq_ret_5d"] = df["qqq_close"].pct_change(5)

    # Score base provisional
    df["score_entrada"] = df.apply(_calcular_score_fila, axis=1)

    # Contexto
    df["estado_mercado"] = df.apply(_calcular_estado_mercado, axis=1)
    df["regimen"] = df.apply(_calcular_regimen, axis=1)

    return df


def ejecutar_estrategia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre el histórico y genera operaciones cerradas.
    """
    capital_actual = float(CAPITAL_INICIAL_EUR)
    operacion_abierta: Optional[OperacionAbierta] = None
    operaciones: List[Dict[str, Any]] = []

    for i, fila in df.iterrows():
        fecha = fila["fecha"]
        precio_actual = float(fila["qqq_close"])

        if pd.isna(precio_actual):
            continue

        if operacion_abierta is None:
            if _debe_entrar(fila):
                operacion_abierta = OperacionAbierta(
                    fecha_entrada=fecha,
                    precio_entrada=precio_actual,
                    score_entrada=int(fila["score_entrada"]),
                    estado_mercado=str(fila["estado_mercado"]),
                    regimen=str(fila["regimen"]),
                )
        else:
            salida = _evaluar_salida(operacion_abierta, fila)

            if salida["cerrar"]:
                precio_salida = precio_actual
                beneficio_bruto = precio_salida - operacion_abierta.precio_entrada
                beneficio_neto = beneficio_bruto - COMISION_POR_OPERACION_EUR
                rentabilidad_pct = 0.0
                if operacion_abierta.precio_entrada != 0:
                    rentabilidad_pct = (beneficio_neto / operacion_abierta.precio_entrada) * 100.0

                capital_actual += beneficio_neto

                operaciones.append(
                    {
                        "version_bot": VERSION_BOT,
                        "fecha_entrada": operacion_abierta.fecha_entrada,
                        "fecha_salida": fecha,
                        "precio_entrada": round(operacion_abierta.precio_entrada, 6),
                        "precio_salida": round(precio_salida, 6),
                        "score_entrada": operacion_abierta.score_entrada,
                        "estado_mercado": operacion_abierta.estado_mercado,
                        "regimen": operacion_abierta.regimen,
                        "motivo_salida": salida["motivo"],
                        "beneficio_neto_eur": round(beneficio_neto, 2),
                        "rentabilidad_pct": round(rentabilidad_pct, 4),
                        "capital_acumulado_eur": round(capital_actual, 2),
                    }
                )

                operacion_abierta = None

    df_operaciones = pd.DataFrame(operaciones)

    if not df_operaciones.empty:
        df_operaciones = df_operaciones.sort_values("fecha_salida").reset_index(drop=True)

    return df_operaciones


def crear_resumen_anual(df_operaciones: pd.DataFrame) -> pd.DataFrame:
    """
    Genera el resumen anual a partir de las operaciones cerradas.
    """
    if df_operaciones.empty:
        return pd.DataFrame(
            columns=[
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
        )

    df = df_operaciones.copy()
    df["anio"] = pd.to_datetime(df["fecha_salida"]).dt.year
    df["ganadora"] = df["beneficio_neto_eur"] > 0
    df["perdedora"] = df["beneficio_neto_eur"] <= 0

    resumen = (
        df.groupby("anio", as_index=False)
        .agg(
            operaciones=("beneficio_neto_eur", "count"),
            ganadoras=("ganadora", "sum"),
            perdedoras=("perdedora", "sum"),
            beneficio_neto_eur=("beneficio_neto_eur", "sum"),
        )
        .sort_values("anio")
        .reset_index(drop=True)
    )

    resumen["win_rate_pct"] = (
        resumen["ganadoras"] / resumen["operaciones"] * 100.0
    ).round(4)

    resumen["rentabilidad_pct"] = (
        resumen["beneficio_neto_eur"] / CAPITAL_INICIAL_EUR * 100.0
    ).round(4)

    drawdowns = []
    for anio in resumen["anio"]:
        df_anio = df[df["anio"] == anio].copy()
        curva = df_anio["capital_acumulado_eur"].astype(float)
        pico = curva.cummax()
        dd = ((curva - pico) / pico.replace(0, pd.NA)) * 100.0
        drawdowns.append(round(float(dd.min()) if not dd.empty else 0.0, 4))

    resumen["drawdown_max_pct"] = drawdowns
    resumen.insert(0, "version_bot", VERSION_BOT)

    return resumen


# ============================================================
# FUNCIONES INTERNAS
# ============================================================

def _normalizar_columnas(df: pd.DataFrame, prefijo: str) -> pd.DataFrame:
    df = df.copy()

    # Limpieza básica de nombres
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Intento de mapear nombres comunes
    mapa = {}

    for col in df.columns:
        if col in ["date", "fecha"]:
            mapa[col] = "fecha"
        elif col in ["close", "adj close", "adj_close", "cierre"]:
            mapa[col] = f"{prefijo}_close"
        elif col in ["open", "apertura"]:
            mapa[col] = f"{prefijo}_open"
        elif col in ["high", "max", "alto"]:
            mapa[col] = f"{prefijo}_high"
        elif col in ["low", "min", "bajo"]:
            mapa[col] = f"{prefijo}_low"
        elif col in ["volume", "volumen"]:
            mapa[col] = f"{prefijo}_volume"

    df = df.rename(columns=mapa)

    if "fecha" not in df.columns:
        raise ValueError(f"No se encontró columna de fecha en {prefijo}")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)

    return df


def _calcular_score_fila(fila: pd.Series) -> int:
    """
    Score provisional y editable.
    Aquí es donde luego meteremos tu score real.
    """
    score = 0

    if pd.notna(fila.get("qqq_ret_1d")) and fila["qqq_ret_1d"] > 0:
        score += 2

    if pd.notna(fila.get("qqq_ret_3d")) and fila["qqq_ret_3d"] > 0:
        score += 2

    if pd.notna(fila.get("qqq_ret_5d")) and fila["qqq_ret_5d"] > 0:
        score += 2

    if pd.notna(fila.get("qqq_media_corta")) and pd.notna(fila.get("qqq_media_larga")):
        if fila["qqq_media_corta"] > fila["qqq_media_larga"]:
            score += 2

    if pd.notna(fila.get("vix_close")):
        if fila["vix_close"] < 20:
            score += 2
        elif fila["vix_close"] < 28:
            score += 1

    return int(score)


def _calcular_estado_mercado(fila: pd.Series) -> str:
    if pd.isna(fila.get("qqq_media_corta")) or pd.isna(fila.get("qqq_media_larga")):
        return "SIN_DATOS"

    if fila["qqq_media_corta"] > fila["qqq_media_larga"]:
        return "ALCISTA"

    return "BAJISTA"


def _calcular_regimen(fila: pd.Series) -> str:
    vix = fila.get("vix_close", pd.NA)
    estado = _calcular_estado_mercado(fila)

    if pd.isna(vix):
        return "SIN_VIX"

    if estado == "ALCISTA" and vix < 18:
        return "TREND_LOWVOL"
    if estado == "ALCISTA" and vix >= 18:
        return "TREND_HIGHVOL"
    if estado == "BAJISTA" and vix >= 25:
        return "BEAR_HIGHVOL"
    return "CHOP"


def _debe_entrar(fila: pd.Series) -> bool:
    if pd.isna(fila.get("score_entrada")) or pd.isna(fila.get("qqq_close")):
        return False

    if int(fila["score_entrada"]) < UMBRAL_SCORE_ENTRADA:
        return False

    if USAR_FILTRO_VIX:
        vix = fila.get("vix_close", pd.NA)
        if pd.notna(vix) and float(vix) > VIX_MAXIMO_PERMITIDO:
            return False

    if USAR_FILTRO_TENDENCIA_QQQ:
        mc = fila.get("qqq_media_corta", pd.NA)
        ml = fila.get("qqq_media_larga", pd.NA)
        if pd.isna(mc) or pd.isna(ml) or float(mc) <= float(ml):
            return False

    return True


def _evaluar_salida(operacion: OperacionAbierta, fila: pd.Series) -> Dict[str, Any]:
    precio_actual = float(fila["qqq_close"])
    fecha_actual = pd.to_datetime(fila["fecha"])

    variacion = 0.0
    if operacion.precio_entrada != 0:
        variacion = (precio_actual / operacion.precio_entrada) - 1.0

    dias_en_operacion = (fecha_actual - operacion.fecha_entrada).days

    if variacion <= -STOP_LOSS_PCT:
        return {"cerrar": True, "motivo": "STOP_LOSS"}

    if variacion >= TAKE_PROFIT_PCT:
        return {"cerrar": True, "motivo": "TAKE_PROFIT"}

    if dias_en_operacion >= MAX_DIAS_EN_OPERACION:
        return {"cerrar": True, "motivo": "TIME_EXIT"}

    return {"cerrar": False, "motivo": ""}