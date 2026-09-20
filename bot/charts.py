"""Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto).

QUAN TRỌNG — cùng ranh giới với formatters.py: các hàm ở đây CHỈ ĐỌC dữ liệu đã
tính sẵn trong store/ (hoặc backtest_results), KHÔNG được tự tính lại mô hình.
Nếu số liệu cần cho 1 chart chưa có trong DB, hàm phải raise lỗi rõ ràng thay vì
tự ước tính — tránh lặp lại sai lầm "tính hai lần một chỉ số ở hai module khác nhau".

Loại chart & lệnh tương ứng (xem docs/ARCHITECTURE.md):
    /chart <mã> price        -> giá + trend Kalman + nền tô màu theo regime
    /chart <mã> risk         -> dải biến động dự báo từ GARCH quanh giá
    /chart <mã> prob         -> histogram phân phối Monte Carlo (P đạt TP trước SL)
    /chart <mã> fundamental  -> radar 4 trục Growth/Quality/Safety/Valuation
    /chart <mã> ta           -> RSI/EMA/Volume, LUÔN gắn nhãn "Tham khảo thêm",
                                 không bao giờ là chart mặc định (mục 9.7)
    /backtest <mã|portfolio> -> equity curve so với B0/B1/B2, đọc từ backtest_results
                                 (KHÔNG chạy backtest live trong lúc trả lời Telegram)
"""

from __future__ import annotations
from pathlib import Path


def render_price_regime_chart(ticker: str, price_history: list[dict], kalman_trend: list[dict],
                               regime_history: list[dict], out_path: str | Path) -> Path:
    """Giá + đường trend Kalman + nền tô theo regime (bull/bear). Thay cho biểu đồ
    nến + MA truyền thống — xem mục 9.7 bảng ánh xạ TA -> Quant.
    """
    raise NotImplementedError


def render_garch_risk_band_chart(ticker: str, price_history: list[dict], sigma_hat_history: list[dict],
                                  out_path: str | Path) -> Path:
    """Dải biến động dự báo GARCH quanh giá — tương tự Bollinger Bands về mặt hình
    ảnh nhưng là forecast thống kê, không phải rolling std cố định.
    """
    raise NotImplementedError


def render_monte_carlo_distribution_chart(ticker: str, mc_outcomes: list[float],
                                           tp_pct: float, sl_pct: float, out_path: str | Path) -> Path:
    """Histogram phân phối kết quả mô phỏng Monte Carlo — không có tương đương TA,
    thể hiện đúng lớp Probabilistic của framework.
    """
    raise NotImplementedError


def render_fundamental_radar_chart(ticker: str, growth_score: float, quality_score: float,
                                    safety_score: float, valuation_score: float,
                                    out_path: str | Path) -> Path:
    """Radar 4 trục Growth/Quality/Safety/Valuation (z-score theo ngành, mục 10) —
    trực quan hoá Tầng 1 để dễ kể chuyện doanh nghiệp (mục 6.1)."""
    raise NotImplementedError


def render_ta_reference_chart(ticker: str, price_history: list[dict], ta_indicators: dict,
                               out_path: str | Path) -> Path:
    """RSI/EMA/Volume — CHỈ gọi khi người dùng chủ động xin (`/chart <mã> ta`), luôn
    kèm nhãn 'Tham khảo thêm, không dùng để ra tín hiệu'. Không gọi hàm này từ bất
    kỳ đường dẫn nào khác ngoài lệnh /chart tường minh của người dùng."""
    raise NotImplementedError


def render_backtest_equity_curve_chart(scope: str, run_id: str, out_path: str | Path) -> Path:
    """Đọc `equity_curve_json` của framework + 3 baseline (B0/B1/B2) từ bảng
    `backtest_results` (đã tính sẵn theo lịch định kỳ) và vẽ chung 1 biểu đồ so sánh.
    KHÔNG chạy backtest ở đây — nếu chưa có `run_id` phù hợp, báo lỗi rõ ràng
    ("chưa có kết quả backtest, chờ lần chạy định kỳ tiếp theo") thay vì tự chạy.
    """
    raise NotImplementedError
