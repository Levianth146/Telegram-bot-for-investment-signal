@echo off
set PYTHONUTF8=1
cd /d d:\Projects\Telegram-bot-for-investment-signal
echo START %DATE% %TIME% >> "d:\Projects\Telegram-bot-for-investment-signal\store\backtest_final_vn100_20260924_b2fix.run.log"
python scripts/run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward --out-json store/backtest_final_vn100_20260924_b2fix.json >> "d:\Projects\Telegram-bot-for-investment-signal\store\backtest_final_vn100_20260924_b2fix.run.log" 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> "d:\Projects\Telegram-bot-for-investment-signal\store\backtest_final_vn100_20260924_b2fix.run.log"
echo END %DATE% %TIME% >> "d:\Projects\Telegram-bot-for-investment-signal\store\backtest_final_vn100_20260924_b2fix.run.log"
