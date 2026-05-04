@echo off
chcp 65001 >nul
title Pipeline Valuation Bancário

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   PIPELINE DE VALUATION BANCÁRIO — Atualização  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM Vai para a pasta do script
cd /d "%~dp0"

REM Verifica se Python está disponível
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python não encontrado. Instale Python 3.10+ e adicione ao PATH.
    pause
    exit /b 1
)

REM Instala dependências se necessário
if not exist ".deps_ok" (
    echo  Instalando dependências...
    pip install -r requirements.txt -q
    echo. > .deps_ok
)

REM Argumentos opcionais (ex: --sem-cache ou --ticker BBDC4 ITUB4)
set ARGS=%*

if "%ARGS%"=="" (
    echo  Processando todos os bancos: BBDC4, BBAS3, ITUB4, SANB11, BPAC11
    echo.
    python main.py --batch BBDC4 BBAS3 ITUB4 SANB11 BPAC11
) else (
    python main.py %ARGS%
)

echo.
if errorlevel 1 (
    echo  [ERRO] Pipeline finalizou com erros. Verifique logs\
) else (
    echo  [OK] Planilhas atualizadas em outputs\
)

echo.
pause
