"""Capa de infraestructura: el borde del sistema.

Aquí viven los adaptadores que implementan los puertos declarados en
`aplicacion.puertos`. Es la única capa que puede importar frameworks
(FastAPI, SQLAlchemy, requests). Nada de dominio ni de aplicación
importa desde aquí.
"""
