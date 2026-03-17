# ============================================================
# SISTEMA DE VERSIONADO
# Formato: P.C.E
# P = version de A_principal.py
# C = version de A_configuracion.py
# E = version de A_estrategia.py
#
# Version actual: 1.1.2 
# Fecha: 2026-03-16
#
# Cambios en esta version:
# - Se mejora el backtest para separar decision y ejecucion
# - La señal se decide con el cierre del dia actual
# - La entrada se ejecuta al open del dia siguiente
# - La salida se ejecuta al open del dia siguiente
# - El trailing sigue evaluandose con el cierre, pero ya no se ejecuta en la misma barra
# - Se mantiene la logica simple para seguir validando el sistema por bloques
#
# Historial:
# 1.0.0
# - Estrategia inicial del nuevo bot con score y salidas mixtas
#
# 1.1.1
# - Estrategia reducida al nucleo que queremos validar antes de seguir complicando
# - Señal simple con QQQ y ejecucion sobre QQQ3
#
# 1.1.2
# - Se hace mas realista la simulacion desplazando la ejecucion al siguiente dia
# - Primera mejora fuerte orientada a acercar backtest y paper/live
# ============================================================

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterable

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


def _parse_num_es(value: str) -> float:
    value = str(value).strip().replace('.', '').replace(',', '.')
    return float(value)


def _to_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _normalizar_columnas(rows: Iterable[Dict[str, Any]], prefijo: str) -> List[Dict[str, Any]]:
    normalizadas: List[Dict[str, Any]] = []

    for raw in rows:
        row = {str(k).strip().lower(): v for k, v in raw.items()}

        if prefijo == 'qqq' and len(row) == 1:
            unico = next(iter(row.values()))
            campos = next(csv.reader([str(unico)]))
            if len(campos) >= 5:
                normalizadas.append(
                    {
                        'fecha': _to_datetime(campos[0]),
                        f'{prefijo}_close': float(campos[1]),
                        f'{prefijo}_open': float(campos[2]),
                        f'{prefijo}_high': float(campos[3]),
                        f'{prefijo}_low': float(campos[4]),
                    }
                )
            continue

        out: Dict[str, Any] = {}
        for col, val in row.items():
            if col in ['date', 'fecha', '"fecha"', '"date']:
                out['fecha'] = _to_datetime(val)
            elif col in ['close', 'adj close', 'adj_close', 'cierre', 'último', 'ultimo']:
                if prefijo == 'qqq':
                    out[f'{prefijo}_close'] = float(str(val).replace(',', '.'))
                else:
                    out[f'{prefijo}_close'] = _parse_num_es(val)
            elif col in ['open', 'apertura']:
                if prefijo == 'qqq':
                    out[f'{prefijo}_open'] = float(str(val).replace(',', '.'))
                else:
                    out[f'{prefijo}_open'] = _parse_num_es(val)
            elif col in ['high', 'max', 'alto', 'máximo']:
                if prefijo == 'qqq':
                    out[f'{prefijo}_high'] = float(str(val).replace(',', '.'))
                else:
                    out[f'{prefijo}_high'] = _parse_num_es(val)
            elif col in ['low', 'min', 'bajo', 'mínimo']:
                if prefijo == 'qqq':
                    out[f'{prefijo}_low'] = float(str(val).replace(',', '.'))
                else:
                    out[f'{prefijo}_low'] = _parse_num_es(val)

        if out.get('fecha') is not None:
            normalizadas.append(out)

    normalizadas.sort(key=lambda x: x['fecha'])
    return normalizadas


