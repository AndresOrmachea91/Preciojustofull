-- Demo de todo el sistema: «la vida de un precio».
-- En VS Code (SQLTools): cursor sobre la consulta y Ctrl+E Ctrl+E.

-- PASO 1 · El precio oficial entra solo (tablas: corrida_fuente, intento_fuente, observacion_precio, fuente)
SELECT * FROM consultas.recolecciones ORDER BY 1 DESC LIMIT 5;
SELECT fuente, count(*) AS precios FROM consultas.precios GROUP BY fuente ORDER BY precios DESC;

-- PASO 2 · El mapa: productos y lugares (tablas: producto, mercado)
SELECT count(*) AS productos FROM producto;
SELECT tipo, count(*) AS lugares FROM mercado GROUP BY tipo;

-- PASO 3 · La casera y su puesto (tablas: usuario, vendedor, puesto, inventario_puesto)
SELECT p.numero AS puesto, i.codigo_producto AS producto, i.monto, i.presentacion AS por,
       i.cantidad AS le_quedan, i.minimo AS avisar_desde, i.disponibilidad AS estado,
       i.modificado_en AS cambiado_el, i.modificado_por AS cambiado_por
FROM inventario_puesto i
JOIN puesto p ON p.id = i.id_puesto
JOIN usuario u ON u.id = p.id_vendedor
WHERE u.correo LIKE 'casero01@%' AND NOT i.eliminado
ORDER BY i.codigo_producto;

-- PASO 4 · Su precio entra al cálculo como «declarado por el vendedor» (tabla: observacion_precio)
SELECT numero, producto, lugar, puesto, monto, unidad, creado_el, creado_por
FROM consultas.precios WHERE fuente = 'vendedor' ORDER BY numero DESC LIMIT 5;

-- PASO 5 · Sus ofertas y lo que dicen los compradores (tablas: oferta, confirmacion_oferta)
SELECT casera, lugar, puesto, producto, monto, por, hasta
FROM consultas.ofertas WHERE estado = 'activa' AND hasta > now() ORDER BY hasta;
SELECT * FROM consultas.opiniones_de_ofertas LIMIT 10;

-- PASO 6 · El comprador arma su lista (tablas: lista_compras, item_lista_compras)
SELECT * FROM consultas.listas ORDER BY 1 DESC LIMIT 5;
SELECT * FROM consultas.productos_de_cada_lista ORDER BY 1 DESC LIMIT 10;

-- PASO 7 · El comprador reporta un precio y el administrador lo revisa (tabla: reporte_precio)
SELECT * FROM consultas.precios_reportados ORDER BY 1 DESC LIMIT 5;

-- PASO 8 · Quién puede hacer qué (tablas: usuario, rol, permiso, rol_permiso)
SELECT * FROM consultas.permisos_de_cada_rol;
