"""Walk-forward validator — tests strategy robustness over rolling time windows."""
import contextlib
import io

import numpy as np
import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import WalkForwardWindow, WalkForwardResult

# Note: 'roi' excluded — existing ParameterOptimizer has a key mismatch bug
# (optimizer uses 'roi' but BacktestMetrics returns 'ROI'). Use 'sharpe_ratio' as default.
VALID_OPT_METRICS = {'sharpe_ratio', 'profit_factor', 'max_drawdown', 'sortino_ratio'}


class WalkForwardValidator:
    """Divide data into rolling or anchored windows for IS/OOS validation.

    Supports two modes:
    - Fixed params: test if strategy degrades over time with constant params.
    - Re-optimization: optimize on IS, validate on OOS (classic walk-forward analysis).

    Args:
        strategy_class: Strategy class inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        n_windows: Number of windows (>= 2).
        oos_ratio: Fraction of each window for OOS (0.0-1.0 exclusive).
        anchored: False=rolling (IS shifts), True=anchored (IS grows from start).
        **strategy_params: Fixed kwargs for strategy.
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        n_windows: int = 5,
        oos_ratio: float = 0.25,
        anchored: bool = False,
        **strategy_params,
    ):
        if n_windows < 2:
            raise ValueError(f"n_windows must be >= 2, got {n_windows}")
        if oos_ratio <= 0.0 or oos_ratio >= 1.0:
            raise ValueError(f"oos_ratio must be in (0.0, 1.0), got {oos_ratio}")
        if len(market_data) < n_windows * 20:
            raise ValueError(
                f"Insufficient data: {len(market_data)} bars for {n_windows} windows "
                f"(need at least {n_windows * 20})"
            )

        self.strategy_class = strategy_class
        self.market_data = market_data
        self.n_windows = n_windows
        self.oos_ratio = oos_ratio
        self.anchored = anchored
        self.strategy_params = strategy_params

    def run(
        self,
        param_ranges: dict | None = None,
        optimization_metric: str = 'sharpe_ratio',
        min_trades: int = 10,
        verbose: bool = True,
    ) -> WalkForwardResult:
        """Execute walk-forward validation.

        Args:
            param_ranges: If provided, re-optimize on each IS window.
                          If None, use fixed strategy_params.
            optimization_metric: Metric for optimizer and efficiency ratio.
            min_trades: Minimum trades for optimizer's get_best_params.
            verbose: Print per-window results.

        Returns:
            WalkForwardResult with per-window and aggregated metrics.
        """
        if param_ranges is not None and optimization_metric not in VALID_OPT_METRICS:
            raise ValueError(
                f"optimization_metric must be one of {VALID_OPT_METRICS}, "
                f"got '{optimization_metric}'"
            )

        windows_ranges = self._compute_windows()
        windows = []

        mode_label = "anchored" if self.anchored else "rolling"
        if verbose:
            opt_label = "optimization" if param_ranges else "fixed params"
            print(f"\n=== Walk-Forward Validation ({self.n_windows} windows, {mode_label}, {opt_label}) ===\n")

        for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_ranges):
            is_data = self.market_data.iloc[is_start:is_end].copy()
            oos_data = self.market_data.iloc[oos_start:oos_end].copy()

            if verbose:
                print(f"Window {i+1}/{self.n_windows}: "
                      f"IS [{is_data.index[0]} -> {is_data.index[-1]}] ({len(is_data)} bars) | "
                      f"OOS [{oos_data.index[0]} -> {oos_data.index[-1]}] ({len(oos_data)} bars)")

            # Determine params for this window
            if param_ranges is not None:
                best_params = self._optimize_window(is_data, param_ranges, optimization_metric, min_trades)
                full_params = {**self.strategy_params, **best_params}
            else:
                best_params = None
                full_params = self.strategy_params

            is_metrics = self._run_single_backtest(is_data, full_params)
            oos_metrics = self._run_single_backtest(oos_data, full_params)

            windows.append(WalkForwardWindow(
                window_id=i,
                is_start=is_data.index[0],
                is_end=is_data.index[-1],
                oos_start=oos_data.index[0],
                oos_end=oos_data.index[-1],
                best_params=best_params if param_ranges else None,
                is_metrics=is_metrics,
                oos_metrics=oos_metrics,
            ))

            if verbose:
                is_score = is_metrics.get(optimization_metric, 0)
                oos_score = oos_metrics.get(optimization_metric, 0)
                params_str = f"  params={best_params}" if best_params else ""
                print(f"  IS {optimization_metric}={is_score:.3f} | "
                      f"OOS {optimization_metric}={oos_score:.3f}{params_str}\n")

        # Aggregate
        valid_windows = [w for w in windows if 'error' not in w.oos_metrics]
        oos_combined_metrics = self._aggregate_oos_metrics(valid_windows)
        efficiency_ratio = self._compute_efficiency(valid_windows, optimization_metric)
        param_stability = self._compute_param_stability(valid_windows, param_ranges)

        if verbose:
            label = "ROBUST" if efficiency_ratio > 0.5 else ("MARGINAL" if efficiency_ratio > 0.3 else "OVERFITTING")
            print(f"Efficiency Ratio: {efficiency_ratio:.2f} ({label})")
            if param_stability:
                print("Param Stability:")
                for param, stats in param_stability.items():
                    cv_label = "STABLE" if stats['cv'] < 0.3 else ("MODERATE" if stats['cv'] < 0.5 else "UNSTABLE")
                    print(f"  {param}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, cv={stats['cv']:.2f} ({cv_label})")

        return WalkForwardResult(
            windows=windows,
            oos_combined_metrics=oos_combined_metrics,
            efficiency_ratio=efficiency_ratio,
            param_stability=param_stability,
        )

    def _compute_windows(self) -> list[tuple[int, int, int, int]]:
        """Compute (is_start, is_end, oos_start, oos_end) index tuples."""
        total = len(self.market_data)
        ranges = []

        if not self.anchored:
            # Rolling: non-overlapping consecutive windows
            window_size = total // self.n_windows
            oos_size = int(window_size * self.oos_ratio)
            is_size = window_size - oos_size

            for i in range(self.n_windows):
                base = i * window_size
                is_start = base
                is_end = base + is_size
                oos_start = is_end
                oos_end = base + window_size
                if i == self.n_windows - 1:
                    oos_end = total  # absorb residue
                ranges.append((is_start, is_end, oos_start, oos_end))
        else:
            # Anchored: IS always starts at 0, grows each window
            oos_total = int(total * self.oos_ratio)
            is_base = total - oos_total
            oos_per_window = oos_total // self.n_windows

            for i in range(self.n_windows):
                is_start = 0
                is_end = is_base + i * oos_per_window
                oos_start = is_end
                oos_end = is_end + oos_per_window
                if i == self.n_windows - 1:
                    oos_end = total
                ranges.append((is_start, is_end, oos_start, oos_end))

        return ranges

    def _optimize_window(self, is_data, param_ranges, metric, min_trades) -> dict:
        """Run ParameterOptimizer on IS data, return best params."""
        from optimization.optimizer import ParameterOptimizer

        with contextlib.redirect_stdout(io.StringIO()):
            optimizer = ParameterOptimizer(
                strategy_class=self.strategy_class,
                market_data=is_data,
                **self.strategy_params,
            )
            optimizer.optimize(
                param_ranges=param_ranges,
                metric=metric,
                show_progress=False,
            )
            best = optimizer.get_best_params(min_trades=min_trades)

        return best if best else {}

    def _run_single_backtest(self, data: pd.DataFrame, params: dict) -> dict:
        """Run backtest, return all_metrics. Returns {'error': msg} on failure."""
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                strategy = self.strategy_class(data=data, **params)
                runner = BacktestRunner(strategy)
                runner.run(verbose=False)
            return runner.metrics.all_metrics
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _aggregate_oos_metrics(valid_windows: list[WalkForwardWindow]) -> dict:
        """Average OOS metrics across valid windows."""
        if not valid_windows:
            return {}
        combined = {}
        keys = valid_windows[0].oos_metrics.keys()
        for key in keys:
            values = [
                w.oos_metrics[key] for w in valid_windows
                if isinstance(w.oos_metrics.get(key), (int, float))
            ]
            if values:
                combined[key] = sum(values) / len(values)
        return combined

    @staticmethod
    def _compute_efficiency(valid_windows: list[WalkForwardWindow], metric: str) -> float:
        """Compute OOS/IS efficiency ratio for target metric."""
        is_scores = [
            w.is_metrics[metric] for w in valid_windows
            if isinstance(w.is_metrics.get(metric), (int, float))
        ]
        oos_scores = [
            w.oos_metrics[metric] for w in valid_windows
            if isinstance(w.oos_metrics.get(metric), (int, float))
        ]
        if not is_scores or not oos_scores:
            return 0.0
        is_avg = sum(is_scores) / len(is_scores)
        oos_avg = sum(oos_scores) / len(oos_scores)
        return oos_avg / is_avg if abs(is_avg) > 1e-10 else 0.0

    @staticmethod
    def _compute_param_stability(
        valid_windows: list[WalkForwardWindow],
        param_ranges: dict | None,
    ) -> dict | None:
        """Compute coefficient of variation for each optimized parameter."""
        if param_ranges is None:
            return None
        windows_with_params = [w for w in valid_windows if w.best_params]
        if len(windows_with_params) < 2:
            return None

        stability = {}
        for param in windows_with_params[0].best_params:
            values = [
                w.best_params[param] for w in windows_with_params
                if param in w.best_params
            ]
            if values and all(isinstance(v, (int, float)) for v in values):
                mean = float(np.mean(values))
                std = float(np.std(values))
                cv = std / abs(mean) if abs(mean) > 1e-10 else float('inf')
                stability[param] = {
                    'values': values,
                    'mean': mean,
                    'std': std,
                    'cv': cv,
                }
        return stability if stability else None
