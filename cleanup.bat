@echo off
REM Script de nettoyage pour Windows

echo Nettoyage des fichiers inutiles...

REM Supprimer __pycache__
echo Suppression des __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Supprimer .pyc
echo Suppression des fichiers .pyc...
del /s /q *.pyc 2>nul

REM Supprimer .pytest_cache
echo Suppression des .pytest_cache...
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"

REM Supprimer node_modules
if exist "node_modules" (
    echo Suppression de node_modules...
    rd /s /q "node_modules"
)

REM Supprimer fichiers nul
echo Suppression des fichiers nul...
del /s /q nul 2>nul

REM Supprimer fichiers temporaires
echo Suppression des fichiers temporaires...
del /s /q *.tmp 2>nul
del /s /q *.bak 2>nul

REM Supprimer fichiers de test
echo Suppression des fichiers de test...
del /s /q test_*.json 2>nul
del /s /q test_*.csv 2>nul

echo.
echo Nettoyage termine!
pause
