"""
Diagrama del flujo completo de PrecioJusto: de dónde entran los precios,
dónde se guardan (con los nombres sencillos del esquema consultas), cómo se
calculan y quién los ve. Cuatro columnas, todo de izquierda a derecha.

    python docs/modelo_er/flujo_del_sistema.py   →   docs/flujo_del_sistema.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SALIDA = Path(__file__).resolve().parents[1] / "flujo_del_sistema.png"
plt.rcParams["font.family"] = "Arial"

ANCHO, ALTO = 30.0, 19.0
fig = plt.figure(figsize=(ANCHO * 0.62, ALTO * 0.62), dpi=200)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, ANCHO)
ax.set_ylim(0, ALTO)
ax.axis("off")

CARRILES = [
    (0.3, 6.6, "1. Entran los precios", "#EAF4FF", "#9CC3E6"),
    (7.0, 14.6, "2. Se guardan en PostgreSQL", "#FFF7E6", "#E6C27A"),
    (15.0, 21.6, "3. Se calculan", "#EEF8EE", "#9ACB9A"),
    (22.0, 29.7, "4. Se muestran", "#F4EEFB", "#BFA6E0"),
]
for x0, x1, titulo, fondo, borde in CARRILES:
    ax.add_patch(FancyBboxPatch((x0, 0.3), x1 - x0, ALTO - 2.1, boxstyle="round,pad=0,rounding_size=0.3",
                                fc=fondo, ec=borde, lw=1.2))
    ax.text((x0 + x1) / 2, ALTO - 2.25, titulo, ha="center", va="center", fontsize=13, weight="bold")
ax.text(ANCHO / 2, ALTO - 0.55, "PrecioJusto: cómo viaja un precio por el sistema", ha="center", fontsize=16, weight="bold")
ax.text(ANCHO / 2, ALTO - 1.15, "Los números marcan el orden. En la columna 2, arriba el nombre sencillo (esquema consultas) "
        "y en color el nombre real de la tabla.", ha="center", fontsize=9.5, color="#444444")

CAJAS = {}


def caja(id_, x, y, w, h, titulo, detalle, fondo="white", real=None):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.18",
                                fc=fondo, ec="#555555", lw=1.1, zorder=3))
    lineas = [titulo]
    ax.text(x, y + h / 2 - 0.32, titulo, ha="center", va="center", fontsize=10.5, weight="bold", zorder=4)
    yy = y + h / 2 - 0.68
    if real:
        ax.text(x, yy, real, ha="center", va="center", fontsize=8.3, color="#8A6300", zorder=4)
        yy -= 0.36
    ax.text(x, yy, detalle, ha="center", va="top", fontsize=8.6, color="#222222", zorder=4, linespacing=1.25)
    CAJAS[id_] = (x, y, w, h)


def borde(id_, lado, desp=0.0):
    x, y, w, h = CAJAS[id_]
    return {"der": (x + w / 2, y + desp), "izq": (x - w / 2, y + desp),
            "arr": (x + desp, y + h / 2), "aba": (x + desp, y - h / 2)}[lado]


def flecha(a, b, texto=None, punteada=False, curva=0.0, pos=0.5, dx=0.0, dy=0.18):
    p = FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, lw=1.15, color="#444444",
                        linestyle="--" if punteada else "-", connectionstyle=f"arc3,rad={curva}", zorder=2,
                        shrinkA=1, shrinkB=1)
    ax.add_patch(p)
    if texto:
        mx = a[0] + (b[0] - a[0]) * pos + dx
        my = a[1] + (b[1] - a[1]) * pos + dy
        ax.text(mx, my, texto, ha="center", va="bottom", fontsize=8.6, color="#333333", zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


# --- 1. Entran -----------------------------------------------------------------
caja("siip", 3.45, 14.6, 5.2, 1.5, "SIIP (fuente oficial)", "boletín diario e IPC;\nel recolector lo baja todos los días")
caja("adm", 3.45, 11.9, 5.2, 1.5, "Administrador", "sube la planilla\nde la ronda de campo")
caja("comp", 3.45, 7.3, 5.2, 1.7, "Comprador", "reporta el precio que vio\ny arma sus listas de compra")
caja("cas", 3.45, 3.4, 5.2, 1.7, "Casera / distribuidora", "su puesto, inventario, precios,\nofertas y combos")

# --- 2. Se guardan -------------------------------------------------------------------
X2, W2 = 10.8, 6.6
caja("recol", X2, 15.55, W2, 1.25, "recolecciones · llamadas_al_siip", "cada bajada y cada llamada al SIIP",
     "#FFFDF7", "corrida_fuente · intento_fuente")
caja("precios", X2, 13.45, W2, 1.75, "precios", "TODOS los precios con su fuente, lugar y fecha\n(SIIP, campo, vendedor y ciudadano)",
     "#FFF1C9", "observacion_precio")
caja("fuentes", X2, 11.55, W2, 1.25, "fuentes_de_precios", "de dónde sale cada precio y cuánto se le cree",
     "#FFFDF7", "fuente")
caja("cat", X2, 10.0, W2, 1.25, "productos · lugares_de_venta", "45 productos · 69 lugares (mercados, distribuidoras)",
     "#FFFDF7", "producto · mercado")
caja("rep", X2, 8.35, W2, 1.25, "precios_reportados", "lo que manda la gente, pendiente de revisar",
     "#FFFDF7", "reporte_precio")
caja("listas", X2, 6.7, W2, 1.25, "listas · productos_de_cada_lista", "la lista de cada persona y lo que lleva",
     "#FFFDF7", "lista_compras · item_lista_compras")
caja("puestos", X2, 5.0, W2, 1.25, "puestos · inventario", "el puesto, su teléfono y «hay / queda poco / se acabó»",
     "#FFFDF7", "puesto · inventario_puesto")
caja("ofertas", X2, 3.3, W2, 1.25, "ofertas · opiniones_de_ofertas", "ofertas, combos y los «lo vi así»",
     "#FFFDF7", "oferta · confirmacion_oferta")
caja("cuentas", X2, 1.4, W2, 1.25, "cuentas · roles · permisos", "quién es quién y qué puede hacer",
     "#FFFDF7", "usuario · rol · permiso")

# --- 3. Se calculan ------------------------------------------------------------------
caja("motor", 18.3, 12.3, 5.8, 2.5, "Motor de fusión",
     "¿alguien lo midió en ese lugar?\nsí → observado\nno → estimado desde el precio de la ciudad\nsiempre con rango, fecha y confianza", "#F7FCF7")
caja("plan", 18.3, 6.0, 5.8, 2.3, "Plan de compra",
     "comprar en 1, 2 o 3 mercados\n+ pasaje (Bs 3; Bs 3,50 a la Zona Sur)\ngana · pierde · neto", "#F7FCF7")

# --- 4. Se muestran ------------------------------------------------------------------
caja("ref", 25.85, 14.9, 6.9, 1.45, "Precios referenciales", "el precio de la ciudad y su historial")
caja("mapa", 25.85, 12.1, 6.9, 1.85, "Mapa de precios", "pines por lugar; al tocar un mercado,\nsus puestos en ramas con su inventario\ny la estrella de las ofertas")
caja("listasv", 25.85, 8.3, 6.9, 1.45, "Mis listas", "dónde conviene comprar y a qué caseras ir")
caja("ofhoy", 25.85, 4.6, 6.9, 1.45, "Ofertas de hoy", "ofertas y combos vigentes")
caja("admv", 25.85, 1.8, 6.9, 1.9, "Administración", "revisa precios reportados y ofertas,\nmira la salud (recolecciones) y la auditoría,\nregistra caseras y da de baja")

# --- Flechas -----------------------------------------------------------------------
flecha(borde("siip", "der", 0.3), borde("recol", "izq"), "1  recolector", pos=0.45)
flecha(borde("siip", "der", -0.3), borde("precios", "izq", 0.2), "2  solo lo nuevo", pos=0.55)
flecha(borde("adm", "der"), borde("precios", "izq", -0.4), "2  fuente: campo", pos=0.5)
flecha(borde("comp", "der", 0.35), borde("rep", "izq"), "2", pos=0.5)
flecha(borde("comp", "der", -0.35), borde("listas", "izq"), "2", pos=0.5)
flecha(borde("cas", "der", 0.45), borde("puestos", "izq"), "2", pos=0.5)
flecha(borde("cas", "der", -0.45), borde("ofertas", "izq"), "2  solo si es más barata", pos=0.5, dy=-0.62)
# Dentro de la base: el reporte aprobado y el precio de la casera pasan a «precios».
flecha(borde("rep", "der", 0.0), (X2 + W2 / 2 + 0.25, 8.35), None)
ax.plot([X2 + W2 / 2 + 0.25, X2 + W2 / 2 + 0.25], [8.35, 13.1], color="#444444", lw=1.15, ls="--", zorder=2)
flecha((X2 + W2 / 2 + 0.25, 13.1), (X2 + W2 / 2, 13.1), None, punteada=True)
ax.text(X2 + W2 / 2 + 0.38, 9.4, "5  aprobado por el\nadministrador\n→ fuente: ciudadano", fontsize=8.2, color="#333333",
        ha="left", va="center", zorder=5, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
ax.plot([X2 - W2 / 2 - 0.25] * 2, [5.0, 13.6], color="#444444", lw=1.15, zorder=2)
ax.plot([X2 - W2 / 2 - 0.25, X2 - W2 / 2], [5.0, 5.0], color="#444444", lw=1.15, zorder=2)
flecha((X2 - W2 / 2 - 0.25, 13.6), (X2 - W2 / 2, 13.6), None)
ax.text(X2 - W2 / 2 - 0.35, 9.2, "su precio\n→ fuente:\nvendedor", fontsize=8.2, color="#333333", ha="right", va="center",
        zorder=5, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))

flecha(borde("precios", "der", 0.2), borde("motor", "izq", 0.6), "3", pos=0.5)
flecha(borde("fuentes", "der"), borde("motor", "izq", -0.2), "3", pos=0.5)
flecha(borde("cat", "der"), borde("motor", "izq", -0.8), "3", pos=0.5)
flecha(borde("motor", "aba"), borde("plan", "arr"), "precio en cada lugar", pos=0.5, dx=1.5)
flecha(borde("listas", "der"), borde("plan", "izq", 0.5), "4", pos=0.5)
flecha(borde("puestos", "der"), borde("plan", "izq", -0.2), "caseras que lo tienen", pos=0.5, dy=-0.62)
flecha(borde("ofertas", "der"), borde("plan", "izq", -0.8), "sus ofertas", pos=0.55, dy=-0.62)

flecha(borde("motor", "der", 0.7), borde("ref", "izq"), "4", pos=0.5)
flecha(borde("motor", "der", -0.2), borde("mapa", "izq"), "4", pos=0.5)
flecha(borde("plan", "der", 0.5), borde("listasv", "izq"), "4", pos=0.5)
flecha(borde("ofertas", "der", -0.35), borde("ofhoy", "izq"), "4", pos=0.82)
flecha(borde("cuentas", "der"), borde("admv", "izq"), "quién puede entrar y qué hacer", pos=0.5)

fig.savefig(SALIDA, dpi=200, facecolor="white")
print(SALIDA)
