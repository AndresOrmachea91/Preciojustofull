"""
Ofertas pausadas por los compradores (C133): el administrador las mira y
decide. Reactivar es decir "era verdad"; retirar, "no lo era". Ninguna de
las dos borra nada: la oferta y sus confirmaciones quedan con su auditoría.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import LectorMercados, LectorProductos, RepositorioOfertas
from src.dominio.excepciones import OfertaNoEncontrada
from src.dominio.modelo import EstadoOferta, Oferta, Permiso, Usuario


@dataclass(frozen=True, slots=True)
class OfertaEnRevision:
    oferta: Oferta
    nombre_producto: str
    nombre_mercado: str
    confirmaron: int
    desmintieron: int


class RevisarOfertas:
    def __init__(self, ofertas: RepositorioOfertas, productos: LectorProductos, mercados: LectorMercados):
        self._ofertas = ofertas
        self._productos = productos
        self._mercados = mercados

    def pendientes(self, actor: Usuario) -> list[OfertaEnRevision]:
        exigir(actor, Permiso.VALIDAR_REPORTES)
        ofertas = self._ofertas.en_revision()
        confirmaciones = self._ofertas.confirmaciones([o.id for o in ofertas])
        salida = []
        for o in ofertas:
            producto = self._productos.obtener(o.codigo_producto)
            mercado = self._mercados.obtener(o.codigo_mercado)
            dichas = confirmaciones.get(o.id, [])
            salida.append(OfertaEnRevision(
                oferta=o, nombre_producto=producto.nombre if producto else o.codigo_producto,
                nombre_mercado=mercado.nombre if mercado else o.codigo_mercado,
                confirmaron=sum(c.la_vio_asi for c in dichas),
                desmintieron=sum(not c.la_vio_asi for c in dichas),
            ))
        return salida

    def reactivar(self, actor: Usuario, id_oferta: int) -> Oferta:
        return self._decidir(actor, id_oferta, reactivar=True)

    def retirar(self, actor: Usuario, id_oferta: int) -> Oferta:
        return self._decidir(actor, id_oferta, reactivar=False)

    def _decidir(self, actor: Usuario, id_oferta: int, reactivar: bool) -> Oferta:
        exigir(actor, Permiso.VALIDAR_REPORTES)
        oferta = self._ofertas.obtener(id_oferta)
        if oferta is None or oferta.estado is not EstadoOferta.EN_REVISION:
            raise OfertaNoEncontrada(id_oferta)
        return self._ofertas.guardar(oferta.reactivar() if reactivar else oferta.retirar())
