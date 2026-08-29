"""Errores del dominio. No conocen HTTP ni códigos de estado."""


class ErrorDominio(Exception):
    """Raíz de todos los errores del dominio."""


class ProductoNoEncontrado(ErrorDominio):
    def __init__(self, codigo: str):
        self.codigo = codigo
        super().__init__(f"No existe el producto {codigo}")


class MercadoNoEncontrado(ErrorDominio):
    def __init__(self, codigo: str):
        self.codigo = codigo
        super().__init__(f"No existe el mercado {codigo}")


class UnidadDesconocida(ErrorDominio):
    def __init__(self, unidad: str):
        self.unidad = unidad
        super().__init__(f"No se puede convertir la unidad {unidad!r}")


class SinObservaciones(ErrorDominio):
    """No hay ninguna observación para consolidar un precio."""

