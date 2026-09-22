"""Hygiene: xóa as_of/filed_at look-ahead 2027-03-31 (end_year=2026 khi FY2026 chưa sẵn).

Chạy thủ công SAU khi quarterly_job end_year=2026 xong — không chạy chồng khi job đang ghi.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument(
        "--stale-asof",
        default="2027-03-31",
        help="Ngày look-ahead cần xóa (mặc định 2027-03-31)",
    )
    parser.add_argument("--apply", action="store_true", help="Thực sự DELETE (mặc định dry-run)")
    args = parser.parse_args()
    db = Path(args.db_path)
    stale = args.stale_asof
    conn = sqlite3.connect(str(db))
    try:
        n_fund = conn.execute(
            "select count(*) from fundamental_scores where filed_at=?", (stale,)
        ).fetchone()[0]
        n_wl = conn.execute(
            "select count(*) from watchlist where as_of_date=?", (stale,)
        ).fetchone()[0]
        print(
            f"dry_run={not args.apply} stale={stale} fund={n_fund} watchlist={n_wl}"
        )
        if args.apply and (n_fund or n_wl):
            conn.execute(
                "delete from fundamental_scores where filed_at=?", (stale,)
            )
            conn.execute("delete from watchlist where as_of_date=?", (stale,))
            conn.commit()
            print("deleted")
        else:
            print("no delete")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
