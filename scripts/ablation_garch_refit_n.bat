@echo off
REM Detached ablation GARCH refit_every_n (real OHLCV ngắn).
cd /d "%~dp0\.."
if not exist outputs\performance mkdir outputs\performance
set OUTLOG=outputs\performance\ablation_garch_refit_n.log
echo Starting %DATE% %TIME% > "%OUTLOG%"
python scripts/ablation_garch_refit_n.py --tickers FPT,VNM,HPG,GAS --start-date 2024-06-01 --signal-every 5 --parallel-workers 1 --out-json store/ablation_garch_refit_n.json >> "%OUTLOG%" 2>&1
echo EXIT=%ERRORLEVEL% >> "%OUTLOG%"
echo Done %DATE% %TIME% >> "%OUTLOG%"
