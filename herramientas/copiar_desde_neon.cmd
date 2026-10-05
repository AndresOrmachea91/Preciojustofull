@echo off
rem Copia la base de Neon al contenedor "db". Ver herramientas\copiar_desde_neon.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0copiar_desde_neon.ps1"