def preparar_datos(df_qqq: List[Dict[str, Any]], df_qqq3: List[Dict[str, Any]], df_vix: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    qqq = _normalizar_columnas(df_qqq, prefijo='qqq')
    qqq3 = _normalizar_columnas(df_qqq3, prefijo='qqq3')
    _ = _normalizar_columnas(df_vix, prefijo='vix')

    map_qqq = {r['fecha']: r for r in qqq}
    map_qqq3 = {r['fecha']: r for r in qqq3}
    fechas = sorted(set(map_qqq.keys()) | set(map_qqq3.keys()))

    rows: List[Dict[str, Any]] = []
    closes: List[float] = []
    ultimas_senales: List[bool] = []
    n = max(1, int(DIAS_CONFIRMACION_ENTRADA))

    for fecha in fechas:
        row = {
            'fecha': fecha,
            'qqq_close': map_qqq.get(fecha, {}).get('qqq_close'),
            'qqq3_close': map_qqq3.get(fecha, {}).get('qqq3_close'),
            'qqq3_open': map_qqq3.get(fecha, {}).get('qqq3_open'),
        }

        close = row['qqq_close']
        if close is None:
            row['qqq_media_larga'] = None
            row['senal_base_on'] = False
        else:
            closes.append(float(close))
            if len(closes) >= PERIODO_MEDIA_LARGA:
                media = sum(closes[-PERIODO_MEDIA_LARGA:]) / PERIODO_MEDIA_LARGA
                row['qqq_media_larga'] = media
                row['senal_base_on'] = float(close) > media
            else:
                row['qqq_media_larga'] = None
                row['senal_base_on'] = False

        ultimas_senales.append(bool(row['senal_base_on']))
        if len(ultimas_senales) > n:
            ultimas_senales.pop(0)
        row['senal_confirmada'] = len(ultimas_senales) == n and all(ultimas_senales)

        rows.append(row)

    return rows


def ejecutar_estrategia(df: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    capital_actual = float(CAPITAL_INICIAL_EUR)
    operacion_abierta: Optional[OperacionAbierta] = None
    operaciones: List[Dict[str, Any]] = []

    entrada_pendiente = False
    salida_pendiente = False
    motivo_salida_pendiente = ''

    for i in range(len(df) - 1):
        hoy = df[i]
        manana = df[i + 1]

        qqq_close_hoy = hoy.get('qqq_close')
        qqq3_close_hoy = hoy.get('qqq3_close')
        qqq3_open_manana = manana.get('qqq3_open')

        if qqq_close_hoy is None or qqq3_close_hoy is None or qqq3_open_manana is None:
            continue

        qqq3_close_hoy = float(qqq3_close_hoy)
        qqq3_open_manana = float(qqq3_open_manana)

        if salida_pendiente and operacion_abierta is not None:
            precio_salida = qqq3_open_manana
            beneficio_bruto = (precio_salida - operacion_abierta.precio_entrada) * operacion_abierta.unidades
            beneficio_neto = beneficio_bruto - COMISION_POR_OPERACION_EUR

            rentabilidad_pct = 0.0
            if operacion_abierta.capital_antes_eur > 0:
                rentabilidad_pct = (beneficio_neto / operacion_abierta.capital_antes_eur) * 100.0

            capital_actual += beneficio_neto
            beneficio_acumulado_eur = capital_actual - CAPITAL_INICIAL_EUR
            stop_trailing = operacion_abierta.maximo_desde_entrada * (1.0 - TRAILING_STOP_PCT)

            operaciones.append(
                {
                    'version_sistema': VERSION_SISTEMA,
                    'fecha_entrada': operacion_abierta.fecha_entrada,
                    'fecha_salida': manana['fecha'],
                    'precio_entrada': round(operacion_abierta.precio_entrada, 6),
                    'precio_salida': round(precio_salida, 6),
                    'unidades': int(operacion_abierta.unidades),
                    'senal_entrada': operacion_abierta.senal_entrada,
                    'motivo_salida': motivo_salida_pendiente,
                    'beneficio_neto_eur': round(beneficio_neto, 2),
                    'beneficio_acumulado_eur': round(beneficio_acumulado_eur, 2),
                    'rentabilidad_pct': round(rentabilidad_pct, 4),
                    'capital_antes_eur': round(operacion_abierta.capital_antes_eur, 2),
                    'capital_acumulado_eur': round(capital_actual, 2),
                    'maximo_desde_entrada': round(operacion_abierta.maximo_desde_entrada, 6),
                    'stop_trailing': round(stop_trailing, 6),
                }
            )

            operacion_abierta = None
            salida_pendiente = False
            motivo_salida_pendiente = ''

        if entrada_pendiente and operacion_abierta is None:
            presupuesto = capital_actual * float(PORCENTAJE_CAPITAL_POR_ENTRADA)
            unidades = int(math.floor(presupuesto / qqq3_open_manana)) if qqq3_open_manana > 0 else 0
            unidades = max(0, min(unidades, int(MAX_UNIDADES_POR_COMPRA)))
            coste_entrada = unidades * qqq3_open_manana + COMISION_POR_OPERACION_EUR

            if unidades > 0 and coste_entrada <= capital_actual:
                operacion_abierta = OperacionAbierta(
                    fecha_entrada=manana['fecha'],
                    precio_entrada=qqq3_open_manana,
                    unidades=unidades,
                    capital_antes_eur=capital_actual,
                    maximo_desde_entrada=qqq3_open_manana,
                    senal_entrada=f'QQQ>SMA{PERIODO_MEDIA_LARGA} x{DIAS_CONFIRMACION_ENTRADA}',
                )

            entrada_pendiente = False

        if operacion_abierta is None:
            if bool(hoy.get('senal_confirmada', False)):
                entrada_pendiente = True
        else:
            operacion_abierta.maximo_desde_entrada = max(operacion_abierta.maximo_desde_entrada, qqq3_close_hoy)
            stop_trailing = operacion_abierta.maximo_desde_entrada * (1.0 - TRAILING_STOP_PCT)

            if qqq3_close_hoy <= stop_trailing:
                salida_pendiente = True
                motivo_salida_pendiente = 'SELL_TRAILING'
            elif not bool(hoy.get('senal_base_on', False)):
                salida_pendiente = True
                motivo_salida_pendiente = 'SELL_SIGNAL'

    return sorted(operaciones, key=lambda x: x['fecha_salida'])


def crear_resumen_anual(df_operaciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not df_operaciones:
        return []

    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for op in df_operaciones:
        anio = op['fecha_salida'].year
        by_year.setdefault(anio, []).append(op)

    resumen: List[Dict[str, Any]] = []

    for anio in sorted(by_year.keys()):
        ops = by_year[anio]
        operaciones = len(ops)
        ganadoras = sum(1 for op in ops if op['beneficio_neto_eur'] > 0)
        perdedoras = operaciones - ganadoras
        beneficio_neto = round(sum(op['beneficio_neto_eur'] for op in ops), 2)

        win_rate = round((ganadoras / operaciones * 100.0) if operaciones else 0.0, 4)
        rentabilidad = round((beneficio_neto / CAPITAL_INICIAL_EUR) * 100.0, 4)

        curva = [float(op['capital_acumulado_eur']) for op in ops]
        pico = 0.0
        dd_min = 0.0
        for valor in curva:
            pico = max(pico, valor)
            if pico > 0:
                dd = ((valor - pico) / pico) * 100.0
                dd_min = min(dd_min, dd)

        resumen.append(
            {
                'version_sistema': VERSION_SISTEMA,
                'anio': anio,
                'operaciones': operaciones,
                'ganadoras': ganadoras,
                'perdedoras': perdedoras,
                'win_rate_pct': win_rate,
                'beneficio_neto_eur': beneficio_neto,
                'rentabilidad_pct': rentabilidad,
                'drawdown_max_pct': round(dd_min, 4),
            }
        )

    return resumen
