# ============================================================
# SISTEMA DE VERSIONADO
# Formato: P.C.E
# P = version de A_principal.py
# C = version de A_configuracion.py
# E = version de A_estrategia.py
#
# Version actual: 1.1.1
# Fecha: 2026-03-16
#
# Cambios en esta version:
# - Se elimina la logica provisional basada en score
# - Se elimina stop loss fijo, take profit y time exit
# - La estrategia pasa a una base simple y trazable:
#   * señal con QQQ > media larga
#   * confirmacion de entrada
#   * ejecucion sobre QQQ3
#   * una sola posicion
#   * salida por trailing stop o perdida de señal
# - Se añade sizing real por unidades
#
# Historial:
# 1.0.0
# - Estrategia inicial del nuevo bot con score y salidas mixtas
#
# 1.1.1
# - Estrategia reducida al nucleo que queremos validar antes de seguir complicando
# - Base preparada para comparar despues con paper y real
# ============================================================

VERSION_SISTEMA = "1.1.1"
VERSION_PRINCIPAL = 1
VERSION_CONFIGURACION = 1
VERSION_ESTRATEGIA = 1

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import math
import pandas as pd

from A_configuracion import (
    VERSION_BOT,
    CAPITAL_INICIAL_EUR,
    COMISION_POR_OPERACION_EUR,
    PERIODO_MEDIA_LARGA,
    DIAS_CONFIRMACION_ENTRADA,
    TRAILING_STOP_PCT,
    PORCENTAJE_CAPITAL_POR_ENTRADA,
    MAX_UNIDADES_POR_COMPRA,
)


@dataclass
class OperacionAbierta:
    fecha_entrada: pd.Timestamp
    precio_entrada: float
    unidades: int
    capital_antes_eur: float
    maximo_desde_entrada: float
    senal_entrada: str


def preparar_datos(df_qqq: pd.DataFrame, df_qqq3: pd.DataFrame, df_vix: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara datos base.
    - Señal en QQQ
    - Ejecución en QQQ3
    """
    qqq = _normalizar_columnas(df_qqq.copy(), prefijo="qqq")
    qqq3 = _normalizar_columnas(df_qqq3.copy(), prefijo="qqq3")
    vix = _normalizar_columnas(df_vix.copy(), prefijo="vix")

    df = qqq.merge(qqq3, on="fecha", how="left")
    df = df.merge(vix, on="fecha", how="left")
    df = df.sort_values("fecha").reset_index(drop=True)

    # Media larga de señal
    df["qqq_media_larga"] = df["qqq_close"].rolling(PERIODO_MEDIA_LARGA).mean()

    # Señal diaria base
    df["senal_base_on"] = (
        pd.notna(df["qqq_close"])
        & pd.notna(df["qqq_media_larga"])
        & (df["qqq_close"] > df["qqq_media_larga"])
    )

    # Confirmación: N cierres consecutivos por encima de la media larga
    n = max(1, int(DIAS_CONFIRMACION_ENTRADA))
    df["senal_confirmada"] = (
        df["senal_base_on"]
        .rolling(n, min_periods=n)
        .sum()
        .eq(n)
    )

    return df


def ejecutar_estrategia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre el histórico y genera operaciones cerradas.
    Lógica Bloque 1:
    - Entrada: señal confirmada ON y sin posición
    - Salida: trailing stop o señal OFF
    - PnL: sobre QQQ3 y con unidades reales
    """
    capital_actual = float(CAPITAL_INICIAL_EUR)
    operacion_abierta: Optional[OperacionAbierta] = None
    operaciones: List[Dict[str, Any]] = []

    for _, fila in df.iterrows():
        fecha = fila["fecha"]

        precio_senal = fila.get("qqq_close", pd.NA)
        precio_operativo = fila.get("qqq3_close", pd.NA)
        senal_confirmada = bool(fila.get("senal_confirmada", False))
        senal_base_on = bool(fila.get("senal_base_on", False))

        if pd.isna(precio_senal) or pd.isna(precio_operativo):
            continue

        precio_operativo = float(precio_operativo)

        # ======================================================
        # SIN POSICIÓN -> evaluar entrada
        # ======================================================
        if operacion_abierta is None:
            if senal_confirmada:
                presupuesto = capital_actual * float(PORCENTAJE_CAPITAL_POR_ENTRADA)
                unidades = 0
                if precio_operativo > 0:
                    unidades = int(math.floor(presupuesto / precio_operativo))

                unidades = max(0, min(unidades, int(MAX_UNIDADES_POR_COMPRA)))

                coste_entrada = unidades * precio_operativo + COMISION_POR_OPERACION_EUR

                if unidades > 0 and coste_entrada <= capital_actual:
                    operacion_abierta = OperacionAbierta(
                        fecha_entrada=fecha,
                        precio_entrada=precio_operativo,
                        unidades=unidades,
                        capital_antes_eur=capital_actual,
                        maximo_desde_entrada=precio_operativo,
                        senal_entrada=f"QQQ>SMA{PERIODO_MEDIA_LARGA} x{DIAS_CONFIRMACION_ENTRADA}",
                    )

        # ======================================================
        # CON POSICIÓN -> actualizar trailing y evaluar salida
        # ======================================================
        else:
            operacion_abierta.maximo_desde_entrada = max(
                operacion_abierta.maximo_desde_entrada,
                precio_operativo,
            )

            stop_trailing = operacion_abierta.maximo_desde_entrada * (1.0 - TRAILING_STOP_PCT)

            cerrar = False
            motivo_salida = ""

            # Prioridad 1: trailing
            if precio_operativo <= stop_trailing:
                cerrar = True
                motivo_salida = "SELL_TRAILING"

            # Prioridad 2: señal OFF
            elif not senal_base_on:
                cerrar = True
                motivo_salida = "SELL_SIGNAL"

            if cerrar:
                precio_salida = precio_operativo

                beneficio_bruto = (precio_salida - operacion_abierta.precio_entrada) * operacion_abierta.unidades
                beneficio_neto = beneficio_bruto - COMISION_POR_OPERACION_EUR

                rentabilidad_pct = 0.0
                if operacion_abierta.capital_antes_eur > 0:
                    rentabilidad_pct = (beneficio_neto / operacion_abierta.capital_antes_eur) * 100.0

                capital_actual += beneficio_neto
                beneficio_acumulado_eur = capital_actual - CAPITAL_INICIAL_EUR

                operaciones.append(
                    {
                        "version_bot": VERSION_BOT,
                        "fecha_entrada": operacion_abierta.fecha_entrada,
                        "fecha_salida": fecha,
                        "precio_entrada": round(operacion_abierta.precio_entrada, 6),
                        "precio_salida": round(precio_salida, 6),
                        "unidades": int(operacion_abierta.unidades),
                        "senal_entrada": operacion_abierta.senal_entrada,
                        "motivo_salida": motivo_salida,
                        "beneficio_neto_eur": round(beneficio_neto, 2),
                        "rentabilidad_pct": round(rentabilidad_pct, 4),
                        "capital_antes_eur": round(operacion_abierta.capital_antes_eur, 2),
                        "beneficio_acumulado_eur": round(beneficio_acumulado_eur, 2),
                        "capital_acumulado_eur": round(capital_actual, 2),
                        "maximo_desde_entrada": round(operacion_abierta.maximo_desde_entrada, 6),
                        "stop_trailing": round(stop_trailing, 6),
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

    df.columns = [str(c).strip().lower() for c in df.columns]
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
