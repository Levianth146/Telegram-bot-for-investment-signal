@echo off
setlocal
cd /d D:\Projects\Telegram-bot-for-investment-signal
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONWARNINGS=ignore
set PYTHONUNBUFFERED=1
set PYTHONFAULTHANDLER=1
echo %DATE% %TIME% START > store\backtest_final_vn100_20260923_p22_watchlist.exit
echo %DATE% %TIME% START > store\backtest_final_vn100_20260923_p22_watchlist.run.log
python -u -X utf8 -X faulthandler scripts\run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward --out-json store\backtest_final_vn100_20260923_p22_watchlist.json >> store\backtest_final_vn100_20260923_p22_watchlist.run.log 2> store\backtest_final_vn100_20260923_p22_watchlist.err.log
echo EXIT=%ERRORLEVEL% FINISH=%DATE% %TIME% > store\backtest_final_vn100_20260923_p22_watchlist.exit
endlocal
