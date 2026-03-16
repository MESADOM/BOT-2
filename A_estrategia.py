from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import math

from A_configuracion import (
    VERSION_SISTEMA,
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
    fecha_entrada: datetime
    precio_entrada: float
    unidades: int
    capital_antes_eur: float
    maximo_desde_entrada: float
    senal_entrada: str


def preparar_datos(df_qqq: List[Dict[str, Any]], df_qqq3: List[Dict[str, Any]], df_vix: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    qqq_por_fecha = {r['fecha']: r for r in df_qqq}
    qqq3_por_fecha = {r['fecha']: r for r in df_qqq3}
    vix_por_fecha = {r['fecha']: r for r in df_vix}

    fechas = sorted(set(qqq_por_fecha) | set(qqq3_por_fecha) | set(vix_por_fecha))
    filas: List[Dict[str, Any]] = []

    closes_qqq: List[Optional[float]] = []
    n_confirm = max(1, int(DIAS_CONFIRMACION_ENTRADA))

    for fecha in fechas:
        qqq = qqq_por_fecha.get(fecha, {})
        qqq3 = qqq3_por_fecha.get(fecha, {})
        vix = vix_por_fecha.get(fecha, {})

        close_qqq = qqq.get('close')
        closes_qqq.append(close_qqq)

        media_larga = None
        ultimos = [x for x in closes_qqq[-PERIODO_MEDIA_LARGA:] if x is not None]
        if len(ultimos) == PERIODO_MEDIA_LARGA:
            media_larga = sum(ultimos) / PERIODO_MEDIA_LARGA

        senal_base_on = bool(close_qqq is not None and media_larga is not None and close_qqq > media_larga)
        prev = [f['senal_base_on'] for f in filas[-(n_confirm - 1):]] if n_confirm > 1 else []
        senal_confirmada = all(prev + [senal_base_on]) and (len(prev) + 1 == n_confirm)

        filas.append(
            {
                'fecha': fecha,
                'qqq_close': close_qqq,
                'qqq3_close': qqq3.get('close'),
                'vix_close': vix.get('close'),
                'qqq_media_larga': media_larga,
                'senal_base_on': senal_base_on,
                'senal_confirmada': senal_confirmada,
            }
        )

    return filas


def ejecutar_estrategia(df: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    capital_actual = float(CAPITAL_INICIAL_EUR)
    operacion_abierta: Optional[OperacionAbierta] = None
    operaciones: List[Dict[str, Any]] = []

    for fila in df:
        fecha = fila['fecha']
        precio_senal = fila.get('qqq_close')
        precio_operativo = fila.get('qqq3_close')
        senal_confirmada = bool(fila.get('senal_confirmada', False))
        senal_base_on = bool(fila.get('senal_base_on', False))

        if precio_senal is None or precio_operativo is None:
            continue

        if operacion_abierta is None:
            if senal_confirmada:
                presupuesto = capital_actual * float(PORCENTAJE_CAPITAL_POR_ENTRADA)
                unidades = int(math.floor(presupuesto / precio_operativo)) if precio_operativo > 0 else 0
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
        else:
            operacion_abierta.maximo_desde_entrada = max(operacion_abierta.maximo_desde_entrada, precio_operativo)
            stop_trailing = operacion_abierta.maximo_desde_entrada * (1.0 - TRAILING_STOP_PCT)

            cerrar = False
            motivo_salida = ''
            if precio_operativo <= stop_trailing:
                cerrar = True
                motivo_salida = 'SELL_TRAILING'
            elif not senal_base_on:
                cerrar = True
                motivo_salida = 'SELL_SIGNAL'

            if cerrar:
                beneficio_bruto = (precio_operativo - operacion_abierta.precio_entrada) * operacion_abierta.unidades
                beneficio_neto = beneficio_bruto - COMISION_POR_OPERACION_EUR
                rentabilidad_pct = (beneficio_neto / operacion_abierta.capital_antes_eur * 100.0) if operacion_abierta.capital_antes_eur > 0 else 0.0
                capital_actual += beneficio_neto
                beneficio_acumulado = capital_actual - CAPITAL_INICIAL_EUR

                operaciones.append(
                    {
                        'version_sistema': VERSION_SISTEMA,
                        'fecha_entrada': operacion_abierta.fecha_entrada,
                        'fecha_salida': fecha,
                        'senal_entrada': operacion_abierta.senal_entrada,
                        'motivo_salida': motivo_salida,
                        'beneficio_neto_eur': round(beneficio_neto, 2),
                        'rentabilidad_pct': round(rentabilidad_pct, 4),
                        'capital_acumulado_eur': round(capital_actual, 2),
                        'beneficio_acumulado_eur': round(beneficio_acumulado, 2),
                    }
                )
                operacion_abierta = None

    operaciones.sort(key=lambda x: x['fecha_salida'])
    return operaciones


def crear_resumen_anual(df_operaciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agrupado: Dict[int, Dict[str, Any]] = {}
    for op in df_operaciones:
        anio = op['fecha_salida'].year
        g = agrupado.setdefault(anio, {'anio': anio, 'operaciones': 0, 'ganadoras': 0, 'perdedoras': 0, 'beneficio_neto_eur': 0.0, 'drawdown_max_pct': 0.0})
        g['operaciones'] += 1
        if op['beneficio_neto_eur'] > 0:
            g['ganadoras'] += 1
        else:
            g['perdedoras'] += 1
        g['beneficio_neto_eur'] += op['beneficio_neto_eur']

    resumen = []
    for anio in sorted(agrupado):
        g = agrupado[anio]
        ops_anio = [op for op in df_operaciones if op['fecha_salida'].year == anio]
        pico = None
        dd_min = 0.0
        for op in ops_anio:
            cap = float(op['capital_acumulado_eur'])
            pico = cap if pico is None else max(pico, cap)
            dd = ((cap - pico) / pico * 100.0) if pico else 0.0
            dd_min = min(dd_min, dd)

        resumen.append(
            {
                'version_sistema': VERSION_SISTEMA,
                'anio': anio,
                'operaciones': g['operaciones'],
                'ganadoras': g['ganadoras'],
                'perdedoras': g['perdedoras'],
                'win_rate_pct': round((g['ganadoras'] / g['operaciones'] * 100.0) if g['operaciones'] else 0.0, 4),
                'beneficio_neto_eur': round(g['beneficio_neto_eur'], 2),
                'rentabilidad_pct': round(g['beneficio_neto_eur'] / CAPITAL_INICIAL_EUR * 100.0, 4),
                'drawdown_max_pct': round(dd_min, 4),
            }
        )

    return resumen
