-- Script de inicio de la base de datos de PrecioJusto.
--
-- Docker lo ejecuta solo, una única vez, cuando el contenedor «db» arranca con el
-- volumen de datos vacío (docker-compose.yml lo monta en /docker-entrypoint-initdb.d).
-- Crea la estructura completa: las 18 tablas, sus índices y relaciones, y el esquema
-- «consultas» con las vistas de nombres sencillos. No trae datos ni contraseñas.
--
-- Si la base ya existe, Docker no lo vuelve a correr. La aplicación revisa la misma
-- estructura al arrancar (sesion.py, crear_esquema), así que las dos formas coinciden.
--
-- Para regenerarlo después de cambiar el modelo:
--   docker compose exec -T db pg_dump -U preciojusto -d preciojusto --schema-only --no-owner --no-privileges

--
-- PostgreSQL database dump
--


-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: consultas; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA consultas;


--
-- Name: SCHEMA consultas; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA consultas IS 'Vistas de solo lectura con nombres sencillos. El sistema usa las tablas de public.';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id integer NOT NULL,
    correo character varying(255) NOT NULL,
    nombre character varying(255) NOT NULL,
    rol character varying(16) NOT NULL,
    hash_contrasena character varying(255) NOT NULL,
    activo boolean NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL
);


--
-- Name: cuentas; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.cuentas AS
 SELECT id AS numero,
    correo,
    nombre,
    rol,
    activo AS puede_entrar,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.usuario;


