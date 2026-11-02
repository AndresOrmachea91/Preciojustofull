#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: datos de PRUEBA para ver el
sistema lleno mientras no hay caseros reales.

    python -m src.infraestructura.adaptadores.entrada.cli.sembrar_demo
    python -m src.infraestructura.adaptadores.entrada.cli.sembrar_demo --retirar

Registra caseros en varios mercados (con su puesto, una foto ilustrada y su
inventario), tres distribuidoras, algunas ofertas, una compradora con su
lista y unos reportes por revisar. Todo pasa por los casos de uso, como si
cada casero lo hiciera desde su celular: valen las mismas reglas.

Los precios no se inventan de la nada: parten del precio del sistema en ese
mercado (el SIIP con su ajuste) y se mueven un poco, como en la realidad.

Todo queda a nombre de "demo" en la auditoría y las cuentas usan el
dominio demo.preciojusto.bo. Con --retirar se da de baja (lógica) todo lo
que creó "demo": nada se borra.

La contraseña de las cuentas sale de DEMO_CONTRASENA (docker/.env).
Nunca correr contra la base de producción.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import struct
import sys
import zlib

from sqlalchemy import text

from src.aplicacion.casos_uso.usuario.listas_compras import RenglonPedido
from src.configuracion import config
from src.dominio.excepciones import ErrorDominio
from src.dominio.modelo import Disponibilidad, Presentacion
from src.infraestructura.adaptadores.entrada.api import dependencias as d
from src.infraestructura.adaptadores.salida.persistencia.auditable import actor_actual
from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_motor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sembrar_demo")

ACTOR = "demo"
DOMINIO = "demo.preciojusto.bo"

# Lo que suele haber en cada clase de puesto (los mercados no venden todos lo mismo).
SURTIDO = {
    "verduras": ("hortaliza", ["tomate", "cebolla", "zanahoria", "locoto", "haba_verde", "arveja", "vainita",
                               "pimenton", "cebolla_verde", "choclo", "zapallo"]),
    "papas": ("tuberculo", ["papa_holandesa", "papa_desiree", "papa_huaycha", "yuca", "cebolla"]),
    "frutas": ("fruta", ["banana", "platano", "manzana", "naranja", "mandarina", "papaya", "limon", "pina"]),
    "abarrotes": ("abarrote", ["arroz_primera", "arroz_segunda", "azucar", "harina_blanca", "fideo",
                               "aceite_soya", "quinua", "mani", "leche_polvo"]),
    "carnes": ("carne", ["pollo_entero", "carne_res", "carne_cerdo", "huevo"]),
    "pescados": ("pescado", ["trucha", "pejerrey", "pacu", "surubi"]),
}

