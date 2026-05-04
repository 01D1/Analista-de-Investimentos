@echo off
chcp 65001 >nul
title Registrar Agendamento Windows

cd /d "%~dp0"

echo.
echo  Registrando pipeline no Agendador de Tarefas do Windows...
echo  Execuções: seg-sex às 07:30 e 18:00
echo.

REM Descobre caminho do Python
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set PYTHON=%%i

REM Caminho do scheduler
set SCHEDULER=%~dp0scheduler.py

REM Tarefa manhã (07:30)
schtasks /create /tn "ValuationBancario_Manha" ^
  /tr "\"%PYTHON%\" \"%SCHEDULER%\" --agora" ^
  /sc WEEKLY /d MON,TUE,WED,THU,FRI ^
  /st 07:30 ^
  /ru "%USERNAME%" ^
  /f

if errorlevel 1 (
    echo  [ERRO] Falha ao criar tarefa da manhã.
) else (
    echo  [OK] Tarefa "ValuationBancario_Manha" criada — seg-sex 07:30
)

REM Tarefa tarde (18:00)
schtasks /create /tn "ValuationBancario_Tarde" ^
  /tr "\"%PYTHON%\" \"%SCHEDULER%\" --agora" ^
  /sc WEEKLY /d MON,TUE,WED,THU,FRI ^
  /st 18:00 ^
  /ru "%USERNAME%" ^
  /f

if errorlevel 1 (
    echo  [ERRO] Falha ao criar tarefa da tarde.
) else (
    echo  [OK] Tarefa "ValuationBancario_Tarde" criada — seg-sex 18:00
)

echo.
echo  Para verificar: Agendador de Tarefas ^> Biblioteca ^> ValuationBancario_*
echo  Para remover:   schtasks /delete /tn "ValuationBancario_Manha" /f
echo.
pause
