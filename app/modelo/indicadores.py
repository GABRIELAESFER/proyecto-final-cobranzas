"""
Indicador: monto vencido por tramo de atraso.

Responde: ¿cuanto dinero nos deben y que tan atrasado esta?
Regla: el DataFrame NO sale de este archivo; devuelve listas y diccionarios.
"""

import pandas as pd


def calcular(registros):
    df = pd.DataFrame(registros)
    hoy = pd.Timestamp.today().normalize()

    # dias de atraso de cada cuota
    df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"])
    df["dias_vencidos"] = (hoy - df["fecha_vencimiento"]).dt.days

    # deuda pendiente = sin fecha de pago y ya vencida
    pendientes = df[df["fecha_pago"].isna() & (df["dias_vencidos"] >= 1)].copy()

    # agrupar por tramo
    tramos = [0, 30, 60, 90, 120, float("inf")]
    nombres = ["01-30 dias", "31-60 dias", "61-90 dias", "91-120 dias", "121+ dias"]
    pendientes["tramo"] = pd.cut(pendientes["dias_vencidos"], bins=tramos, labels=nombres)
    grupos = pendientes.groupby("tramo", observed=False)["monto_cuota"].agg(["count", "sum"])

    #calccula el toadl de todo el dineroa trasado y recorre cada fila
    total = float(pendientes["monto_cuota"].sum())
    por_tramo = []
    for tramo, fila in grupos.iterrows():
        monto = float(fila["sum"])
        por_tramo.append({
            "tramo": str(tramo),
            "cuotas": int(fila["count"]),
            "monto": round(monto, 2),
            "porcentaje": round(monto / total * 100, 2) if total else 0.0,
        })

    return {"total_vencido": round(total, 2),
            "cuotas_pendientes": int(len(pendientes)),
            "por_tramo": por_tramo}