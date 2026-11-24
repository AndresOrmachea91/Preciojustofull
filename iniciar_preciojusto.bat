@echo off
chcp 65001 >nul
title PrecioJusto - iniciar
cd /d "%~dp0"

echo Revisando Docker...
docker info >nul 2>&1
if not errorlevel 1 goto levantar
echo Docker no esta abierto. Abriendo Docker Desktop...
start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
:esperar
ping -n 4 127.0.0.1 >nul
docker info >nul 2>&1
if errorlevel 1 goto esperar

:levantar
echo Levantando PrecioJusto...
docker compose up -d
if errorlevel 1 goto fallo

echo Esperando a que responda la pagina...
:pagina
ping -n 3 127.0.0.1 >nul
curl -s -o nul http://localhost:8088/ || goto pagina

start "" "http://localhost:8088/#/precios"
echo Listo: PrecioJusto esta en http://localhost:8088
ping -n 6 127.0.0.1 >nul
exit /b 0

:fallo
echo.
echo Algo fallo. Mire el mensaje de arriba.
pause
exit /b 1
