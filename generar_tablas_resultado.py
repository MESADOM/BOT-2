from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from A_configuracion import (
    CAPITAL_INICIAL_EUR,
    COMISION_POR_OPERACION_EUR,
    DIAS_CONFIRMACION_ENTRADA,
    MAX_UNIDADES_POR_COMPRA,
    PERIODO_MEDIA_LARGA,
    PORCENTAJE_CAPITAL_POR_ENTRADA,
    TRAILING_STOP_PCT,
    VERSION_SISTEMA,
)

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class OperacionAbierta:
    fecha_entrada: datetime
    precio_entrada: float
    unidades: int
    capital_antes_eur: float
    maximo_desde_entrada: float
    senal_entrada: str


def _parse_num_es(value: str) -> float:
    value = value.strip().replace('.', '').replace(',', '.')
    return float(value)


def _leer_qqq(path: Path) -> Dict[datetime, Dict[str, float]]:
    filas: Dict[datetime, Dict[str, float]] = {}
    with path.open(encoding='utf-8-sig', newline='') as fh:
        raw_lines = [line.strip() for line in fh if line.strip()]

    for line in raw_lines[1:]:
        first = next(csv.reader([line]))
        row = next(csv.reader([first[0]]))
        fecha = datetime.strptime(row[0], '%m/%d/%Y')
        filas[fecha] = {
            'close': float(row[1]),
            'open': float(row[2]),
            'high': float(row[3]),
            'low': float(row[4]),
        }
    return filas


