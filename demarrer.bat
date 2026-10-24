@echo off
rem Lance Vision Board (API + interface) dans une fenêtre, puis ouvre le navigateur.
rem Pour arrêter l'application : fermez la fenêtre « Vision Board ».
cd /d "%~dp0"
start "Vision Board" cmd /k npm start
timeout /t 6 /nobreak >nul
start "" http://localhost:5173
