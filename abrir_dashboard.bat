@echo off
title Reto Apuestas Dashboard
echo =======================================================
echo 🏆 RETO APUESTAS - INICIANDO DASHBOARD WEB
echo =======================================================

:: Intentar liberar el puerto 8000 si está ocupado por una instancia previa
echo 🔍 Verificando puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr 8000') do (
    echo 🧹 Liberando puerto ocupado (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

:: Iniciar el servidor web de Python en segundo plano
echo 📡 Iniciando servidor HTTP local de Python en segundo plano...
start /B python src/services/web_server.py >nul 2>&1

:: Esperar 1 segundo para asegurar el arranque del servidor
timeout /t 1 /nobreak >nul

:: Abrir el dashboard en el navegador web por defecto
echo 🌐 Abriendo el navegador en http://localhost:8000/dashboard/index.html ...
start http://localhost:8000/dashboard/index.html

echo.
echo ✅ ¡Listo! El servidor web está corriendo en segundo plano.
echo Puedes cerrar esta ventana sin problemas.
timeout /t 3 >nul
exit
