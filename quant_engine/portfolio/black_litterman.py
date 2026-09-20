"""Black-Litterman — P1 + equal-weight fallback (P0).

Khi ``portfolio_black_litterman.enabled = false``, dùng
``equal_weight_fallback`` (ARCHITECTURE invariant #4).

Formula (framework mục 9.4, Idzorek / BL standard):
  π = δ Σ w_mkt
  μ = [(τΣ)^{-1} + P' Ω^{-1} P]^{-1} [(τΣ)^{-1} π + P' Ω^{-1} Q]
  w ∝ Σ^{-1} μ  (long-only renormalize)
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def equal_weight_fallback(tickers: list[str]) -> dict[str, float]:
    """Fallback khi portfolio_black_litterman.enabled = false (mục 11.1)."""
    cleaned = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if not cleaned:
        return {}
    weight = 1.0 / len(cleaned)
    return {ticker: weight for ticker in cleaned}


def build_views(
    alpha_signals: Mapping[str, float],
    valuation_signals: Mapping[str, float] | None = None,
    *,
    alpha_scale: float = 0.02,
    valuation_scale: float = 0.01,
    min_omega: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Ghép view Absolute Alpha + Valuation → P, Q, Omega (mục 9.4).

    Returns
    -------
    P, Q, Omega, tickers
        Absolute views (P = I). Q in excess-return units. Omega diagonal.
    """
    valuation_signals = valuation_signals or {}
    tickers = sorted(
        {
            str(t).strip().upper()
            for t in list(alpha_signals) + list(valuation_signals)
            if str(t).strip()
        }
    )
    if not tickers:
        raise ValueError("build_views requires at least one ticker")

    n = len(tickers)
    p_mat = np.eye(n)
    q = np.zeros(n)
    omega_diag = np.zeros(n)
    for i, ticker in enumerate(tickers):
        alpha = alpha_signals.get(ticker)
        val = valuation_signals.get(ticker)
        alpha_term = 0.0
        if alpha is not None and not pd.isna(alpha):
            alpha_term = float(np.tanh(float(alpha))) * alpha_scale
        val_term = 0.0
        if val is not None and not pd.isna(val):
            val_term = (float(val) - 50.0) / 50.0 * valuation_scale
        q[i] = alpha_term + val_term
        # Weaker |signal| → higher view uncertainty
        strength = abs(alpha_term) + abs(val_term)
        omega_diag[i] = max(min_omega, (alpha_scale**2) / (1.0 + 10.0 * strength))

    omega = np.diag(omega_diag)
    return p_mat, q, omega, tickers


def _market_weights(market_caps: Mapping[str, float], tickers: list[str]) -> np.ndarray:
    caps = np.array(
        [max(float(market_caps.get(t, 1.0) or 1.0), 1e-12) for t in tickers],
        dtype=float,
    )
    return caps / caps.sum()


def black_litterman_weights(
    market_caps: Mapping[str, float],
    cov_matrix: np.ndarray | pd.DataFrame,
    P: np.ndarray,
    Q: np.ndarray,
    Omega: np.ndarray,
    *,
    tau: float = 0.05,
    delta: float = 2.5,
    tickers: list[str] | None = None,
) -> dict[str, float]:
    """Trả về trọng số BL (long-only). Falls back to equal-weight on singular Σ."""
    sigma = np.asarray(cov_matrix, dtype=float)
    if sigma.ndim != 2 or sigma.shape[0] != sigma.shape[1]:
        raise ValueError("cov_matrix must be square")
    n = sigma.shape[0]
    if tickers is None:
        if isinstance(cov_matrix, pd.DataFrame):
            tickers = [str(c).strip().upper() for c in cov_matrix.columns]
        else:
            tickers = [f"T{i}" for i in range(n)]
    if len(tickers) != n:
        raise ValueError("tickers length must match cov_matrix")

    w_mkt = _market_weights(market_caps, tickers)
    try:
        pi = delta * sigma @ w_mkt
        tau_sigma = tau * sigma
        inv_tau_sigma = np.linalg.pinv(tau_sigma)
        inv_omega = np.linalg.pinv(Omega)
        mid = inv_tau_sigma + P.T @ inv_omega @ P
        rhs = inv_tau_sigma @ pi + P.T @ inv_omega @ Q
        mu = np.linalg.pinv(mid) @ rhs
        raw = np.linalg.pinv(sigma) @ mu
    except np.linalg.LinAlgError:
        return equal_weight_fallback(tickers)

    long_only = np.maximum(raw, 0.0)
    total = float(long_only.sum())
    if total <= 0:
        return equal_weight_fallback(tickers)
    weights = long_only / total
    return {ticker: float(weights[i]) for i, ticker in enumerate(tickers)}


def covariance_from_closes(
    close_by_ticker: Mapping[str, pd.Series],
    tickers: list[str],
    *,
    min_obs: int = 60,
) -> pd.DataFrame:
    """Sample covariance of aligned log-returns (annualization not required for BL)."""
    frames = []
    for ticker in tickers:
        series = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        rets = np.log(series).diff().dropna()
        rets.name = ticker
        frames.append(rets)
    if not frames:
        raise ValueError("no returns for covariance")
    aligned = pd.concat(frames, axis=1, join="inner").dropna()
    if len(aligned) < min_obs:
        # Shrink toward diagonal when history is short
        vol = aligned.std().replace(0, np.nan).fillna(aligned.std().mean() or 0.01)
        return pd.DataFrame(np.diag(vol.to_numpy() ** 2), index=tickers, columns=tickers)
    return aligned.cov()


def bl_portfolio_weights(
    close_by_ticker: Mapping[str, pd.Series],
    tickers: list[str],
    alpha_signals: Mapping[str, float],
    valuation_signals: Mapping[str, float] | None = None,
    market_caps: Mapping[str, float] | None = None,
    *,
    tau: float = 0.05,
    delta: float = 2.5,
) -> dict[str, float]:
    """End-to-end BL weights with equal-weight fallback on any failure."""
    cleaned = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if not cleaned:
        return {}
    try:
        p_mat, q, omega, view_tickers = build_views(
            alpha_signals, valuation_signals
        )
        # Align views to cleaned universe order
        order = [t for t in cleaned if t in view_tickers]
        if len(order) < 2:
            return equal_weight_fallback(cleaned)
        idx = [view_tickers.index(t) for t in order]
        p_mat = p_mat[np.ix_(idx, idx)]
        q = q[idx]
        omega = omega[np.ix_(idx, idx)]
        cov = covariance_from_closes(close_by_ticker, order)
        caps = market_caps or {t: 1.0 for t in order}
        weights = black_litterman_weights(
            caps, cov, p_mat, q, omega, tau=tau, delta=delta, tickers=order
        )
        # Include any tickers missing from views at zero then renormalize
        for ticker in cleaned:
            weights.setdefault(ticker, 0.0)
        total = sum(weights.values())
        if total <= 0:
            return equal_weight_fallback(cleaned)
        return {t: weights[t] / total for t in cleaned}
    except (ValueError, np.linalg.LinAlgError, KeyError):
        return equal_weight_fallback(cleaned)
