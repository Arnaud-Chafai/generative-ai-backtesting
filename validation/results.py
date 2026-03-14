"""Dataclasses for validation module results."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class OOSResult:
    """Results from out-of-sample split validation."""
    in_sample_metrics: dict
    out_of_sample_metrics: dict
    split_date: pd.Timestamp
    is_size: int
    oos_size: int
    degradation: dict  # {metric: {'is': float, 'oos': float, 'pct_change': float}}


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo trade permutation."""
    original_final_equity: float
    simulated_equities: np.ndarray  # (n_simulations, n_trades)
    percentiles: dict  # {5: float, 25: float, 50: float, 75: float, 95: float}
    p_value: float
    max_drawdowns: np.ndarray  # (n_simulations,)
    confidence_intervals: dict  # {'final_equity': (lo, hi), 'max_drawdown': (lo, hi)}


@dataclass
class WalkForwardWindow:
    """Results from a single walk-forward window."""
    window_id: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    best_params: dict | None
    is_metrics: dict
    oos_metrics: dict


@dataclass
class WalkForwardResult:
    """Aggregated results from walk-forward validation."""
    windows: list[WalkForwardWindow]
    oos_combined_metrics: dict
    efficiency_ratio: float
    param_stability: dict | None  # {param: {'values', 'mean', 'std', 'cv'}}


@dataclass
class ValidationReport:
    """Consolidated report from all validators."""
    oos: OOSResult | None
    monte_carlo: MonteCarloResult | None
    walk_forward: WalkForwardResult | None
    summary: dict  # {'is_robust': bool, 'issues': list[str], 'scores': dict}