--
-- Name: fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fuente (
    codigo character varying(32) NOT NULL,
    nombre character varying(128) NOT NULL,
    descripcion character varying(512) NOT NULL,
    confianza_base character varying(16) NOT NULL,
    deriva_de character varying(32),
    automatica boolean NOT NULL,
    url character varying(255),
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: fuentes_de_precios; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.fuentes_de_precios AS
 SELECT codigo,
    nombre,
    descripcion,
    confianza_base AS cuanto_se_le_cree,
    deriva_de AS copia_a,
    automatica AS la_trae_el_recolector,
    url AS direccion,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.fuente;


--
-- Name: inventario_puesto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventario_puesto (
    id integer NOT NULL,
    id_puesto integer NOT NULL,
    codigo_producto character varying(64) NOT NULL,
    monto double precision NOT NULL,
    presentacion character varying(16) NOT NULL,
    disponibilidad character varying(12) NOT NULL,
    actualizado_en timestamp with time zone NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL,
    cantidad double precision,
    minimo double precision
);


--
-- Name: inventario; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.inventario AS
 SELECT id AS numero,
    id_puesto AS puesto,
    codigo_producto AS producto,
    monto,
    presentacion AS por,
    disponibilidad AS le_queda,
    actualizado_en AS actualizado_el,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.inventario_puesto;


--
-- Name: lista_compras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lista_compras (
    id integer NOT NULL,
    id_usuario integer NOT NULL,
    nombre character varying(120) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: listas; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.listas AS
 SELECT id AS numero,
    id_usuario AS cuenta,
    nombre,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.lista_compras;


--
-- Name: intento_fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intento_fuente (
    id integer NOT NULL,
    fuente character varying(64) NOT NULL,
    url character varying(512),
    exito integer NOT NULL,
    duracion_ms integer,
    detalle character varying(512),
    ocurrido_en timestamp with time zone NOT NULL,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL
);


--
-- Name: llamadas_al_siip; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.llamadas_al_siip AS
 SELECT id AS numero,
    fuente,
    url AS direccion,
    (exito = 1) AS respondio,
    duracion_ms AS tardo_milisegundos,
    detalle AS error,
    ocurrido_en AS cuando,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.intento_fuente;


--
-- Name: mercado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mercado (
    codigo character varying(64) NOT NULL,
    nombre character varying(255) NOT NULL,
    tipo character varying(32) NOT NULL,
    zona character varying(128) NOT NULL,
    latitud double precision,
    longitud double precision,
    factor_mercado double precision NOT NULL,
    macrodistrito character varying(64) DEFAULT ''::character varying NOT NULL,
    codigo_padre character varying(64),
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL
);


--
-- Name: lugares_de_venta; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.lugares_de_venta AS
 SELECT codigo,
    nombre,
    tipo,
    zona,
    macrodistrito,
    latitud,
    longitud,
    factor_mercado AS ajuste_de_precio,
    codigo_padre AS es_sector_de,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.mercado;


--
-- Name: oferta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oferta (
    id integer NOT NULL,
    id_vendedor integer NOT NULL,
    codigo_mercado character varying(64) NOT NULL,
    numero_puesto character varying(16),
    codigo_producto character varying(64) NOT NULL,
    monto double precision NOT NULL,
    presentacion character varying(16) NOT NULL,
    precio_por_unidad_base double precision NOT NULL,
    desde timestamp with time zone NOT NULL,
    hasta timestamp with time zone NOT NULL,
    nota character varying(80) NOT NULL,
    estado character varying(16) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL,
    combo character varying(40)
);


--
-- Name: ofertas; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.ofertas AS
 SELECT id AS numero,
    id_vendedor AS casera,
    codigo_mercado AS lugar,
    numero_puesto AS puesto,
    codigo_producto AS producto,
    monto,
    presentacion AS por,
    precio_por_unidad_base,
    combo,
    nota,
    estado,
    desde,
    hasta,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.oferta;


--
-- Name: confirmacion_oferta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.confirmacion_oferta (
    id integer NOT NULL,
    id_oferta integer NOT NULL,
    id_usuario integer NOT NULL,
    la_vio_asi boolean NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: opiniones_de_ofertas; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.opiniones_de_ofertas AS
 SELECT id AS numero,
    id_oferta AS oferta,
    id_usuario AS cuenta,
    la_vio_asi,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.confirmacion_oferta;


--
-- Name: permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permiso (
    codigo character varying(32) NOT NULL,
    descripcion character varying(255) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: permisos; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.permisos AS
 SELECT codigo,
    descripcion,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.permiso;


--
-- Name: rol_permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_permiso (
    codigo_rol character varying(16) NOT NULL,
    codigo_permiso character varying(32) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: permisos_de_cada_rol; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.permisos_de_cada_rol AS
 SELECT codigo_rol AS rol,
    codigo_permiso AS permiso,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.rol_permiso;


--
-- Name: observacion_precio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.observacion_precio (
    id integer NOT NULL,
    fuente character varying(32) NOT NULL,
    nivel character varying(16) NOT NULL,
    codigo_producto character varying(64) NOT NULL,
    codigo_mercado character varying(64),
    anio integer NOT NULL,
    mes integer,
    dia integer,
    precio_monto double precision NOT NULL,
    unidad_texto character varying(64) NOT NULL,
    precio_canonico double precision,
    unidad_canonica character varying(8),
    reputacion_informante double precision NOT NULL,
    capturada_en timestamp with time zone NOT NULL,
    ambito character varying(16) DEFAULT 'punto_venta'::character varying NOT NULL,
    cantidad double precision DEFAULT 1.0 NOT NULL,
    variedad character varying(64) DEFAULT 'desconocida'::character varying NOT NULL,
    fecha_observacion date,
    tipo_precio character varying(16) DEFAULT 'desconocido'::character varying NOT NULL,
    evidencia character varying(512),
    ultima_captura_en timestamp with time zone,
    revisa_a integer,
    ciudad character varying(64),
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL,
    informante character varying(64),
    puesto character varying(16)
);


--
-- Name: precios; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.precios AS
 SELECT id AS numero,
    codigo_producto AS producto,
    codigo_mercado AS lugar,
    ciudad,
    puesto,
    fuente,
    nivel,
    precio_monto AS monto,
    unidad_texto AS unidad,
    cantidad,
    precio_canonico AS precio_por_unidad_base,
    unidad_canonica AS unidad_base,
    fecha_observacion AS fecha_del_precio,
    anio,
    mes,
    dia,
    variedad,
    tipo_precio,
    informante AS quien_lo_dijo,
    reputacion_informante AS cuanto_se_le_cree,
    evidencia AS de_donde_salio,
    ambito,
    capturada_en AS visto_el,
    ultima_captura_en AS visto_por_ultima_vez,
    revisa_a AS corrige_al_numero,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.observacion_precio;


--
-- Name: reporte_precio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reporte_precio (
    id integer NOT NULL,
    codigo_producto character varying(64) NOT NULL,
    codigo_mercado character varying(64) NOT NULL,
    monto double precision NOT NULL,
    unidad character varying(64) NOT NULL,
    id_autor integer NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    estado character varying(16) NOT NULL,
    id_revisor integer,
    revisado_en timestamp with time zone,
    motivo_rechazo character varying(512),
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL
);


--
-- Name: precios_reportados; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.precios_reportados AS
 SELECT id AS numero,
    codigo_producto AS producto,
    codigo_mercado AS lugar,
    monto,
    unidad,
    id_autor AS lo_reporto,
    estado,
    id_revisor AS lo_reviso,
    revisado_en AS revisado_el,
    motivo_rechazo AS por_que_se_rechazo,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.reporte_precio;


--
-- Name: producto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.producto (
    codigo character varying(64) NOT NULL,
    nombre character varying(255) NOT NULL,
    categoria character varying(32) NOT NULL,
    dias_conservacion integer NOT NULL,
    zona_origen character varying(128),
    unidad_base character varying(8) DEFAULT 'kg'::character varying NOT NULL,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL,
    presentaciones character varying(128)
);


--
-- Name: productos; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.productos AS
 SELECT codigo,
    nombre,
    categoria,
    unidad_base,
    presentaciones AS se_vende_por,
    dias_conservacion AS dias_que_dura,
    zona_origen AS de_donde_viene,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.producto;


--
-- Name: item_lista_compras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_lista_compras (
    id integer NOT NULL,
    id_lista integer NOT NULL,
    codigo_producto character varying(64) NOT NULL,
    cantidad double precision NOT NULL,
    presentacion character varying(16) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: productos_de_cada_lista; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.productos_de_cada_lista AS
 SELECT id AS numero,
    id_lista AS lista,
    codigo_producto AS producto,
    cantidad,
    presentacion AS por,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.item_lista_compras;


--
-- Name: puesto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.puesto (
    id integer NOT NULL,
    codigo_mercado character varying(64) NOT NULL,
    numero character varying(16) NOT NULL,
    nombre character varying(80) NOT NULL,
    rubros character varying(128) NOT NULL,
    referencia character varying(160) NOT NULL,
    id_vendedor integer,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL,
    foto character varying(80),
    celular character varying(16)
);


--
-- Name: puestos; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.puestos AS
 SELECT id AS numero_interno,
    codigo_mercado AS lugar,
    numero AS numero_de_puesto,
    nombre,
    rubros AS que_vende,
    referencia AS como_encontrarlo,
    celular AS telefono_de_contacto,
    foto,
    id_vendedor AS duena,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.puesto;


--
-- Name: corrida_fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.corrida_fuente (
    id integer NOT NULL,
    fuente character varying(64) NOT NULL,
    codigo_producto character varying(64) NOT NULL,
    hechos_vistos integer NOT NULL,
    hechos_nuevos integer NOT NULL,
    ocurrido_en timestamp with time zone NOT NULL,
    creado_en timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creado_por character varying(255) DEFAULT 'sistema'::character varying NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean DEFAULT false NOT NULL
);


--
-- Name: recolecciones; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.recolecciones AS
 SELECT id AS numero,
    fuente,
    codigo_producto AS producto,
    hechos_vistos AS precios_vistos,
    hechos_nuevos AS precios_nuevos,
    ocurrido_en AS cuando,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.corrida_fuente;


--
-- Name: rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol (
    codigo character varying(16) NOT NULL,
    nombre character varying(64) NOT NULL,
    descripcion character varying(255) NOT NULL,
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: roles; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.roles AS
 SELECT codigo,
    nombre,
    descripcion,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.rol;


--
-- Name: vendedor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vendedor (
    id_usuario integer NOT NULL,
    codigo_punto_venta character varying(64),
    creado_en timestamp with time zone NOT NULL,
    creado_por character varying(255) NOT NULL,
    modificado_en timestamp with time zone,
    modificado_por character varying(255),
    eliminado boolean NOT NULL
);


--
-- Name: vendedores; Type: VIEW; Schema: consultas; Owner: -
--

CREATE VIEW consultas.vendedores AS
 SELECT id_usuario AS cuenta,
    codigo_punto_venta AS lugar,
    creado_en AS creado_el,
    creado_por,
    modificado_en AS cambiado_el,
    modificado_por AS cambiado_por,
    eliminado AS dado_de_baja
   FROM public.vendedor;


--
-- Name: confirmacion_oferta_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.confirmacion_oferta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: confirmacion_oferta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.confirmacion_oferta_id_seq OWNED BY public.confirmacion_oferta.id;


--
-- Name: corrida_fuente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.corrida_fuente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: corrida_fuente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.corrida_fuente_id_seq OWNED BY public.corrida_fuente.id;


--
-- Name: intento_fuente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intento_fuente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intento_fuente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intento_fuente_id_seq OWNED BY public.intento_fuente.id;


--
-- Name: inventario_puesto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventario_puesto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventario_puesto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventario_puesto_id_seq OWNED BY public.inventario_puesto.id;


--
-- Name: item_lista_compras_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_lista_compras_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_lista_compras_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_lista_compras_id_seq OWNED BY public.item_lista_compras.id;


--
-- Name: lista_compras_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lista_compras_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lista_compras_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lista_compras_id_seq OWNED BY public.lista_compras.id;


--
-- Name: observacion_precio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.observacion_precio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: observacion_precio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.observacion_precio_id_seq OWNED BY public.observacion_precio.id;


--
-- Name: oferta_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.oferta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oferta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.oferta_id_seq OWNED BY public.oferta.id;


--
-- Name: puesto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.puesto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: puesto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.puesto_id_seq OWNED BY public.puesto.id;


--
-- Name: reporte_precio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reporte_precio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reporte_precio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reporte_precio_id_seq OWNED BY public.reporte_precio.id;


--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: confirmacion_oferta id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.confirmacion_oferta ALTER COLUMN id SET DEFAULT nextval('public.confirmacion_oferta_id_seq'::regclass);


--
-- Name: corrida_fuente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrida_fuente ALTER COLUMN id SET DEFAULT nextval('public.corrida_fuente_id_seq'::regclass);


--
-- Name: intento_fuente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intento_fuente ALTER COLUMN id SET DEFAULT nextval('public.intento_fuente_id_seq'::regclass);


--
-- Name: inventario_puesto id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventario_puesto ALTER COLUMN id SET DEFAULT nextval('public.inventario_puesto_id_seq'::regclass);


--
-- Name: item_lista_compras id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_lista_compras ALTER COLUMN id SET DEFAULT nextval('public.item_lista_compras_id_seq'::regclass);


--
-- Name: lista_compras id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lista_compras ALTER COLUMN id SET DEFAULT nextval('public.lista_compras_id_seq'::regclass);


--
-- Name: observacion_precio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observacion_precio ALTER COLUMN id SET DEFAULT nextval('public.observacion_precio_id_seq'::regclass);


--
-- Name: oferta id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oferta ALTER COLUMN id SET DEFAULT nextval('public.oferta_id_seq'::regclass);


--
-- Name: puesto id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.puesto ALTER COLUMN id SET DEFAULT nextval('public.puesto_id_seq'::regclass);


--
-- Name: reporte_precio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reporte_precio ALTER COLUMN id SET DEFAULT nextval('public.reporte_precio_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Name: confirmacion_oferta confirmacion_oferta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.confirmacion_oferta
    ADD CONSTRAINT confirmacion_oferta_pkey PRIMARY KEY (id);


--
-- Name: corrida_fuente corrida_fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrida_fuente
    ADD CONSTRAINT corrida_fuente_pkey PRIMARY KEY (id);


--
-- Name: fuente fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fuente
    ADD CONSTRAINT fuente_pkey PRIMARY KEY (codigo);


--
-- Name: intento_fuente intento_fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intento_fuente
    ADD CONSTRAINT intento_fuente_pkey PRIMARY KEY (id);


--
-- Name: inventario_puesto inventario_puesto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventario_puesto
    ADD CONSTRAINT inventario_puesto_pkey PRIMARY KEY (id);


--
-- Name: item_lista_compras item_lista_compras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_lista_compras
    ADD CONSTRAINT item_lista_compras_pkey PRIMARY KEY (id);


--
-- Name: lista_compras lista_compras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lista_compras
    ADD CONSTRAINT lista_compras_pkey PRIMARY KEY (id);


--
-- Name: mercado mercado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mercado
    ADD CONSTRAINT mercado_pkey PRIMARY KEY (codigo);


--
-- Name: observacion_precio observacion_precio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observacion_precio
    ADD CONSTRAINT observacion_precio_pkey PRIMARY KEY (id);


--
-- Name: oferta oferta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oferta
    ADD CONSTRAINT oferta_pkey PRIMARY KEY (id);


--
-- Name: permiso permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_pkey PRIMARY KEY (codigo);


--
-- Name: producto producto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto
    ADD CONSTRAINT producto_pkey PRIMARY KEY (codigo);


--
-- Name: puesto puesto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.puesto
    ADD CONSTRAINT puesto_pkey PRIMARY KEY (id);


--
-- Name: reporte_precio reporte_precio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reporte_precio
    ADD CONSTRAINT reporte_precio_pkey PRIMARY KEY (id);


--
-- Name: rol_permiso rol_permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_pkey PRIMARY KEY (codigo_rol, codigo_permiso);


--
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (codigo);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: vendedor vendedor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vendedor
    ADD CONSTRAINT vendedor_pkey PRIMARY KEY (id_usuario);


--
-- Name: ix_confirmacion_oferta; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_confirmacion_oferta ON public.confirmacion_oferta USING btree (id_oferta, id_usuario);


--
-- Name: ix_corrida_fuente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_corrida_fuente ON public.corrida_fuente USING btree (fuente, ocurrido_en);


--
-- Name: ix_intento_fuente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_intento_fuente ON public.intento_fuente USING btree (fuente, ocurrido_en);


--
-- Name: ix_inventario_puesto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inventario_puesto ON public.inventario_puesto USING btree (id_puesto);


--
-- Name: ix_item_lista; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_lista ON public.item_lista_compras USING btree (id_lista);


--
-- Name: ix_lista_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lista_usuario ON public.lista_compras USING btree (id_usuario);


--
-- Name: ix_obs_consulta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_obs_consulta ON public.observacion_precio USING btree (codigo_producto, codigo_mercado, anio, mes);


--
-- Name: ix_obs_nivel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_obs_nivel ON public.observacion_precio USING btree (nivel, anio, mes);


--
-- Name: ix_observacion_precio_informante; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_observacion_precio_informante ON public.observacion_precio USING btree (informante);


--
-- Name: ix_oferta_vendedor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_oferta_vendedor ON public.oferta USING btree (id_vendedor);


--
-- Name: ix_oferta_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_oferta_vigencia ON public.oferta USING btree (estado, hasta);


--
-- Name: ix_puesto_mercado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_puesto_mercado ON public.puesto USING btree (codigo_mercado);


--
-- Name: ix_reporte_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reporte_estado ON public.reporte_precio USING btree (estado, creado_en);


--
-- Name: uq_hecho_observado_v2; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_hecho_observado_v2 ON public.observacion_precio USING btree (fuente, nivel, codigo_producto, ambito, COALESCE(codigo_mercado, ''::character varying), COALESCE(ciudad, ''::character varying), anio, COALESCE(mes, 0), COALESCE(dia, 0), unidad_texto, cantidad, COALESCE(informante, ''::character varying), COALESCE(puesto, ''::character varying), precio_monto);


--
-- Name: uq_inventario_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_inventario_vigente ON public.inventario_puesto USING btree (id_puesto, codigo_producto) WHERE (NOT eliminado);


--
-- Name: uq_puesto_numero_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_puesto_numero_vigente ON public.puesto USING btree (codigo_mercado, numero) WHERE (NOT eliminado);


--
-- Name: uq_puesto_vendedor_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_puesto_vendedor_vigente ON public.puesto USING btree (id_vendedor) WHERE ((NOT eliminado) AND (id_vendedor IS NOT NULL));


--
-- Name: uq_usuario_correo_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_usuario_correo_vigente ON public.usuario USING btree (correo) WHERE (NOT eliminado);


--
-- Name: confirmacion_oferta confirmacion_oferta_id_oferta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.confirmacion_oferta
    ADD CONSTRAINT confirmacion_oferta_id_oferta_fkey FOREIGN KEY (id_oferta) REFERENCES public.oferta(id);


--
-- Name: confirmacion_oferta confirmacion_oferta_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.confirmacion_oferta
    ADD CONSTRAINT confirmacion_oferta_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id);


--
-- Name: observacion_precio fk_observacion_fuente; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observacion_precio
    ADD CONSTRAINT fk_observacion_fuente FOREIGN KEY (fuente) REFERENCES public.fuente(codigo);


--
-- Name: usuario fk_usuario_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT fk_usuario_rol FOREIGN KEY (rol) REFERENCES public.rol(codigo);


--
-- Name: fuente fuente_deriva_de_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fuente
    ADD CONSTRAINT fuente_deriva_de_fkey FOREIGN KEY (deriva_de) REFERENCES public.fuente(codigo);


--
-- Name: inventario_puesto inventario_puesto_codigo_producto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventario_puesto
    ADD CONSTRAINT inventario_puesto_codigo_producto_fkey FOREIGN KEY (codigo_producto) REFERENCES public.producto(codigo);


--
-- Name: inventario_puesto inventario_puesto_id_puesto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventario_puesto
    ADD CONSTRAINT inventario_puesto_id_puesto_fkey FOREIGN KEY (id_puesto) REFERENCES public.puesto(id);


--
-- Name: item_lista_compras item_lista_compras_id_lista_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_lista_compras
    ADD CONSTRAINT item_lista_compras_id_lista_fkey FOREIGN KEY (id_lista) REFERENCES public.lista_compras(id);


--
-- Name: lista_compras lista_compras_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lista_compras
    ADD CONSTRAINT lista_compras_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id);


--
-- Name: mercado mercado_codigo_padre_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mercado
    ADD CONSTRAINT mercado_codigo_padre_fkey FOREIGN KEY (codigo_padre) REFERENCES public.mercado(codigo);


--
-- Name: observacion_precio observacion_precio_revisa_a_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observacion_precio
    ADD CONSTRAINT observacion_precio_revisa_a_fkey FOREIGN KEY (revisa_a) REFERENCES public.observacion_precio(id);


--
-- Name: oferta oferta_codigo_mercado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oferta
    ADD CONSTRAINT oferta_codigo_mercado_fkey FOREIGN KEY (codigo_mercado) REFERENCES public.mercado(codigo);


--
-- Name: oferta oferta_codigo_producto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oferta
    ADD CONSTRAINT oferta_codigo_producto_fkey FOREIGN KEY (codigo_producto) REFERENCES public.producto(codigo);


--
-- Name: oferta oferta_id_vendedor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oferta
    ADD CONSTRAINT oferta_id_vendedor_fkey FOREIGN KEY (id_vendedor) REFERENCES public.usuario(id);


--
-- Name: puesto puesto_codigo_mercado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.puesto
    ADD CONSTRAINT puesto_codigo_mercado_fkey FOREIGN KEY (codigo_mercado) REFERENCES public.mercado(codigo);


--
-- Name: puesto puesto_id_vendedor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.puesto
    ADD CONSTRAINT puesto_id_vendedor_fkey FOREIGN KEY (id_vendedor) REFERENCES public.usuario(id);


--
-- Name: reporte_precio reporte_precio_id_autor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reporte_precio
    ADD CONSTRAINT reporte_precio_id_autor_fkey FOREIGN KEY (id_autor) REFERENCES public.usuario(id);


--
-- Name: reporte_precio reporte_precio_id_revisor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reporte_precio
    ADD CONSTRAINT reporte_precio_id_revisor_fkey FOREIGN KEY (id_revisor) REFERENCES public.usuario(id);


--
-- Name: rol_permiso rol_permiso_codigo_permiso_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_codigo_permiso_fkey FOREIGN KEY (codigo_permiso) REFERENCES public.permiso(codigo);


--
-- Name: rol_permiso rol_permiso_codigo_rol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_codigo_rol_fkey FOREIGN KEY (codigo_rol) REFERENCES public.rol(codigo);


--
-- Name: vendedor vendedor_codigo_punto_venta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vendedor
    ADD CONSTRAINT vendedor_codigo_punto_venta_fkey FOREIGN KEY (codigo_punto_venta) REFERENCES public.mercado(codigo);


--
-- Name: vendedor vendedor_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vendedor
    ADD CONSTRAINT vendedor_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id);


--
-- PostgreSQL database dump complete
--


