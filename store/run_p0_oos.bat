@echo off
cd /d d:\Projects\Telegram-bot-for-investment-signal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONWARNINGS=ignore
set PYTHONFAULTHANDLER=1
set PYTHONUNBUFFERED=1
echo START %DATE% %TIME%> store\backtest_final_vn100_20260923_p0fix.run.log
python -u -X utf8 -X faulthandler scripts\run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward --out-json store\backtest_final_vn100_20260923_p0fix.json >> store\backtest_final_vn100_20260923_p0fix.run.log 2>&1
echo EXIT_CODE=%ERRORLEVEL%>> store\backtest_final_vn100_20260923_p0fix.run.log
echo END %DATE% %TIME%>> store\backtest_final_vn100_20260923_p0fix.run.log
