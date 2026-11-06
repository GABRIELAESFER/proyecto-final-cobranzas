# Cola de cobranza

Herramienta de consola en Python para el área de **Cobranzas**. Carga un archivo de cuotas, descarta las filas inválidas, guarda las válidas en SQLite, calcula cuánto dinero está atrasado y entrega un Excel con las deudas ordenadas por prioridad.

**Pregunta de negocio que responde:** ¿a quién llamamos primero mañana?

> Proyecto final del curso. La data es ficticia y se genera con el script del curso (`generar_datos.py`).

## Qué hace

El menú tiene cinco opciones:

| Opción | Qué hace |
|---|---|
| 1. Cargar data del día | Lee el CSV, valida cada fila, quita duplicados y guarda en SQLite. Las filas inválidas se rechazan con su fila y su motivo; nunca tumban la carga. |
| 2. Ver indicadores | Muestra el monto vencido por tramo de atraso (cuánto dinero se debe y hace cuántos días). |
| 3. Explorar la data | Busca una cuota por su id (`OP-00000001`). |
| 4. Generar entregable | Crea un Excel con las deudas pendientes ordenadas por puntaje de prioridad. |
| 5. Historial de cargas | Muestra qué archivos se cargaron y cuándo. |

## Cómo funciona

```
CSV → validar → quitar duplicados → SQLite → indicador (pandas) → Excel priorizado
```

- **Validación:** cada fila se convierte en una `Deuda`. Si falta un campo, el DNI no tiene 8 dígitos, el monto es inválido, etc., se rechaza y se anota el motivo. Acepta fechas `YYYY-MM-DD` y `DD/MM/YYYY` y montos con coma o punto decimal.
- **Sin duplicados:** `id_operacion` es llave primaria, y la tabla `cargas` impide cargar el mismo archivo dos veces el mismo día.
- **Indicador:** monto vencido por tramo (1-30, 31-60, 61-90, 91-120 y más de 120 días), calculado con pandas.
- **Regla de negocio:** cada deuda pendiente recibe un puntaje de 0 a 100.

| Factor | Puntos máximos |
|---|---|
| Monto de la cuota | 40 |
| Días vencidos | 35 |
| Promesa de pago incumplida | 15 |
| Gestiones previas | 10 |

Prioridad **Alta** desde 70 puntos, **Media** desde 40 y **Baja** el resto. Los pesos y umbrales son constantes en la clase `Deuda` (`app/modelo/entidades.py`).

## Estructura

```
app/
├── controlador/app.py      Menú: coordina modelo y vista
├── modelo/
│   ├── entidades.py        Clase Deuda: validación y puntaje
│   ├── ingesta.py          Lectura del CSV y duplicados
│   ├── repositorio.py      Persistencia en SQLite
│   ├── indicadores.py      Cálculo con pandas
│   └── exportador.py       Generación del Excel
└── vista/consola.py        Todo lo que se imprime
data/                       CSV y base de datos (no se suben a git)
main.py                     Punto de entrada
```

La separación es MVC: el modelo tiene las reglas, la vista solo imprime y el controlador solo coordina.

## Cómo ejecutarlo

1. Instala las dependencias:

   ```
   pip install -r requirements.txt
   ```

2. Genera la data con el script del curso (sin `--limpio`, para que traiga errores a propósito):

   ```
   python generar_datos.py cobranzas --filas 10000 --output data/data_cobranzas.csv
   ```

3. Corre el programa:

   ```
   python main.py
   ```

4. Usa la opción 1 para cargar, y luego las demás. El Excel queda en la carpeta `output/` con la fecha en el nombre (`cola_cobranza_AAAA-MM-DD.xlsx`).

## Tecnologías

Python, pandas, SQLite (`sqlite3`) y openpyxl.

## Limitaciones

- No considera feriados.
- Los pesos del puntaje son un criterio propio, no salen de datos reales.
- La data es sintética: por ejemplo, tener más gestiones previas no aumenta la probabilidad de pago.