# (mercado, número, nombre, clase, cómo encontrarlo)
PUESTOS = [
    ("rodriguez", "14", "Verduras Doña Rosa", "verduras", "Pasillo de verduras, frente a la puerta 2"),
    ("rodriguez", "22", "Papas Don Feliciano", "papas", "Al fondo, junto a las gradas"),
    ("rodriguez", "31", "Frutería La Yungueña", "frutas", "Entrada por la calle Rodríguez"),
    ("rodriguez", "8", "Abarrotes Mamá Julia", "abarrotes", "Esquina con la Zoilo Flores"),
    ("rodriguez", "45", "Pollos Doña Martha", "carnes", "Sector carnes, planta baja"),
    ("lanza", "B-12", "Verduras Doña Elena", "verduras", "Segundo piso, ala norte"),
    ("lanza", "B-20", "Abarrotes El Ahorro", "abarrotes", "Segundo piso, al lado del ascensor"),
    ("lanza", "A-5", "Frutas Don Tito", "frutas", "Planta baja, puerta de la Figueroa"),
    ("camacho", "3", "Carnes Don Lucho", "carnes", "Pasillo central"),
    ("camacho", "17", "Verduras La Cholita", "verduras", "Frente a la fuente"),
    ("camacho", "26", "Abarrotes San Miguel", "abarrotes", "Entrada de la Camacho"),
    ("yungas", "9", "Frutas del Trópico", "frutas", "Primer pasillo"),
    ("yungas", "15", "Papas Doña Benita", "papas", "Junto a la puerta lateral"),
    ("miraflores", "4", "Verduras Doña Carmen", "verduras", "Sector verduras"),
    ("miraflores", "11", "Carnes Miraflores", "carnes", "Sector carnes"),
    ("sopocachi", "6", "Frutería Sopocachi", "frutas", "Entrada de la Guachalla"),
    ("sopocachi", "12", "Abarrotes Doña Ruth", "abarrotes", "Al lado de los jugos"),
    ("villa_fatima", "21", "Papas del Altiplano", "papas", "Sector papas"),
    ("villa_fatima", "33", "Verduras Doña Juana", "verduras", "Pasillo 3"),
    ("uruguay", "2", "Pescados del Titicaca", "pescados", "Planta baja"),
    ("pescado", "7", "Trucha Fresca Doña Lidia", "pescados", "Primer puesto a la derecha"),
    ("pescado", "10", "Pescados Amazonía", "pescados", "Fondo del mercado"),
    ("frutas", "18", "Frutas Doña Paulina", "frutas", "Pasillo principal"),
    ("modelo_achumani", "5", "Verduras Achumani", "verduras", "Planta baja"),
    ("modelo_achumani", "13", "Abarrotes Calacoto", "abarrotes", "Junto a la entrada"),
    ("las_cholas", "16", "Verduras Doña Teodora", "verduras", "Pasillo central"),
    ("munaypata", "24", "Papas Don Gregorio", "papas", "Sector papas"),
]

# (nombre, zona, macrodistrito, latitud, longitud, clases, referencia)
DISTRIBUIDORAS = [
    ("Distribuidora El Sol", "Villa Fátima", "Periférica", -16.4865, -68.1215, ["abarrotes"],
     "Av. de las Américas, portón verde"),
    ("Distribuidora Andina de Papa", "Max Paredes", "Max Paredes", -16.4935, -68.1465, ["papas", "verduras"],
     "Cerca de la Garita de Lima"),
    ("Avícola Don Pedro", "Obrajes", "Sur", -16.5225, -68.1105, ["carnes"], "Calle 8 de Obrajes"),
]

NOMBRES = ["Rosa", "Feliciano", "Julia", "Martha", "Elena", "Tito", "Luis", "Carmen", "Ruth", "Juana",
           "Lidia", "Paulina", "Teodora", "Gregorio", "Benita", "Pedro", "Miguel", "Sonia", "Hilda", "Remedios"]

# Colores de las lonas de los puestos paceños: la foto ilustrada usa uno por puesto.
LONAS = [(28, 107, 87), (196, 69, 54), (36, 99, 170), (217, 148, 30), (122, 72, 160), (24, 140, 140),
         (200, 90, 140), (70, 120, 50)]
PRODUCTO_COLOR = {
    "verduras": [(214, 52, 41), (90, 160, 60), (240, 140, 30), (60, 120, 40)],
    "papas": [(170, 130, 80), (140, 100, 60), (200, 170, 120)],
    "frutas": [(245, 205, 40), (230, 120, 30), (200, 40, 50), (120, 180, 60)],
    "abarrotes": [(240, 235, 220), (220, 180, 90), (180, 60, 50), (70, 110, 170)],
    "carnes": [(190, 70, 70), (230, 190, 160), (250, 240, 225)],
    "pescados": [(150, 170, 185), (200, 140, 120), (120, 140, 160)],
}


# --- la foto ilustrada (PNG hecho a mano: sin dependencias) -------------------

def _png(ancho: int, alto: int, filas: list[bytes]) -> bytes:
    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    crudo = b"".join(b"\x00" + f for f in filas)
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
            + trozo(b"IDAT", zlib.compress(crudo, 9)) + trozo(b"IEND", b""))


