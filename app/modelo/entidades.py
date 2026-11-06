"""
Clases de dominio de cobranzas.

Aqui vive la regla de negocio: la Deuda sabe validarse, calcular sus dias
de atraso y decir que tan prioritaria es para la cola de llamadas.
"""

import re
from datetime import date, datetime


def a_decimal(texto):
    """Convierte texto a decimal. Acepta coma o punto."""
    if texto is None:
        raise ValueError("valor vacio")
    texto = str(texto).strip().replace(",", ".")
    if texto == "":
        raise ValueError("valor vacio")
    return float(texto)


def a_entero(texto):
    """Convierte texto a entero."""
    if texto is None:
        raise ValueError("valor vacio")
    texto = str(texto).strip()
    if texto == "":
        raise ValueError("valor vacio")
    return int(float(texto.replace(",", ".")))


def a_fecha(texto):
    """Convierte texto a fecha. Acepta YYYY-MM-DD y DD/MM/YYYY."""
    if texto is None:
        raise ValueError("valor vacio")
    texto = str(texto).strip()
    if texto == "":
        raise ValueError("valor vacio")
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError(f"fecha invalida '{texto}'")


def _campo(nombre, convertir, valor):
    """Aplica una conversion y le pone el nombre del campo al error."""
    #error de la fila si falla decimal
    try:
        return convertir(valor)
    except ValueError as error:
        raise ValueError(f"{nombre}: {error}")