def _leer_es(path: Path) -> Dict[datetime, Dict[str, float]]:
    filas: Dict[datetime, Dict[str, float]] = {}
    with path.open(encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fecha = datetime.strptime(row['Fecha'], '%d.%m.%Y')
            filas[fecha] = {
                'close': _parse_num_es(row['Último']),
                'open': _parse_num_es(row['Apertura']),
                'high': _parse_num_es(row['Máximo']),
                'low': _parse_num_es(row['Mínimo']),
            }
    return filas


def preparar_base() -> List[Dict]:
    qqq = _leer_qqq(BASE_DIR / 'datos' / 'QQQ.csv')
    qqq3 = _leer_es(BASE_DIR / 'datos' / 'QQQ3.csv')

    fechas = sorted(set(qqq.keys()) | set(qqq3.keys()))
    rows = []
    for fecha in fechas:
        rows.append(
            {
                'fecha': fecha,
                'qqq_close': qqq.get(fecha, {}).get('close'),
                'qqq3_close': qqq3.get(fecha, {}).get('close'),
                'qqq3_open': qqq3.get(fecha, {}).get('open'),
            }
        )

    closes: List[float] = []
    ultimas_senales: List[bool] = []
    n = max(1, int(DIAS_CONFIRMACION_ENTRADA))

    for row in rows:
        close = row['qqq_close']
        if close is None:
            row['qqq_media_larga'] = None
            row['senal_base_on'] = False
            ultimas_senales.append(False)
            if len(ultimas_senales) > n:
                ultimas_senales.pop(0)
            row['senal_confirmada'] = len(ultimas_senales) == n and all(ultimas_senales)
            continue

        closes.append(close)
        if len(closes) >= PERIODO_MEDIA_LARGA:
            sma = sum(closes[-PERIODO_MEDIA_LARGA:]) / PERIODO_MEDIA_LARGA
            row['qqq_media_larga'] = sma
            row['senal_base_on'] = close > sma
        else:
            row['qqq_media_larga'] = None
            row['senal_base_on'] = False

        ultimas_senales.append(bool(row['senal_base_on']))
        if len(ultimas_senales) > n:
            ultimas_senales.pop(0)
        row['senal_confirmada'] = len(ultimas_senales) == n and all(ultimas_senales)

    return rows


def ejecutar(rows: List[Dict]) -> List[Dict]:
    capital_actual = float(CAPITAL_INICIAL_EUR)
    operacion_abierta: Optional[OperacionAbierta] = None
    operaciones: List[Dict] = []

    entrada_pendiente = False
    salida_pendiente = False
    motivo_salida_pendiente = ''

    for i in range(len(rows) - 1):
        hoy = rows[i]
        manana = rows[i + 1]

        qqq_close_hoy = hoy.get('qqq_close')
        qqq3_close_hoy = hoy.get('qqq3_close')
        qqq3_open_manana = manana.get('qqq3_open')

        if qqq_close_hoy is None or qqq3_close_hoy is None or qqq3_open_manana is None:
            continue

        if salida_pendiente and operacion_abierta is not None:
            precio_salida = qqq3_open_manana
            beneficio_bruto = (precio_salida - operacion_abierta.precio_entrada) * operacion_abierta.unidades
            beneficio_neto = beneficio_bruto - COMISION_POR_OPERACION_EUR

            rentabilidad_pct = 0.0
            if operacion_abierta.capital_antes_eur > 0:
                rentabilidad_pct = beneficio_neto / operacion_abierta.capital_antes_eur * 100.0

            capital_actual += beneficio_neto
            beneficio_acumulado_eur = capital_actual - CAPITAL_INICIAL_EUR
            stop_trailing = operacion_abierta.maximo_desde_entrada * (1.0 - TRAILING_STOP_PCT)

            operaciones.append(
                {
                    'version_sistema': VERSION_SISTEMA,
                    'fecha_entrada': operacion_abierta.fecha_entrada,
                    'fecha_salida': manana['fecha'],
                    'beneficio_neto_eur': round(beneficio_neto, 2),
                    'beneficio_acumulado_eur': round(beneficio_acumulado_eur, 2),
                    'capital_acumulado_eur': round(capital_actual, 2),
                    'motivo_salida': motivo_salida_pendiente,
                    'rentabilidad_pct': round(rentabilidad_pct, 4),
                    'capital_antes_eur': round(operacion_abierta.capital_antes_eur, 2),
                    'unidades': operacion_abierta.unidades,
                    'precio_entrada': round(operacion_abierta.precio_entrada, 6),
                    'precio_salida': round(precio_salida, 6),
                    'senal_entrada': operacion_abierta.senal_entrada,
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


def resumen_anual(operaciones: List[Dict]) -> List[Dict]:
    by_year: Dict[int, List[Dict]] = {}
    for op in operaciones:
        anio = op['fecha_salida'].year
        by_year.setdefault(anio, []).append(op)

    result = []
    for anio in sorted(by_year):
        ops = by_year[anio]
        operaciones_count = len(ops)
        ganadoras = sum(1 for o in ops if o['beneficio_neto_eur'] > 0)
        perdedoras = operaciones_count - ganadoras
        beneficio = round(sum(o['beneficio_neto_eur'] for o in ops), 2)
        win_rate = round((ganadoras / operaciones_count) * 100.0 if operaciones_count else 0.0, 4)
        rent = round((beneficio / CAPITAL_INICIAL_EUR) * 100.0, 4)
        capital_cierre_anual = round(ops[-1]['capital_acumulado_eur'], 2)

        curva = [o['capital_acumulado_eur'] for o in ops]
        pico = 0.0
        dd_min = 0.0
        for v in curva:
            pico = max(pico, v)
            if pico > 0:
                dd = ((v - pico) / pico) * 100.0
                dd_min = min(dd_min, dd)

        result.append(
            {
                'version_sistema': VERSION_SISTEMA,
                'anio': anio,
                'operaciones': operaciones_count,
                'ganadoras': ganadoras,
                'perdedoras': perdedoras,
                'win_rate_pct': win_rate,
                'beneficio_neto_eur': beneficio,
                'capital_acumulado_eur': capital_cierre_anual,
                'rentabilidad_pct': rent,
                'drawdown_max_pct': round(dd_min, 4),
            }
        )

    return result


def _fmt(v: object) -> str:
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d')
    return str(v)


def _tsv(rows: List[Dict], columns: List[str], headers: List[str]) -> str:
    lines = ['	'.join(headers)]
    for row in rows:
        lines.append('	'.join(_fmt(row.get(col, '')) for col in columns))
    return '\n'.join(lines)


def main() -> None:
    rows = preparar_base()
    operaciones = ejecutar(rows)
    resumen = resumen_anual(operaciones)

    print(f'Version sistema: {VERSION_SISTEMA}')
    print()

    print('Resumen anual')
    print(_tsv(
        resumen,
        [
            'anio',
            'operaciones',
            'ganadoras',
            'perdedoras',
            'win_rate_pct',
            'beneficio_neto_eur',
            'capital_acumulado_eur',
            'rentabilidad_pct',
            'drawdown_max_pct',
        ],
        [
            'Año',
            'Operaciones',
            'Ganadoras',
            'Perdedoras',
            'Win rate %',
            'Beneficio neto €',
            'Capital acumulado €',
            'Rentabilidad %',
            'Drawdown máx %',
        ]
    ))
    print()

    print('Detalle completo de operaciones')
    print(_tsv(
        operaciones,
        [
            'fecha_entrada',
            'fecha_salida',
            'senal_entrada',
            'precio_entrada',
            'precio_salida',
            'unidades',
            'motivo_salida',
            'beneficio_neto_eur',
            'beneficio_acumulado_eur',
            'rentabilidad_pct',
            'capital_acumulado_eur',
        ],
        [
            'Fecha entrada',
            'Fecha salida',
            'Señal entrada',
            'Precio entrada',
            'Precio salida',
            'Unidades',
            'Motivo salida',
            'Beneficio neto €',
            'Beneficio acumulado €',
            'Rentabilidad %',
            'Capital acumulado €',
        ]
    ))


if __name__ == '__main__':
    main()
