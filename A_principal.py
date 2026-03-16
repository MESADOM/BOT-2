from __future__ import annotations

import csv
from datetime import datetime
from typing import Any, Dict, List

from A_configuracion import (
    VERSION_BOT,
    CAPITAL_INICIAL_EUR,
    RUTA_QQQ,
    RUTA_QQQ3,
    RUTA_VIX,
    GUARDAR_RESULTADOS,
    RUTA_SALIDA_OPERACIONES,
    RUTA_SALIDA_RESUMEN,
)
from A_estrategia import preparar_datos, ejecutar_estrategia, crear_resumen_anual


def _parse_num(texto: str) -> float | None:
    t = (texto or '').strip().replace('"', '')
    if not t:
        return None
    t = t.replace('.', '').replace(',', '.') if ',' in t and '.' in t and t.find(',') > t.find('.') else t.replace(',', '.')
    t = t.replace('%', '').replace('K', '').replace('M', '').replace('B', '')
    try:
        return float(t)
    except ValueError:
        return None


def _parse_fecha(texto: str) -> datetime:
    t = texto.strip().replace('"', '')
    for fmt in ('%m/%d/%Y', '%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    raise ValueError(f'Fecha no reconocida: {texto}')


def _leer_csv_generico(ruta: str, formato_qqq: bool = False) -> List[Dict[str, Any]]:
    filas: List[Dict[str, Any]] = []
    with open(ruta, 'r', encoding='utf-8-sig', newline='') as f:
        lines = f.read().splitlines()

    for raw in lines[1:]:
        if not raw.strip():
            continue
        if formato_qqq:
            campo = next(csv.reader([raw]))[0]
            parts = next(csv.reader([campo]))
            if len(parts) < 2:
                continue
            fecha = _parse_fecha(parts[0])
            close = _parse_num(parts[1])
        else:
            parts = next(csv.reader([raw]))
            if len(parts) < 2:
                continue
            fecha = _parse_fecha(parts[0])
            close = _parse_num(parts[1])

        filas.append({'fecha': fecha, 'close': close})

    filas.sort(key=lambda x: x['fecha'])
    return filas


def cargar_csv(ruta):
    ruta_str = str(ruta)
    return _leer_csv_generico(ruta_str, formato_qqq=ruta_str.endswith('QQQ.csv'))


def ejecutar_bot():
    df_qqq = cargar_csv(RUTA_QQQ)
    df_qqq3 = cargar_csv(RUTA_QQQ3)
    df_vix = cargar_csv(RUTA_VIX)

    df_base = preparar_datos(df_qqq=df_qqq, df_qqq3=df_qqq3, df_vix=df_vix)
    df_operaciones = ejecutar_estrategia(df_base)
    df_resumen_anual = crear_resumen_anual(df_operaciones)

    if GUARDAR_RESULTADOS:
        _guardar_csv(RUTA_SALIDA_OPERACIONES, df_operaciones)
        _guardar_csv(RUTA_SALIDA_RESUMEN, df_resumen_anual)

    return {
        'version_bot': VERSION_BOT,
        'operaciones': df_operaciones,
        'resumen_anual': df_resumen_anual,
    }


def _guardar_csv(ruta, filas: List[Dict[str, Any]]):
    if not filas:
        return
    with open(ruta, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def _imprimir_tsv(titulo: str, columnas: List[str], filas: List[List[Any]]):
    print(titulo)
    print('\t'.join(columnas))
    for fila in filas:
        print('\t'.join(str(x) for x in fila))


if __name__ == '__main__':
    r = ejecutar_bot()

    resumen_filas = []
    capital = CAPITAL_INICIAL_EUR
    for x in sorted(r['resumen_anual'], key=lambda y: y['anio']):
        capital += x['beneficio_neto_eur']
        resumen_filas.append([
            x['anio'], x['operaciones'], x['ganadoras'], x['perdedoras'],
            x['win_rate_pct'], x['beneficio_neto_eur'], round(capital, 2),
            x['rentabilidad_pct'], x['drawdown_max_pct']
        ])

    ops = sorted(r['operaciones'], key=lambda y: y['fecha_entrada'])
    ops_filas = []
    for x in ops:
        s_entrada = x.get('senal_entrada', '')
        s_salida = x.get('motivo_salida', '')
        ops_filas.append([
            x['fecha_entrada'].strftime('%Y-%m-%d'),
            x['fecha_salida'].strftime('%Y-%m-%d'),
            s_entrada,
            s_salida,
            s_entrada,
            s_entrada,
            x['motivo_salida'],
            x['beneficio_neto_eur'],
            x['rentabilidad_pct'],
            x['capital_acumulado_eur'],
        ])

    print(f"Versión\t{r['version_bot']}")
    _imprimir_tsv(
        'Resumen anual',
        ['Año', 'Operaciones', 'Ganadoras', 'Perdedoras', 'Win rate %', 'Beneficio neto €', 'Capital acumulado €', 'Rentabilidad %', 'Drawdown máx %'],
        resumen_filas,
    )
    _imprimir_tsv(
        'Detalle completo de operaciones',
        ['Fecha entrada', 'Fecha salida', 'Score entrada', 'Score salida', 'Estado mercado', 'Régimen', 'Motivo salida', 'Beneficio neto €', 'Rentabilidad %', 'Capital acumulado €'],
        ops_filas,
    )