def foto_de_puesto(clase: str, semilla: int) -> bytes:
    """Un puesto visto desde el pasillo: lona a rayas, mostrador y la mercadería."""
    azar = random.Random(semilla)
    ancho, alto = 480, 360
    lona = LONAS[semilla % len(LONAS)]
    colores = PRODUCTO_COLOR[clase]
    # La mercadería: montoncitos redondos sobre el mostrador.
    bolitas = [(azar.randint(30, ancho - 30), azar.randint(200, 270), azar.randint(14, 24), azar.choice(colores))
               for _ in range(70)]
    bolitas.sort(key=lambda b: b[1])
    pixeles = [[(0, 0, 0)] * ancho for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            if y < 110:   # la lona a rayas, con el borde ondulado
                borde = 100 + int(8 * abs(((x % 60) - 30) / 30))
                if y > borde:
                    c = (235, 228, 214)
                else:
                    c = lona if (x // 40) % 2 == 0 else (250, 246, 238)
            elif y < 180:  # el fondo del puesto
                c = (88, 70, 58) if (x // 120) % 2 else (98, 78, 64)
            elif y < 290:  # el mostrador
                c = (176, 132, 88)
            else:          # el piso del pasillo
                c = (120, 116, 110) if ((x // 30) + (y // 30)) % 2 else (132, 128, 122)
            pixeles[y][x] = c
    for cx, cy, r, color in bolitas:
        for y in range(max(0, cy - r), min(alto, cy + r)):
            for x in range(max(0, cx - r), min(ancho, cx + r)):
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy <= r * r:
                    luz = 1.18 if dx + dy < -r * 0.6 else (0.82 if dx + dy > r * 0.5 else 1.0)
                    pixeles[y][x] = tuple(min(255, int(v * luz)) for v in color)
    # El letrero: una franja clara bajo la lona.
    for y in range(118, 146):
        for x in range(150, 330):
            pixeles[y][x] = (250, 246, 238) if 120 < y < 144 and 152 < x < 328 else lona
    return _png(ancho, alto, [bytes(v for p in fila for v in p) for fila in pixeles])


# --- la siembra --------------------------------------------------------------

def _presentacion_para(producto, mayorista: bool, azar: random.Random) -> Presentacion:
    opciones = list(producto.presentaciones)
    if mayorista:
        for p in (Presentacion.QUINTAL, Presentacion.ARROBA, Presentacion.MAPLE):
            if p in opciones:
                return p
    if Presentacion.ARROBA in opciones and producto.categoria.value == "tuberculo" and azar.random() < 0.4:
        return Presentacion.ARROBA
    for p in (Presentacion.KILO, Presentacion.LITRO, Presentacion.UNIDAD, Presentacion.ATADO):
        if p in opciones:
            return p
    return opciones[0]


def _monto(base: float, presentacion: Presentacion, azar: random.Random, mayorista: bool) -> float:
    monto = base * presentacion.factor * azar.uniform(0.9, 1.1) * (0.88 if mayorista else 1.0)
    paso = 0.5 if monto >= 5 else 0.1
    return max(paso, round(round(monto / paso) * paso, 2))


def _disponibilidad(azar: random.Random) -> Disponibilidad:
    tiro = azar.random()
    return Disponibilidad.AGOTADO if tiro < 0.07 else Disponibilidad.POCO if tiro < 0.22 else Disponibilidad.HAY


class Siembra:
    def __init__(self, contrasena: str):
        self.contrasena = contrasena
        self.azar = random.Random(2026)
        self.usuarios = d._cuentas()[0]
        self.registrar = d.caso_registrar_usuario()
        self.mi_puesto = d.caso_mi_puesto()
        self.inventario = d.caso_inventario()
        self.ofertas = d.caso_ofertas_del_casero()
        self.consultar = d.caso_consultar_precio()
        self.productos = {p.codigo: p for p in d.obtener_productos().listar()}
        self.cuenta = {"caseros": 0, "articulos": 0, "ofertas": 0}

    def _usuario(self, correo: str, nombre: str, vende: bool):
        existente = self.usuarios.obtener_por_correo(correo)
        return existente or self.registrar.registrarse(correo, nombre, self.contrasena, quiere_vender=vende)

    def _base(self, codigo_producto: str, codigo_mercado: str) -> float | None:
        try:
            return self.consultar.ejecutar(codigo_producto, codigo_mercado).rango.centro
        except ErrorDominio:
            return None

    def _cargar_inventario(self, vendedor, codigo_mercado: str, clases: list[str], mayorista: bool) -> None:
        # El primero de cada surtido es lo que nunca falta en ese puesto (el tomate en las verduras).
        tiene = {a.codigo_producto for a in self.inventario.ver(vendedor)}
        estrellas = [SURTIDO[clase][1][0] for clase in clases]
        resto = [c for clase in clases for c in SURTIDO[clase][1][1:]]
        elegidos = [] if tiene else self.azar.sample(resto, k=min(len(resto), self.azar.randint(3, 6)))
        for codigo in dict.fromkeys(c for c in estrellas + elegidos if c not in tiene):
            producto = self.productos.get(codigo)
            base = self._base(codigo, codigo_mercado) if producto else None
            if base is None:
                continue
            presentacion = _presentacion_para(producto, mayorista, self.azar)
            try:
                self.inventario.guardar(vendedor, codigo, _monto(base, presentacion, self.azar, mayorista),
                                        presentacion, _disponibilidad(self.azar))
                self.cuenta["articulos"] += 1
            except ErrorDominio as e:
                log.warning("  %s en %s: %s", codigo, codigo_mercado, e)

    def _oferta(self, vendedor, codigo_mercado: str) -> None:
        """Una rebaja de verdad: por debajo del precio del sistema, o no se publica."""
        for articulo in self.inventario.ver(vendedor):
            base = self._base(articulo.codigo_producto, codigo_mercado)
            if base is None or articulo.disponibilidad is Disponibilidad.AGOTADO:
                continue
            monto = round(base * articulo.presentacion.factor * 0.85, 1)
            try:
                self.ofertas.publicar(vendedor, articulo.codigo_producto, monto, articulo.presentacion,
                                      self.azar.choice([24, 48, 72]), nota="Precio de casera")
                self.cuenta["ofertas"] += 1
                return
            except ErrorDominio:
                continue

    def caseros(self) -> None:
        for i, (mercado, numero, nombre, clase, referencia) in enumerate(PUESTOS):
            correo = f"casero{i + 1:02d}@{DOMINIO}"
            vendedor = self._usuario(correo, f"{NOMBRES[i % len(NOMBRES)]} (prueba)", vende=True)
            try:
                puesto = self.mi_puesto.ver(vendedor)
                if puesto is None:
                    puesto = self.mi_puesto.guardar(vendedor, numero, nombre, [SURTIDO[clase][0]], referencia, mercado)
                if puesto.foto is None:
                    self.mi_puesto.poner_foto(vendedor, foto_de_puesto(clase, i))
                vendedor = self.usuarios.obtener_por_correo(correo)
                nuevo = not self.inventario.ver(vendedor)
                self._cargar_inventario(vendedor, mercado, [clase], mayorista=False)
                if nuevo and i % 3 == 0:
                    self._oferta(vendedor, mercado)
                self.cuenta["caseros"] += 1
                log.info("Puesto %s de %s listo", numero, mercado)
            except ErrorDominio as e:
                log.warning("Puesto %s de %s: %s", numero, mercado, e)

    def distribuidoras(self) -> None:
        for j, (nombre, zona, macro, lat, lon, clases, referencia) in enumerate(DISTRIBUIDORAS):
            correo = f"distribuidora{j + 1:02d}@{DOMINIO}"
            vendedor = self._usuario(correo, f"{nombre} (prueba)", vende=True)
            try:
                puesto = self.mi_puesto.ver(vendedor)
                if puesto is None:
                    puesto = self.mi_puesto.registrar_distribuidora(
                        vendedor, nombre=nombre, zona=zona, macrodistrito=macro, latitud=lat, longitud=lon,
                        rubros=[SURTIDO[c][0] for c in clases], referencia=referencia)
                if puesto.foto is None:
                    self.mi_puesto.poner_foto(vendedor, foto_de_puesto(clases[0], 100 + j))
                vendedor = self.usuarios.obtener_por_correo(correo)
                self._cargar_inventario(vendedor, puesto.codigo_mercado, clases, mayorista=True)
                self.cuenta["caseros"] += 1
                log.info("Distribuidora %s lista", nombre)
            except ErrorDominio as e:
                log.warning("Distribuidora %s: %s", nombre, e)

    def compradora(self) -> None:
        """Una compradora con su lista de la semana y reportes por revisar del administrador."""
        compradora = self._usuario(f"compradora@{DOMINIO}", "Ana (prueba)", vende=False)
        listas = d.caso_gestionar_listas()
        if listas.listar(compradora):   # ya sembrada: no se repiten los reportes
            return
        listas.crear(compradora, "Lo de la semana", [
            RenglonPedido("papa_holandesa", 1, Presentacion.ARROBA),
            RenglonPedido("tomate", 2, Presentacion.KILO),
            RenglonPedido("cebolla", 1, Presentacion.KILO),
            RenglonPedido("arroz_primera", 2, Presentacion.KILO),
            RenglonPedido("pollo_entero", 1, Presentacion.KILO),
        ])
        reportar = d.caso_registrar_reporte()
        for producto, mercado in (("tomate", "rodriguez"), ("papa_holandesa", "lanza"), ("banana", "yungas")):
            base = self._base(producto, mercado)
            if base is not None:
                reportar.ejecutar(compradora, producto, mercado, round(base * 0.95, 1), "kg")


def retirar(motor) -> None:
    """Baja lógica de todo lo que sembró "demo": nada se borra."""
    tablas = ["oferta", "inventario_puesto", "observacion_precio", "reporte_precio", "item_lista_compras",
              "lista_compras", "puesto", "vendedor", "usuario", "mercado"]
    with motor.begin() as conexion:
        for tabla in tablas:
            filas = conexion.execute(text(
                f"UPDATE {tabla} SET eliminado = true, modificado_por = :actor "
                "WHERE creado_por = :actor AND eliminado = false"), {"actor": ACTOR}).rowcount
            print(f"  {tabla:<20} {filas:>5} dados de baja")


def main() -> int:
    actor_actual.set(ACTOR)
    p = argparse.ArgumentParser(description="Datos de prueba: caseros, puestos, inventario y ofertas")
    p.add_argument("--retirar", action="store_true", help="Da de baja (lógica) todo lo que sembró este comando")
    args = p.parse_args()

    if not config.base_datos_url:
        log.error("BASE_DATOS_URL no está configurada: no hay dónde guardar los datos de prueba.")
        return 2
    if "neon.tech" in config.base_datos_url:
        log.error("Esto es la base de Neon: los datos de prueba nunca van a producción.")
        return 2

    if args.retirar:
        retirar(crear_motor(config.base_datos_url))
        print("Datos de prueba retirados.")
        return 0

    contrasena = os.environ.get("DEMO_CONTRASENA", "")
    if not contrasena:
        log.error("Falta DEMO_CONTRASENA en el entorno (docker/.env).")
        return 2

    siembra = Siembra(contrasena)
    siembra.caseros()
    siembra.distribuidoras()
    siembra.compradora()
    c = siembra.cuenta
    print(f"\nListo: {c['caseros']} caseros, {c['articulos']} productos en inventario, {c['ofertas']} ofertas.")
    print(f"Las cuentas son casero01..{len(PUESTOS):02d}@{DOMINIO}, distribuidora01..03@{DOMINIO} "
          f"y compradora@{DOMINIO}; la contraseña está en DEMO_CONTRASENA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
