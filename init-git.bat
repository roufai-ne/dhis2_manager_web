@echo off
REM Script d'initialisation Git pour Windows

echo Initialisation du repository Git...

REM Verifier si Git est installe
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git n'est pas installe. Installez-le d'abord.
    echo Telechargez depuis: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Verifier si .git existe deja
if exist ".git" (
    echo Repository Git existe deja!
    set /p "answer=Voulez-vous reinitialiser? (y/N) "
    if /i "%answer%"=="y" (
        rmdir /s /q .git
        echo Repository supprime
    ) else (
        echo Annule
        pause
        exit /b 0
    )
)

REM Initialiser Git
git init
echo Repository Git initialise

REM Creer les repertoires avec .gitkeep
if not exist "logs" mkdir logs
if not exist "sessions" mkdir sessions
if not exist "uploads" mkdir uploads
echo. > logs\.gitkeep
echo. > sessions\.gitkeep
echo. > uploads\.gitkeep

REM Ajouter tous les fichiers
echo Ajout des fichiers...
git add .

REM Premier commit
echo Premier commit...
git commit -m "Initial commit - DHIS2 Manager v5.0" -m "- Application web Flask pour gestion DHIS2" -m "- Mode Template: Generation templates Excel" -m "- Mode Automatique: Traitement TCD avec mapping intelligent" -m "- Configuration Docker complete" -m "- Documentation exhaustive" -m "- Pret pour deploiement production"

echo.
echo Repository Git initialise avec succes!
echo.
echo Prochaines etapes:
echo 1. Creer un repository sur GitHub/GitLab
echo 2. Ajouter le remote:
echo    git remote add origin ^<URL_REPOSITORY^>
echo 3. Pousser le code:
echo    git push -u origin main
echo.
echo Statistiques:
git log --oneline
echo.
git status

pause
