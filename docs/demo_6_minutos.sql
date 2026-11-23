-- Demo de 6 minutos: lo que pasa en la pantalla y cómo queda en la base.
-- En VS Code (SQLTools): cursor sobre la consulta y Ctrl+E Ctrl+E.

-- A) Lo que se ve en el mapa sale de aquí: cada precio con su fuente
SELECT fuente, count(*) AS precios FROM consultas.precios GROUP BY fuente ORDER BY precios DESC;

-- B) El inventario de la casera del puesto 14 (Rodríguez): cuánto le queda y desde cuánto avisar
SELECT p.numero AS puesto, i.codigo_producto AS producto, i.monto, i.presentacion AS por,
       i.cantidad AS le_quedan, i.minimo AS avisar_desde, i.disponibilidad AS estado,
       i.modificado_en AS cambiado_el, i.modificado_por AS cambiado_por
FROM inventario_puesto i
JOIN puesto p ON p.id = i.id_puesto
JOIN usuario u ON u.id = p.id_vendedor
WHERE u.correo LIKE 'casero01@%' AND NOT i.eliminado
ORDER BY i.codigo_producto;

-- C) El precio que publica la casera entra como «declarado por el vendedor»
SELECT numero, producto, lugar, puesto, monto, unidad, creado_el, creado_por
FROM consultas.precios WHERE fuente = 'vendedor' ORDER BY numero DESC LIMIT 5;

-- D) Las ofertas vigentes (con estrella en el mapa)
SELECT casera, lugar, puesto, producto, monto, por, hasta
FROM consultas.ofertas WHERE estado = 'activa' AND hasta > now() ORDER BY hasta;

-- E) Cada bajada del SIIP queda registrada
SELECT * FROM consultas.recolecciones ORDER BY 1 DESC LIMIT 5;
