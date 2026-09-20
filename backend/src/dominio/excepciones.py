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



class JerarquiaInvalida(ErrorDominio):
    """La relación padre-hijo entre puntos de venta rompe una invariante."""

    def __init__(self, infracciones: list[str]):
        self.infracciones = list(infracciones)
        super().__init__("Jerarquía inválida: " + "; ".join(self.infracciones))


class ReferenciaNoEsMedicion(ErrorDominio):
    """
    Se intentó consolidar como precio de un local un dato que la fuente
    publica por ciudad. Ese dato es referencia para estimar, no medición.
    """

    def __init__(self, codigo_mercado: str):
        self.codigo_mercado = codigo_mercado
        super().__init__(
            f"Las observaciones de ámbito ciudad ({codigo_mercado}) no son mediciones "
            "de un local: úsese MotorFusion.estimar_desde_ciudad"
        )


class NivelesNoComparables(ErrorDominio):
    """Se intentó mezclar precios mayoristas con precios de consumidor final."""

    def __init__(self, niveles: set[str]):
        self.niveles = niveles
        super().__init__(
            "No se pueden consolidar observaciones de niveles distintos: "
            + ", ".join(sorted(niveles))
        )
