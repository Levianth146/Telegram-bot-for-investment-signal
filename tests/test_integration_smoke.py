"""Integration smoke test — đảm bảo pipeline chạy được end-to-end (dù là stub)
theo đúng mốc tuần 2 (mục 11.5 tài liệu framework). Không test logic chi tiết,
chỉ test rằng các module import được và ghép nối đúng.
"""


def test_can_import_all_modules():
    import fundamental_filter.growth  # noqa: F401
    import fundamental_filter.quality  # noqa: F401
    import fundamental_filter.safety  # noqa: F401
    import fundamental_filter.valuation  # noqa: F401
    import fundamental_filter.scoring  # noqa: F401
    import quant_engine.regime  # noqa: F401
    import quant_engine.alpha.kalman_trend  # noqa: F401
    import quant_engine.alpha.ou_meanrev  # noqa: F401
    import quant_engine.risk.garch  # noqa: F401
    import quant_engine.portfolio.black_litterman  # noqa: F401
    import quant_engine.probabilistic.monte_carlo  # noqa: F401
    import quant_engine.probabilistic.hawkes  # noqa: F401
    import store.repository  # noqa: F401
    import backtest.engine  # noqa: F401
    import bot.formatters  # noqa: F401
