-- Consultas listas para mostrar la base de PrecioJusto.
-- En VS Code: conéctese a «PrecioJusto (Docker)» en el panel de SQLTools,
-- ponga el cursor sobre una consulta y apriete Ctrl+E dos veces (o «Run on active connection»).
-- Todas leen el esquema «consultas», que tiene los nombres sencillos de cada tabla.

-- 1. Los puestos registrados: dónde están, qué venden y su teléfono
SELECT lugar, numero_de_puesto, nombre, que_vende, telefono_de_contacto, duena
FROM consultas.puestos
WHERE NOT dado_de_baja
ORDER BY lugar, numero_de_puesto;

-- 2. Lo que cada casera tiene hoy y a cuánto
SELECT * FROM consultas.inventario LIMIT 50;

-- 3. Las ofertas vigentes (las que se ven en «Ofertas de hoy»)
SELECT casera, lugar, puesto, producto, monto, por, combo, nota, hasta
FROM consultas.ofertas
WHERE estado = 'activa' AND hasta > now()
ORDER BY hasta;

-- 4. Las listas de compra de cada persona y lo que llevan
SELECT * FROM consultas.listas;
SELECT * FROM consultas.productos_de_cada_lista LIMIT 50;

-- 5. Todos los precios guardados, con su fuente (SIIP, campo, vendedor o ciudadano)
SELECT * FROM consultas.precios ORDER BY 1 DESC LIMIT 50;

-- 6. Cuántos precios aportó cada fuente
SELECT * FROM consultas.fuentes_de_precios;

-- 7. Lo que reportó la gente y está esperando revisión
SELECT * FROM consultas.precios_reportados LIMIT 50;

-- 8. Las cuentas y sus roles (sin contraseñas)
SELECT * FROM consultas.cuentas LIMIT 50;

-- 9. Cada vez que el recolector bajó precios del SIIP
SELECT * FROM consultas.recolecciones ORDER BY 1 DESC LIMIT 20;