class Deuda:
    """Una cuota vencida (o ya pagada) de un cliente."""

    # fecha_pago no es obligatoria: vacia significa cuota impaga
    OBLIGATORIAS = ["id_operacion", "documento_cliente", "cliente", "monto_cuota",
                    "fecha_vencimiento", "canal_preferido", "gestiones_previas",
                    "promesa_incumplida"]
    CANALES = {"Telefono", "Correo", "Mensajeria", "Visita"}

    # Regla de negocio: puntaje de 0 a 100
    PESO_MONTO = 40        # cuanto dinero esta en juego
    PESO_DIAS = 35         # antiguedad de la deuda
    PESO_PROMESA = 15      # promesa de pago incumplida
    PESO_GESTIONES = 10    # historial de gestiones previas
    MONTO_TOPE = 4500      # desde este monto ya se cuenta el puntaje completo
    DIAS_TOPE = 120
    GESTIONES_TOPE = 5
    UMBRAL_ALTA = 70
    UMBRAL_MEDIA = 40

    def __init__(self, id_operacion, documento_cliente, cliente, monto_cuota,
                 fecha_vencimiento, fecha_pago, canal_preferido,
                 gestiones_previas, promesa_incumplida):
        self.id_operacion = id_operacion
        self.documento_cliente = documento_cliente
        self.cliente = cliente
        self.monto_cuota = monto_cuota
        self.fecha_vencimiento = fecha_vencimiento
        self.fecha_pago = fecha_pago
        self.canal_preferido = canal_preferido
        self.gestiones_previas = gestiones_previas
        self.promesa_incumplida = promesa_incumplida   # "SI" o "NO"
    #recibe una fila y hace una deuda o lanza un error si la fil ano sirve
    @classmethod
    def desde_fila(cls, fila):
        """Construye la Deuda desde una fila del CSV o levanta ValueError."""
        #limpiar y convertir todo a texto, quitamos los espacios
        f = {k: ("" if v is None else str(v)).strip() for k, v in fila.items() if k is not None}
        hoy = date.today()

        #si alguno esta cio error, pero fecha de pago si puede estar vacio
        for campo in cls.OBLIGATORIAS:
            if not f.get(campo):
                raise ValueError(f"{campo} vacio")
            
        #pasa a mayusculas y comprueba q el id tenga mas de 8 digitos, sino error
        id_operacion = f["id_operacion"].upper()
        if not re.fullmatch(r"OP-\d{8}", id_operacion):
            raise ValueError(f"id_operacion invalido: '{id_operacion}'")

        
        #exact 8 digitos, dni del suusario
        documento = f["documento_cliente"]
        if not re.fullmatch(r"\d{8}", documento):
            raise ValueError(f"documento_cliente invalido: '{documento}'")
        

        #convierte a numero y comprueba q sea mmayor a 0
        monto = _campo("monto_cuota", a_decimal, f["monto_cuota"])
        if monto <= 0:
            raise ValueError("monto_cuota debe ser mayor a 0")

        #convertimos a fecha y comprobamos q mo pase de hoy
        vencimiento = _campo("fecha_vencimiento", a_fecha, f["fecha_vencimiento"])
        if vencimiento > hoy:
            raise ValueError("fecha_vencimiento en el futuro")

        
        #igual fecha de pago si viene comprobamos q no sea futura
        pago = None
        if f.get("fecha_pago"):
            pago = _campo("fecha_pago", a_fecha, f["fecha_pago"])
            if pago > hoy:
                raise ValueError("fecha_pago en el futuro")
            
        #canal preferido
        canal = f["canal_preferido"].capitalize()
        if canal not in cls.CANALES:
            raise ValueError(f"canal_preferido no reconocido: '{canal}'")

        #entero y no negativo
        gestiones = _campo("gestiones_previas", a_entero, f["gestiones_previas"])
        if gestiones < 0:
            raise ValueError("gestiones_previas no puede ser negativo")

        #validamos la promesa q sea si o no
        promesa = f["promesa_incumplida"].upper()
        if promesa not in ("SI", "NO"):
            raise ValueError(f"promesa_incumplida debe ser SI o NO: '{promesa}'")

        #y por ultimo fabricamos la deuda
        return cls(id_operacion, documento, f["cliente"].title(), monto,
                   vencimiento, pago, canal, gestiones, promesa)

    # ---- calculos ----

    #si tiene fecha de pago y no es futura TRUE
    def esta_pagada(self, fecha_ref=None):
        fecha_ref = fecha_ref or date.today()
        return self.fecha_pago is not None and self.fecha_pago <= fecha_ref

    #reetatmos la fecha de vencimiento - hoy (dias vencidos)
    def dias_vencidos(self, fecha_ref=None):
        fecha_ref = fecha_ref or date.today()
        return (fecha_ref - self.fecha_vencimiento).days
    
    #categorizamos los dias vencidos
    def tramo(self, fecha_ref=None):
        dias = self.dias_vencidos(fecha_ref)
        if dias <= 30:
            return "01-30 dias"
        if dias <= 60:
            return "31-60 dias"
        if dias <= 90:
            return "61-90 dias"
        if dias <= 120:
            return "91-120 dias"
        return "121+ dias"

    def puntaje(self, fecha_ref=None):
        """Puntaje de prioridad de 0 a 100. Una cuota pagada vale 0."""
        if self.esta_pagada(fecha_ref) or self.dias_vencidos(fecha_ref) < 1:
            return 0.0
        pts = min(self.monto_cuota / self.MONTO_TOPE, 1) * self.PESO_MONTO
        pts += min(self.dias_vencidos(fecha_ref) / self.DIAS_TOPE, 1) * self.PESO_DIAS
        pts += self.PESO_PROMESA if self.promesa_incumplida == "SI" else 0
        pts += min(self.gestiones_previas / self.GESTIONES_TOPE, 1) * self.PESO_GESTIONES
        return round(pts, 1)

    def clasificar(self, fecha_ref=None):
        """Pagada / Alta / Media / Baja, segun el puntaje."""
        if self.esta_pagada(fecha_ref):
            return "Pagada"
        pts = self.puntaje(fecha_ref)
        if pts >= self.UMBRAL_ALTA:#70
            return "Alta"
        if pts >= self.UMBRAL_MEDIA:#40
            return "Media"
        return "Baja"

    def como_diccionario(self, fecha_ref=None):
        """Datos como diccionario (la vista no recibe objetos del modelo).

        Con fecha_ref agrega los campos calculados para la cola de cobranza.
        """
        datos = {
            "id_operacion": self.id_operacion,
            "documento_cliente": self.documento_cliente,
            "cliente": self.cliente,
            "monto_cuota": self.monto_cuota,
            "fecha_vencimiento": self.fecha_vencimiento.isoformat(),
            "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None,
            "canal_preferido": self.canal_preferido,
            "gestiones_previas": self.gestiones_previas,
            "promesa_incumplida": self.promesa_incumplida,
        }
        if fecha_ref is not None:
            datos["dias_vencidos"] = self.dias_vencidos(fecha_ref)
            datos["tramo"] = self.tramo(fecha_ref)
            datos["puntaje"] = self.puntaje(fecha_ref)
            datos["prioridad"] = self.clasificar(fecha_ref)
        return datos
