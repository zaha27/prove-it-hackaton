"""Backtest metrics calculations."""

import numpy as np
from typing import Any


def calculate_win_rate(returns: list[float]) -> float:
    """Calculate win rate (percentage of positive returns).

    Args:
        returns: List of trade returns

    Returns:
        Win rate as float between 0 and 1
    """
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return wins / len(returns)


def calculate_profit_factor(returns: list[float]) -> float:
    """Calculate profit factor (gross profit / gross loss).

    Args:
        returns: List of trade returns

    Returns:
        Profit factor (1.0 = breakeven)
    """
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 1.0

    return gross_profit / gross_loss


def calculate_sharpe_ratio(
    returns: list[float], risk_free_rate: float = 0.0
) -> float:
    """Calculate Sharpe ratio (risk-adjusted return).

    Args:
        returns: List of trade returns
        risk_free_rate: Annual risk-free rate (default 0)

    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate

    std_dev = np.std(excess_returns, ddof=1)
    if std_dev == 0:
        return 0.0

    return np.mean(excess_returns) / std_dev


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    """Calculate maximum drawdown.

    Args:
        equity_curve: List of equity values over time

    Returns:
        Maximum drawdown as negative percentage
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    equity_array = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_array)
    drawdown = (equity_array - peak) / peak

    return np.min(drawdown) * 100  # Return as percentage


def calculate_expectancy(returns: list[float]) -> float:
    """Calculate expectancy (expected return per trade).

    Args:
        returns: List of trade returns

    Returns:
        Expectancy as percentage
    """
    if not returns:
        return 0.0

    win_rate = calculate_win_rate(returns)
    avg_win = np.mean([r for r in returns if r > 0]) if any(r > 0 for r in returns) else 0
    avg_loss = np.mean([r for r in returns if r < 0]) if any(r < 0 for r in returns) else 0

    return (win_rate * avg_win) + ((1 - win_rate) * avg_loss)


def calculate_calmar_ratio(
    returns: list[float], equity_curve: list[float]
) -> float:
    """Calculate Calmar ratio (return / max drawdown).

    Args:
        returns: List of trade returns
        equity_curve: List of equity values

    Returns:
        Calmar ratio
    """
    if not returns or not equity_curve:
        return 0.0

    total_return = sum(returns)
    max_dd = abs(calculate_max_drawdown(equity_curve))

    if max_dd == 0:
        return 0.0

    return total_return / max_dd


def calculate_var(returns: list[float], confidence: float = 0.95) -> float:
    """Calculate Value at Risk.

    Args:
        returns: List of trade returns
        confidence: Confidence level (default 95%)

    Returns:
        VaR as negative percentage
    """
    if not returns:
        return 0.0

    percentile = (1 - confidence) * 100
    return np.percentile(returns, percentile)


def calculate_cvar(returns: list[float], confidence: float = 0.95) -> float:
    """Calculate Conditional Value at Risk (Expected Shortfall).

    Args:
        returns: List of trade returns
        confidence: Confidence level (default 95%)

    Returns:
        CVaR as negative percentage
    """
    if not returns:
        return 0.0

    var = calculate_var(returns, confidence)
    tail_returns = [r for r in returns if r <= var]

    if not tail_returns:
        return var

    return np.mean(tail_returns)


def calculate_confidence_interval(
    returns: list[float], confidence: float = 0.95
) -> tuple[float, float]:
    """Calculate confidence interval for mean return.

    Args:
        returns: List of trade returns
        confidence: Confidence level

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if not returns or len(returns) < 2:
        return (0.0, 0.0)

    mean = np.mean(returns)
    std_err = np.std(returns, ddof=1) / np.sqrt(len(returns))

    # Z-score for confidence level
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    margin = z * std_err
    return (mean - margin, mean + margin)


def calculate_all_metrics(
    returns: list[float], equity_curve: list[float] | None = None
) -> dict[str, Any]:
    """Calculate all backtest metrics.

    Args:
        returns: List of trade returns
        equity_curve: Optional equity curve for drawdown calculations

    Returns:
        Dictionary with all metrics
    """
    if not returns:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0,
            "total_return": 0.0,
            "avg_return": 0.0,
            "var_95": 0.0,
            "cvar_95": 0.0,
            "worst_case_95": 0.0,
            "best_case_95": 0.0,
        }

    # Use cumulative returns as equity curve if not provided
    if equity_curve is None:
        equity_curve = [100]  # Start with $100
        for ret in returns:
            equity_curve.append(equity_curve[-1] * (1 + ret / 100))

    # Calculate confidence interval
    ci_lower, ci_upper = calculate_confidence_interval(returns)

    return {
        "total_trades": len(returns),
        "win_rate": calculate_win_rate(returns),
        "profit_factor": calculate_profit_factor(returns),
        "sharpe_ratio": calculate_sharpe_ratio(returns),
        "max_drawdown": calculate_max_drawdown(equity_curve),
        "expectancy": calculate_expectancy(returns),
        "calmar_ratio": calculate_calmar_ratio(returns, equity_curve),
        "total_return": sum(returns),
        "avg_return": np.mean(returns),
        "std_dev": np.std(returns, ddof=1),
        "var_95": calculate_var(returns),
        "cvar_95": calculate_cvar(returns),
        "worst_case_95": ci_lower,
        "best_case_95": ci_upper,
        "min_return": min(returns),
        "max_return": max(returns),
    }


def passes_thresholds(metrics: dict[str, Any], config: Any) -> tuple[bool, list[str]]:
    """Check if metrics pass all configured thresholds.

    Args:
        metrics: Dictionary of metrics
        config: Configuration object with thresholds

    Returns:
        Tuple of (passes, list of failure reasons)
    """
    failures = []

    if metrics["win_rate"] < config.min_win_rate:
        failures.append(
            f"Win rate {metrics['win_rate']:.2%} below threshold {config.min_win_rate:.2%}"
        )

    if metrics["sharpe_ratio"] < config.min_sharpe_ratio:
        failures.append(
            f"Sharpe ratio {metrics['sharpe_ratio']:.2f} below threshold {config.min_sharpe_ratio}"
        )

    if abs(metrics["max_drawdown"]) > config.max_drawdown_pct:
        failures.append(
            f"Max drawdown {metrics['max_drawdown']:.2f}% exceeds threshold {config.max_drawdown_pct}%"
        )

    if metrics["expectancy"] < config.min_expectancy * 100:  # Convert to percentage
        failures.append(
            f"Expectancy {metrics['expectancy']:.2f}% below threshold {config.min_expectancy * 100}%"
        )

    return len(failures) == 0, failures
