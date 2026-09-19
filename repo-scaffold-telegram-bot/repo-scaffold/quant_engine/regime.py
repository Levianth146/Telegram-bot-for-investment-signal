"""Regime — Markov switching trên VN-Index.

Tham chiếu: Mục 8 lớp 1 / mục 9 của tài liệu framework.
Câu hỏi trả lời: "Thị trường hôm nay đang ở trạng thái nào — bull/bear/turbulent?"

QUAN TRỌNG: backtest và live PHẢI dùng filtered probability, KHÔNG dùng
smoothed probability (smoothed dùng thông tin tương lai -> look-ahead bias).
Xem mục 12 (sai lầm cần tránh, 12.2, dòng đầu tiên).
"""

from __future__ import annotations


def fit_markov_regime(index_returns, n_states: int = 3):
    """Fit Hidden Markov Model trên lợi nhuận VN-Index. Trả về model đã fit.

    n_states=3 tương ứng {bull, bear, turbulent}.
    """
    raise NotImplementedError


def filtered_regime_probability(model, returns_up_to_t) -> dict:
    """Trả về P(state=k | F_t) CHỈ dùng dữ liệu tới thời điểm t (filtered, không smoothed)."""
    raise NotImplementedError
