"""
El casero publica, ve y retira sus ofertas (C133). Los candados viven en
el dominio (dominio/modelo/oferta.py); acá se aplican los que necesitan
mirar afuera: el precio del sistema y cuántas tiene activas.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.casos_uso.precios.ofertas_vigentes import informante_de
from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.casos_uso.vendedor.publicar_precio import punto_de_venta_del
from src.aplicacion.puertos.salida import (
    LectorMercados, LectorObservaciones, LectorProductos, RepositorioOfertas, RepositorioPuestos,
)
from src.dominio.excepciones import OfertaNoEncontrada, OfertaNoPermitida, PresentacionInvalida, ProductoNoEncontrado
from src.dominio.modelo import Confirmacion, EstadoOferta, Oferta, Permiso, Presentacion, Usuario
from src.dominio.modelo.oferta import MAXIMO_ACTIVAS, ahorro_frente_al_sistema
from src.dominio.servicio.motor_fusion import MotorFusion


@dataclass(frozen=True, slots=True)
class MiOferta:
    """Una oferta del casero tal como él la ve: con su estado de hoy y lo que dijeron los compradores."""

    oferta: Oferta
    nombre_producto: str
    estado: str          # activa, vencida, en_revision, retirada
    confirmaron: int
    desmintieron: int


def _estado_de(oferta: Oferta, ahora: datetime) -> str:
    if oferta.estado is EstadoOferta.ACTIVA and oferta.vencida(ahora):
        return "vencida"
    return oferta.estado.value


class OfertasDelCasero:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, ofertas: RepositorioOfertas, puestos: RepositorioPuestos,
                 reloj: Callable[[], object] | None = None, ahora: Callable[[], datetime] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._ofertas = ofertas
        self._puestos = puestos
        self._reloj = reloj
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def publicar(self, vendedor: Usuario, codigo_producto: str, monto: float, presentacion: Presentacion,
                 horas: int, nota: str = "") -> Oferta:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        mercado = punto_de_venta_del(vendedor, self._mercados)
        producto = self._productos.obtener(codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(codigo_producto)
        if presentacion not in producto.presentaciones:
            raise PresentacionInvalida(f"{producto.nombre} no se vende por {presentacion.value}")

        ahora = self._ahora()
        activas = [o for o in self._ofertas.del_vendedor(vendedor.id) if o.vigente(ahora)]
        if len(activas) >= MAXIMO_ACTIVAS:
            raise OfertaNoPermitida(
                f"Ya tiene {MAXIMO_ACTIVAS} ofertas activas: retire una o espere a que venza. "
                "Si todo está en oferta, nada lo está."
            )
        puesto = self._puestos.del_vendedor(vendedor.id)
        oferta = Oferta.nueva(
            id_vendedor=vendedor.id, codigo_mercado=mercado.codigo, codigo_producto=producto.codigo,
            monto=monto, presentacion=presentacion, horas=horas, ahora=ahora, nota=nota,
            numero_puesto=puesto.numero if puesto and puesto.codigo_mercado == mercado.codigo else None,
        )

        # El candado principal: más barata que el precio del sistema en su
        # mercado, calculado sin su propia voz.
        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)
        sistema = referencia.precio(producto.codigo, mercado, sin_informante=informante_de(vendedor.id))
        unidad = presentacion.unidad_base.value
        if sistema is None:
            raise OfertaNoPermitida(
                f"Todavía no hay un precio de {producto.nombre} en {mercado.nombre} contra el cual comparar: "
                "publíquelo como precio normal."
            )
        if ahorro_frente_al_sistema(oferta.precio_por_unidad_base, sistema.rango.centro) is None:
            raise OfertaNoPermitida(
                f"Bs {oferta.precio_por_unidad_base:.2f} por {unidad} no es más barato que el precio "
                f"{sistema.procedencia.value} de {producto.nombre} en {mercado.nombre} "
                f"(Bs {sistema.rango.centro:.2f} por {unidad}). Publíquelo como precio normal."
            )
        return self._ofertas.guardar(oferta)

    def mias(self, vendedor: Usuario) -> list[MiOferta]:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        ahora = self._ahora()
        ofertas = self._ofertas.del_vendedor(vendedor.id)
        confirmaciones = self._ofertas.confirmaciones([o.id for o in ofertas])
        salida = []
        for o in ofertas:
            producto = self._productos.obtener(o.codigo_producto)
            dichas: list[Confirmacion] = confirmaciones.get(o.id, [])
            salida.append(MiOferta(
                oferta=o, nombre_producto=producto.nombre if producto else o.codigo_producto,
                estado=_estado_de(o, ahora),
                confirmaron=sum(c.la_vio_asi for c in dichas),
                desmintieron=sum(not c.la_vio_asi for c in dichas),
            ))
        return salida

    def retirar(self, vendedor: Usuario, id_oferta: int) -> Oferta:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        oferta = self._ofertas.obtener(id_oferta)
        if oferta is None or oferta.id_vendedor != vendedor.id:
            raise OfertaNoEncontrada(id_oferta)
        return self._ofertas.guardar(oferta.retirar())
