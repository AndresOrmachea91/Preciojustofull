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

    def __init__(self, ciudad: str):
        self.ciudad = ciudad
        super().__init__(
            f"Las observaciones de ámbito ciudad ({ciudad}) no son mediciones "
            "de un local: úsese MotorFusion.estimar_desde_ciudad"
        )


class GruposNoComparables(ErrorDominio):
    """
    Se pidió UN precio para observaciones que no son comparables entre sí
    (variedad, unidad o período distintos). No es conflicto: son grupos
    separados, y se publican por separado.
    """

    def __init__(self, claves: list[str]):
        self.claves = list(claves)
        super().__init__("Las observaciones forman grupos no comparables: " + "; ".join(self.claves))


class DerivacionCiclica(ErrorDominio):
    """La relación deriva_de entre fuentes tiene un ciclo: un clan se contendría a sí mismo."""

    def __init__(self, ciclo: list[str]):
        self.ciclo = list(ciclo)
        super().__init__("Ciclo en la derivación de fuentes: " + " -> ".join(self.ciclo))


class NivelesNoComparables(ErrorDominio):
    """Se intentó mezclar precios mayoristas con precios de consumidor final."""

    def __init__(self, niveles: set[str]):
        self.niveles = niveles
        super().__init__(
            "No se pueden consolidar observaciones de niveles distintos: "
            + ", ".join(sorted(niveles))
        )


# --- usuarios, sesiones y reportes ---------------------------------------

class CorreoInvalido(ErrorDominio):
    def __init__(self, correo: str):
        self.correo = correo
        super().__init__(f"El correo {correo!r} no es válido")


class ContrasenaDebil(ErrorDominio):
    """La contraseña no cumple la política mínima."""


class CorreoYaRegistrado(ErrorDominio):
    def __init__(self, correo: str):
        self.correo = correo
        super().__init__(f"Ya existe una cuenta con el correo {correo}")


class CredencialesInvalidas(ErrorDominio):
    """
    Correo o contraseña incorrectos, o cuenta desactivada. Es UN solo error
    a propósito: decir cuál de las dos falló le enseña a un atacante qué
    correos existen.
    """

    def __init__(self):
        super().__init__("Correo o contraseña incorrectos")


class UsuarioNoEncontrado(ErrorDominio):
    def __init__(self, id_usuario: int):
        self.id_usuario = id_usuario
        super().__init__(f"No existe el usuario {id_usuario}")


class PermisoDenegado(ErrorDominio):
    def __init__(self, permiso: str):
        self.permiso = permiso
        super().__init__(f"No tiene permiso para {permiso}")


class SinAdministradores(ErrorDominio):
    """El cambio dejaría al sistema sin ningún administrador activo."""

    def __init__(self):
        super().__init__("Debe quedar al menos un administrador activo")


class AutoEliminacion(ErrorDominio):
    """Un administrador no puede eliminar su propia cuenta."""

    def __init__(self):
        super().__init__("No puede eliminar su propia cuenta")


class ReporteNoEncontrado(ErrorDominio):
    def __init__(self, id_reporte: int):
        self.id_reporte = id_reporte
        super().__init__(f"No existe el reporte {id_reporte}")


class ReporteYaRevisado(ErrorDominio):
    def __init__(self, id_reporte: int | None, estado: str):
        self.id_reporte = id_reporte
        self.estado = estado
        super().__init__(f"El reporte {id_reporte} ya fue revisado ({estado})")


# --- catálogo ---------------------------------------------------------------

class PresentacionInvalida(ErrorDominio):
    """Las presentaciones de venta no corresponden a la unidad del producto."""


class CodigoYaExiste(ErrorDominio):
    def __init__(self, que: str, codigo: str):
        self.codigo = codigo
        super().__init__(f"Ya existe un {que} con el código {codigo}")


class DatoInvalido(ErrorDominio):
    """Un dato del catálogo no cumple su regla (coordenadas, nombre vacío...)."""


class PuntoVentaConDependientes(ErrorDominio):
    def __init__(self, codigo: str, motivo: str):
        self.codigo = codigo
        super().__init__(f"No se puede eliminar {codigo}: {motivo}")


# --- vendedor y listas de compras -------------------------------------------

class SinPuntoVenta(ErrorDominio):
    """El vendedor todavía no tiene puesto asignado: no hay dónde publicar."""

    def __init__(self):
        super().__init__("Todavía no tiene un puesto asignado. Pídale al administrador que se lo asigne.")


class ListaNoEncontrada(ErrorDominio):
    def __init__(self, id_lista: int):
        self.id_lista = id_lista
        super().__init__(f"No existe la lista {id_lista}")
