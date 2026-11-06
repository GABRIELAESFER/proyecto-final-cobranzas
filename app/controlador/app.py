"""
Controlador.

Le pide cosas al modelo y se las pasa a la vista.
No calcula ni imprime. Si aqui aparece un print(), algo se hizo mal.
"""

import os

from app.modelo import entidades, exportador, indicadores, ingesta
from app.modelo.repositorio import Repositorio, CargaDuplicada
from app.vista import consola


class Aplicacion:

    def __init__(self, ruta_csv, ruta_bd, carpeta_output):
        self.ruta_csv = ruta_csv
        self.carpeta_output = carpeta_output
        self.repositorio = Repositorio(ruta_bd)

    def cargar(self):
        """Lee, valida, quita duplicados, guarda e informa."""
        if not os.path.exists(self.ruta_csv):
            consola.advertencia(f"El archivo {self.ruta_csv} no existe.")
            return

        consola.mensaje("Leyendo archivo...")
        try:
            deudas, errores = ingesta.leer_csv(self.ruta_csv)
        except (OSError, UnicodeDecodeError) as error:
            consola.advertencia(f"No se pudo leer el archivo: {error}")
            return

        unicas, duplicadas = ingesta.quitar_duplicados(deudas)
        if not unicas:
            consola.advertencia("No hay filas validas para guardar.")
            return

        try:
            guardadas = self.repositorio.guardar_deudas(unicas, errores, self.ruta_csv)
        except CargaDuplicada:
            consola.advertencia("Este archivo ya se cargo hoy. No se guardo nada.")
            return

        consola.mensaje(f"Filas validas guardadas: {guardadas}")
        consola.mensaje(f"Filas duplicadas descartadas: {duplicadas}")
        consola.mensaje(f"Filas rechazadas: {len(errores)}")
        for error in errores[:5]:
            consola.mensaje(f"  fila {error['fila']}: {error['motivo']}")

    def ver_indicadores(self):
        registros = self.repositorio.listar()
        if not registros:
            consola.advertencia("No hay datos cargados. Usa primero la opcion 1.")
            return

        r = indicadores.calcular(registros)
        consola.mensaje(f"Monto vencido total: {r['total_vencido']:,.2f}")
        consola.mensaje(f"Cuotas pendientes: {r['cuotas_pendientes']}")
        consola.mensaje("--- Monto vencido por tramo ---")
        for t in r["por_tramo"]:
            consola.mensaje(f"{t['tramo']:<12} {t['cuotas']:>6} cuotas  "
                            f"{t['monto']:>14,.2f}  ({t['porcentaje']}%)")

    def explorar(self):
        id_op = consola.pedir_texto("Id de la operacion (ej. OP-00000001): ")
        d = self.repositorio.buscar(id_op)
        if d is None:
            consola.advertencia(f"No existe la operacion {id_op}.")
            return
        consola.mensaje(f"Operacion: {d['id_operacion']}")
        consola.mensaje(f"Cliente: {d['cliente']} (doc {d['documento_cliente']})")
        consola.mensaje(f"Monto de la cuota: {d['monto_cuota']:,.2f}")
        consola.mensaje(f"Vencimiento: {d['fecha_vencimiento']} | "
                        f"Pago: {d['fecha_pago'] or 'pendiente'}")
        consola.mensaje(f"Canal: {d['canal_preferido']} | "
                        f"Gestiones previas: {d['gestiones_previas']} | "
                        f"Promesa incumplida: {d['promesa_incumplida']}")
        
    def generar_entregable(self):
        registros = self.repositorio.listar()
        if not registros:
            consola.advertencia("No hay datos cargados. Usa primero la opcion 1.")
            return

        ruta, filas = exportador.generar(registros, self.carpeta_output)
        if filas == 0:
            consola.advertencia("No hay deudas pendientes para cobrar.")
            return

        consola.mensaje(f"Entregable generado: {ruta}")
        consola.mensaje(f"Casos en la cola de cobranza: {filas}")

    def ver_historial(self):
        cargas = self.repositorio.historial()
        if not cargas:
            consola.advertencia("Todavia no hay cargas registradas.")
            return
        for c in cargas:
            consola.mensaje(
                f"{c['fecha']} | {c['archivo']} | "
                f"validas: {c['filas_validas']} | rechazadas: {c['filas_rechazadas']}")

    def ejecutar(self):
        acciones = {
            "1": self.cargar,
            "2": self.ver_indicadores,
            "3": self.explorar,
            "4": self.generar_entregable,
            "5": self.ver_historial,
        }
        while True:
            consola.mostrar_menu()
            opcion = consola.pedir_opcion()
            if opcion == "6":
                consola.mensaje("Fin del proceso.")
                return
            accion = acciones.get(opcion)
            if accion is None:
                consola.advertencia("Esa opcion no existe.")
                continue
            try:
                accion()
            except NotImplementedError:
                consola.advertencia("Esa opcion aun no esta implementada.")