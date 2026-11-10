-- Vistas con nombres sencillos para revisar la base (Navicat, psql…).
--
-- Muestran los mismos datos que las tablas, al día, con nombres en palabras
-- simples. El programa sigue usando las tablas originales: estas vistas son
-- solo para mirar. Se crean en el esquema «consultas» y se quitan con:
--     DROP SCHEMA consultas CASCADE;
--
-- Aplicar en la base local de Docker:
--     docker compose exec -T db psql -U preciojusto -d preciojusto < docker/consultas_sencillas.sql
--
-- Las columnas de auditoría se llaman igual en todas:
--     creado_el, creado_por, cambiado_el, cambiado_por, dado_de_baja

DROP SCHEMA IF EXISTS consultas CASCADE;
CREATE SCHEMA consultas;
COMMENT ON SCHEMA consultas IS 'Vistas de solo lectura con nombres sencillos. El sistema usa las tablas de public.';

-- Todos los precios: del SIIP, de campo, de las caseras y de la gente.
CREATE VIEW consultas.precios AS
SELECT id                       AS numero,
       codigo_producto          AS producto,
       codigo_mercado           AS lugar,
       ciudad,
       puesto,
       fuente,
       nivel,
       precio_monto             AS monto,
       unidad_texto             AS unidad,
       cantidad,
       precio_canonico          AS precio_por_unidad_base,
       unidad_canonica          AS unidad_base,
       fecha_observacion        AS fecha_del_precio,
       anio, mes, dia,
       variedad,
       tipo_precio,
       informante               AS quien_lo_dijo,
       reputacion_informante    AS cuanto_se_le_cree,
       evidencia                AS de_donde_salio,
       ambito,
       capturada_en             AS visto_el,
       ultima_captura_en        AS visto_por_ultima_vez,
       revisa_a                 AS corrige_al_numero,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.observacion_precio;

-- Mercados, sectores, distribuidoras y mayoristas.
CREATE VIEW consultas.lugares_de_venta AS
SELECT codigo, nombre, tipo, zona, macrodistrito, latitud, longitud,
       factor_mercado           AS ajuste_de_precio,
       codigo_padre             AS es_sector_de,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.mercado;

CREATE VIEW consultas.productos AS
SELECT codigo, nombre, categoria,
       unidad_base,
       presentaciones           AS se_vende_por,
       dias_conservacion        AS dias_que_dura,
       zona_origen              AS de_donde_viene,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.producto;

-- Las cuentas (sin la contraseña cifrada: no hace falta verla).
CREATE VIEW consultas.cuentas AS
SELECT id                       AS numero,
       correo, nombre, rol,
       activo                   AS puede_entrar,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.usuario;

CREATE VIEW consultas.vendedores AS
SELECT id_usuario               AS cuenta,
       codigo_punto_venta       AS lugar,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.vendedor;

CREATE VIEW consultas.roles AS
SELECT codigo, nombre, descripcion,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.rol;

CREATE VIEW consultas.permisos AS
SELECT codigo, descripcion,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.permiso;

CREATE VIEW consultas.permisos_de_cada_rol AS
SELECT codigo_rol               AS rol,
       codigo_permiso           AS permiso,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.rol_permiso;

CREATE VIEW consultas.fuentes_de_precios AS
SELECT codigo, nombre, descripcion,
       confianza_base           AS cuanto_se_le_cree,
       deriva_de                AS copia_a,
       automatica               AS la_trae_el_recolector,
       url                      AS direccion,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.fuente;

-- Cada vez que se bajaron precios del SIIP.
CREATE VIEW consultas.recolecciones AS
SELECT id                       AS numero,
       fuente,
       codigo_producto          AS producto,
       hechos_vistos            AS precios_vistos,
       hechos_nuevos            AS precios_nuevos,
       ocurrido_en              AS cuando,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.corrida_fuente;

-- Cada llamada al SIIP: si respondió y cuánto tardó.
CREATE VIEW consultas.llamadas_al_siip AS
SELECT id                       AS numero,
       fuente,
       url                      AS direccion,
       (exito = 1)              AS respondio,
       duracion_ms              AS tardo_milisegundos,
       detalle                  AS error,
       ocurrido_en              AS cuando,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.intento_fuente;

-- Los precios que manda la gente para que un administrador los revise.
CREATE VIEW consultas.precios_reportados AS
SELECT id                       AS numero,
       codigo_producto          AS producto,
       codigo_mercado           AS lugar,
       monto, unidad,
       id_autor                 AS lo_reporto,
       estado,
       id_revisor               AS lo_reviso,
       revisado_en              AS revisado_el,
       motivo_rechazo           AS por_que_se_rechazo,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.reporte_precio;

-- Las listas de compra de cada persona y lo que lleva cada una.
CREATE VIEW consultas.listas AS
SELECT id                       AS numero,
       id_usuario               AS cuenta,
       nombre,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.lista_compras;

CREATE VIEW consultas.productos_de_cada_lista AS
SELECT id                       AS numero,
       id_lista                 AS lista,
       codigo_producto          AS producto,
       cantidad,
       presentacion             AS por,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.item_lista_compras;

-- Los puestos de las caseras y los locales de las distribuidoras.
CREATE VIEW consultas.puestos AS
SELECT id                       AS numero_interno,
       codigo_mercado           AS lugar,
       numero                   AS numero_de_puesto,
       nombre, rubros           AS que_vende,
       referencia               AS como_encontrarlo,
       celular                  AS telefono_de_contacto,
       foto,
       id_vendedor              AS duena,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.puesto;

CREATE VIEW consultas.inventario AS
SELECT id                       AS numero,
       id_puesto                AS puesto,
       codigo_producto          AS producto,
       monto, presentacion      AS por,
       disponibilidad           AS le_queda,
       actualizado_en           AS actualizado_el,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.inventario_puesto;

CREATE VIEW consultas.ofertas AS
SELECT id                       AS numero,
       id_vendedor              AS casera,
       codigo_mercado           AS lugar,
       numero_puesto            AS puesto,
       codigo_producto          AS producto,
       monto, presentacion      AS por,
       precio_por_unidad_base,
       combo,
       nota,
       estado,
       desde, hasta,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.oferta;

CREATE VIEW consultas.opiniones_de_ofertas AS
SELECT id                       AS numero,
       id_oferta                AS oferta,
       id_usuario               AS cuenta,
       la_vio_asi,
       creado_en AS creado_el, creado_por, modificado_en AS cambiado_el, modificado_por AS cambiado_por, eliminado AS dado_de_baja
FROM public.confirmacion_oferta;
