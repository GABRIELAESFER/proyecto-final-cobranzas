"""
Persistencia en SQLite.

Dos tablas como minimo:
  - la de tu entidad, con su identificador como PRIMARY KEY
  - una tabla de cargas, para saber que dia se cargo que archivo

La segunda es la que impide cargar dos veces el mismo dia.

Advertencia de rendimiento: NO pongas commit() dentro del bucle de
insercion. Con 50 000 filas se vuelve de cientos a miles de veces mas
lento. Usa executemany() y un solo commit al final.
"""

import os
import sqlite3
from datetime import date

COLUMNAS_DEUDA = [
    "id_operacion", "documento_cliente", "cliente", "monto_cuota",
    "fecha_vencimiento", "fecha_pago", "canal_preferido",
    "gestiones_previas", "promesa_incumplida",
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS deudas(
    id_operacion       TEXT PRIMARY KEY,
    documento_cliente  TEXT NOT NULL,
    cliente            TEXT NOT NULL,
    monto_cuota        REAL NOT NULL CHECK (monto_cuota > 0),
    fecha_vencimiento  TEXT NOT NULL,
    fecha_pago         TEXT,
    canal_preferido    TEXT NOT NULL,
    gestiones_previas  INTEGER NOT NULL CHECK (gestiones_previas >= 0),
    promesa_incumplida TEXT NOT NULL CHECK (promesa_incumplida IN ('SI', 'NO'))
);


CREATE TABLE IF NOT EXISTS cargas(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha             TEXT NOT NULL,
    archivo           TEXT NOT NULL,
    filas_validas     INTEGER NOT NULL,
    filas_rechazadas  INTEGER NOT NULL,
    UNIQUE (fecha, archivo)
);

CREATE TABLE IF NOT EXISTS rechazos(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha    TEXT NOT NULL,
    archivo  TEXT NOT NULL,
    fila     INTEGER NOT NULL,
    motivo   TEXT NOT NULL
);
"""

# Si el mismo id_operacion llega otro dia, se actualiza en vez de duplicarse.
# Un pago ya registrado no se borra si el archivo nuevo no lo trae.
INSERTAR_DEUDA = """
INSERT INTO deudas (id_operacion, documento_cliente, cliente, monto_cuota,
                    fecha_vencimiento, fecha_pago, canal_preferido,
                    gestiones_previas, promesa_incumplida)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id_operacion) DO UPDATE SET
    documento_cliente  = excluded.documento_cliente,
    cliente            = excluded.cliente,
    monto_cuota        = excluded.monto_cuota,
    fecha_vencimiento  = excluded.fecha_vencimiento,
    fecha_pago         = COALESCE(excluded.fecha_pago, deudas.fecha_pago),
    canal_preferido    = excluded.canal_preferido,
    gestiones_previas  = excluded.gestiones_previas,
    promesa_incumplida = excluded.promesa_incumplida
"""


class CargaDuplicada(Exception):
    """Se intento cargar el mismo archivo dos veces el mismo dia."""


class Repositorio:

    def __init__(self, ruta_bd):
        carpeta = os.path.dirname(ruta_bd)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        self.ruta_bd = ruta_bd
        self.conexion = sqlite3.connect(ruta_bd)
        self.conexion.row_factory = sqlite3.Row
        self.conexion.executescript(ESQUEMA)
        self.conexion.commit()

    def ya_se_cargo_hoy(self, archivo):
        """True si ese archivo ya se cargo hoy (consulta la tabla de cargas)."""
        fila = self.conexion.execute(
            "SELECT 1 FROM cargas WHERE fecha = ? AND archivo = ?",
            (date.today().isoformat(), archivo),
        ).fetchone()
        return fila is not None

    def registrar_carga(self, archivo, validos, rechazados):
        """Anota la carga. No hace commit: lo hace guardar_deudas al final."""
        self.conexion.execute(
            "INSERT INTO cargas (fecha, archivo, filas_validas, filas_rechazadas) "
            "VALUES (?, ?, ?, ?)",
            (date.today().isoformat(), archivo, validos, rechazados),
        )

    def guardar_deudas(self, deudas, errores, ruta_csv):
        """Guarda las deudas, los rechazos y la carga en UNA sola transaccion.

        Lanza CargaDuplicada si ese archivo ya se cargo hoy.
        Devuelve la cantidad de deudas guardadas.
        """
        archivo = os.path.basename(ruta_csv)
        if self.ya_se_cargo_hoy(archivo):
            raise CargaDuplicada(f"{archivo} ya se cargo hoy")

        filas = []
        for deuda in deudas:
            datos = deuda.como_diccionario()
            filas.append(tuple(datos[c] for c in COLUMNAS_DEUDA))

        hoy = date.today().isoformat()
        rechazos = [(hoy, archivo, e["fila"], e["motivo"]) for e in errores]

        with self.conexion:  # un solo commit al final; rollback si algo falla
            self.conexion.executemany(INSERTAR_DEUDA, filas)
            self.conexion.executemany(
                "INSERT INTO rechazos (fecha, archivo, fila, motivo) "
                "VALUES (?, ?, ?, ?)", rechazos)
            self.registrar_carga(archivo, len(filas), len(errores))
        return len(filas)

    def historial(self, limite=15):
        """Ultimas cargas, como lista de diccionarios."""
        filas = self.conexion.execute(
            "SELECT fecha, archivo, filas_validas, filas_rechazadas "
            "FROM cargas ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return [dict(f) for f in filas]

    def contar(self):
        return self.conexion.execute("SELECT COUNT(*) FROM deudas").fetchone()[0]

    def listar(self):
        """Devuelve la data como lista de diccionarios."""
        filas = self.conexion.execute(
            "SELECT * FROM deudas ORDER BY id_operacion").fetchall()
        return [dict(f) for f in filas]

    def primeras(self, limite=10):
        """Primeras deudas ordenadas por id, como lista de diccionarios."""
        filas = self.conexion.execute(
            "SELECT * FROM deudas ORDER BY id_operacion LIMIT ?", (limite,)).fetchall()
        return [dict(f) for f in filas]

    def buscar(self, id_operacion):
        """Devuelve la deuda como diccionario, o None si no existe."""
        fila = self.conexion.execute(
            "SELECT * FROM deudas WHERE id_operacion = ?",
            (id_operacion.strip().upper(),)).fetchone()
        return dict(fila) if fila else None

    def cerrar(self):
        self.conexion.close()