"""
Lectura y validacion del archivo del dia.

Regla que no se negocia: una fila mala nunca tumba la carga.
Se rechaza, se anota el motivo y se sigue con la siguiente.
"""

import csv

from app.modelo.entidades import Deuda


def leer_csv(ruta):
    """Devuelve (registros_validos, errores). Cada error dice la fila y el motivo."""
    deudas = []
    errores = []
    with open(ruta, encoding="utf-8", newline="") as archivo:#leer linea a linea
        lector = csv.DictReader(archivo)
        for numero, fila in enumerate(lector, start=2):#fila 2
            try:
                deudas.append(Deuda.desde_fila(fila))
            except ValueError as error:#unaa fila mala no hace que caiga
                errores.append({"fila": numero, "motivo": str(error)})
    return deudas, errores


def quitar_duplicados(deudas):
    """Deja una sola Deuda por id_operacion. Devuelve (unicos, cantidad_descartada)."""
    unicos = {}
    duplicados = 0
    for deuda in deudas:
        if deuda.id_operacion in unicos:
            duplicados += 1
        else:
            unicos[deuda.id_operacion] = deuda # primera vez: guardar
    return list(unicos.values()), duplicados