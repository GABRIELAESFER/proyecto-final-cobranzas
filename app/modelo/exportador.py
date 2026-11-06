"""
Generacion del entregable: la cola de cobranza para el area de Cobranzas.
Lleva la fecha en el nombre para que el de hoy no pise el de ayer.
"""

import os
from datetime import date

import pandas as pd

from app.modelo.entidades import Deuda


def generar(registros, carpeta_output):
    hoy = date.today()

    # solo las deudas que todavia hay que cobrar, con su puntaje y prioridad
    filas = []
    for registro in registros:
        deuda = Deuda.desde_fila(registro)
        if not deuda.esta_pagada(hoy) and deuda.dias_vencidos(hoy) >= 1:
            filas.append(deuda.como_diccionario(hoy))

    if not filas:
        return None, 0

    # la primera fila es a quien se llama primero
    df = pd.DataFrame(filas).sort_values("puntaje", ascending=False)
    df = df[["id_operacion", "cliente", "documento_cliente", "canal_preferido",
             "monto_cuota", "dias_vencidos", "puntaje", "prioridad"]]
    df.columns = ["Id operación", "Cliente", "Documento", "Canal de contacto",
                  "Monto de la cuota", "Días vencidos", "Puntaje", "Prioridad"]

    os.makedirs(carpeta_output, exist_ok=True)
    ruta = os.path.join(carpeta_output, f"cola_cobranza_{hoy.isoformat()}.xlsx")
    df.to_excel(ruta, index=False)
    return ruta, len(df)