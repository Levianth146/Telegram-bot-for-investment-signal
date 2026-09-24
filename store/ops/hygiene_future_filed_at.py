"""Ops một lần: xoá hàng ``fundamental_scores`` có ``filed_at`` > hôm nay.

Rác thường đến từ ``quarterly_job --end-year`` vượt năm đã kết thúc
(vd. end_year=2026 → filed_at=2027-03-31 khi hôm nay vẫn 2026). Đồng bộ xoá
``watchlist`` cùng ``as_of_date`` tương lai nếu có.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Xoá fundamental_scores / watchlist có ngày > as_of (PIT hygiene)"
    )
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument(
        "--as-of",
        default="",
        help="ISO date; mặc định hôm nay. Xoá mọi filed_at / as_of_date > as_of.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực sự DELETE (mặc định dry-run)",
    )
    args = parser.parse_args()
    as_of = (args.as_of or "").strip() or date.today().isoformat()
    db = Path(args.db_path)
    conn = sqlite3.connect(str(db))
    try:
        n_fund = conn.execute(
            "SELECT COUNT(*) FROM fundamental_scores WHERE filed_at > ?",
            (as_of,),
        ).fetchone()[0]
        n_wl = conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE as_of_date > ?",
            (as_of,),
        ).fetchone()[0]
        by_filed = conn.execute(
            """
            SELECT filed_at, COUNT(*) AS n
            FROM fundamental_scores
            WHERE filed_at > ?
            GROUP BY filed_at
            ORDER BY filed_at
            """,
            (as_of,),
        ).fetchall()
        print(
            f"dry_run={not args.apply} as_of={as_of} "
            f"fund_future={n_fund} watchlist_future={n_wl} by_filed={by_filed}"
        )
        if args.apply and (n_fund or n_wl):
            conn.execute(
                "DELETE FROM fundamental_scores WHERE filed_at > ?", (as_of,)
            )
            conn.execute(
                "DELETE FROM watchlist WHERE as_of_date > ?", (as_of,)
            )
            conn.commit()
            print(f"deleted fund={n_fund} watchlist={n_wl}")
        else:
            print("no delete")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
