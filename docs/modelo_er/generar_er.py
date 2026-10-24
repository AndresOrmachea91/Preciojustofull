"""Genera el Modelo Entidad Relación de PrecioJusto desde el esquema real (information_schema)."""
import html
from collections import defaultdict

AUDITORIA = {"creado_en", "creado_por", "modificado_en", "modificado_por", "eliminado"}
TIPOS = {"character varying": "varchar", "timestamp with time zone": "timestamptz", "double precision": "double",
         "integer": "int", "boolean": "bool", "date": "date"}

cols = defaultdict(list)
for linea in open("cols.txt", encoding="utf-8"):
    t, c, tipo, nulo, _ = linea.strip().split("|")
    cols[t].append((c, TIPOS.get(tipo, tipo), nulo == "YES"))
pk, fk = defaultdict(set), []
for linea in open("keys.txt", encoding="utf-8"):
    t, c, rt, rc, k = linea.strip().split("|")
    if k == "PRIMARY KEY": pk[t].add(c)
    else: fk.append((t, c, rt, rc))
fkcols = {(t, c) for t, c, _, _ in fk}

# Relaciones lógicas: se usan como referencia pero no llevan FK declarada en la base.
LOGICAS = [
    ("observacion_precio", "codigo_producto", "producto"), ("observacion_precio", "codigo_mercado", "mercado"),
    ("reporte_precio", "codigo_producto", "producto"), ("reporte_precio", "codigo_mercado", "mercado"),
    ("item_lista_compras", "codigo_producto", "producto"), ("corrida_fuente", "fuente", "fuente"),
    ("intento_fuente", "fuente", "fuente"),
]
logcols = {(t, c) for t, c, _ in LOGICAS}

GRUPO = {
    "Catálogos": ["rol", "permiso", "rol_permiso", "fuente", "producto", "mercado"],
    "Precios y recolección": ["observacion_precio", "corrida_fuente", "intento_fuente"],
    "Personas y operación": ["usuario", "vendedor", "reporte_precio", "lista_compras", "item_lista_compras",
                             "puesto", "oferta", "confirmacion_oferta"],
}
COLOR = {"Catálogos": "#A9D08E", "Precios y recolección": "#9DC3E6", "Personas y operación": "#F4B183"}

def entidad(t, color):
    filas = [f'<tr><td colspan="3" bgcolor="{color}"><b>{t.upper()}</b></td></tr>']
    for c, tipo, nulo in cols[t]:
        if c in AUDITORIA: continue
        marca = "PK" + (" FK" if (t, c) in fkcols else "") if c in pk[t] else ("FK" if (t, c) in fkcols else ("FK*" if (t, c) in logcols else ""))
        nombre = f"<b>{c}</b>" if c in pk[t] else c
        nombre = nombre if not nulo else f"{nombre}"
        filas.append(f'<tr><td align="left" port="{c}"><font point-size="9">{marca or " "}</font></td>'
                     f'<td align="left">{nombre}</td><td align="left"><font color="#555555">{tipo}{"" if not nulo else " ?"}</font></td></tr>')
    filas.append('<tr><td colspan="3" align="left"><font point-size="8" color="#548235"><i>+ 5 campos de auditoría</i></font></td></tr>')
    return f'  {t} [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="3" bgcolor="white">{"".join(filas)}</table>>];'

out = ['digraph ER {', '  graph [rankdir=LR, splines=true, nodesep=0.3, ranksep=1.4, newrank=true, fontname="Arial", pad=0.4,',
       '         labelloc=t, fontsize=22, label=<<b>PrecioJusto Bolivia — Modelo Entidad Relación</b><br/><br/><font point-size="12">Base de datos PostgreSQL · 19 entidades · generado del esquema real</font>>];',
       '  node [shape=plain, fontname="Arial", fontsize=10];',
       '  edge [fontname="Arial", fontsize=8, color="#3a3a3a", arrowsize=0.8];']
for g, tablas in GRUPO.items():
    out += [entidad(t, COLOR[g]) for t in tablas]

def arista(t, c, rt, rc, logica=False):
    # muchos (crow) del lado de la tabla que referencia; uno (tee) del lado referenciado.
    uno_a_uno = t == "vendedor" and c == "id_usuario"
    cola = "tee" if uno_a_uno else ("crowodot" if any(x[0] == c and x[2] for x in cols[t]) else "crowtee")
    estilo = ', style=dashed' if logica else ''
    return f'  {rt} -> {t}:{c}:w [dir=both, arrowhead={cola}, arrowtail=tee{estilo}];'

for t, c, rt, rc in fk:
    out.append(arista(t, c, rt, rc))
for t, c, rt in LOGICAS:
    out.append(arista(t, c, rt, "codigo", logica=True))

leyenda = ('<table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="white">'
 '<tr><td colspan="2" bgcolor="#E2EFDA"><b>Leyenda</b></td></tr>'
 '<tr><td align="left">PK / FK</td><td align="left">clave primaria / clave foránea declarada</td></tr>'
 '<tr><td align="left">FK*</td><td align="left">referencia lógica sin restricción en la base (línea punteada)</td></tr>'
 '<tr><td align="left">tipo ?</td><td align="left">admite nulo</td></tr>'
 '<tr><td align="left">pata de gallo</td><td align="left">lado "muchos"; con círculo = opcional</td></tr>'
 '<tr><td align="left" bgcolor="#A9D08E">verde</td><td align="left">catálogos</td></tr>'
 '<tr><td align="left" bgcolor="#9DC3E6">azul</td><td align="left">precios y recolección</td></tr>'
 '<tr><td align="left" bgcolor="#F4B183">naranja</td><td align="left">personas y operación</td></tr>'
 '<tr><td align="left">auditoría</td><td align="left">todas las tablas: creado_en, creado_por, modificado_en, modificado_por, eliminado (borrado lógico)</td></tr>'
 '<tr><td align="left">vendedor</td><td align="left">herencia 1 a 1 de usuario (su PK es también FK)</td></tr>'
 '</table>')
out.append(f'  leyenda [label=<{leyenda}>];')
out.append("}")
open("modelo_er.dot", "w", encoding="utf-8").write("\n".join(out))
print("ok")
