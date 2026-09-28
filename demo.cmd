@echo off
rem Alias historico: demo.cmd hace lo mismo que serve.cmd y ademas abre el
rem navegador. El comando recomendado es serve.cmd.
start "" http://localhost:8000
call "%~dp0serve.cmd" %*
