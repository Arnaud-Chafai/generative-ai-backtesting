"""Out-of-sample split validator — detects overfitting via IS/OOS comparison."""
import contextlib
import io

import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import OOSResult

METRICS_TO_COMPARE = [
    'sharpe_ratio',
    'ROI',
    'profit_factor',
    'percent_profitable',
    'max_drawdown_pct',
]


class OOSSplitValidator:
    """Split data into in-sample and out-of-sample periods.

    Runs independent backtests on each portion and measures degradation
    of key metrics to detect overfitting.

    Args:
        strategy_class: Strategy class (not instance) inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        oos_ratio: Fraction of data for OOS (0.0-1.0 exclusive).
        **strategy_params: Fixed kwargs for strategy (symbol, timeframe, etc.)
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        oos_ratio: float = 0.3,
        **strategy_params,
    ):
        if oos_ratio <= 0.0 or oos_ratio >= 1.0:
            raise ValueError(f"oos_ratio must be in (0.0, 1.0), got {oos_ratio}")
        if len(market_data) < 20:
            raise ValueError(
                f"market_data must have at least 20 rows, got {len(market_data)}"
            )

        self.strategy_class = strategy_class
        self.market_data = market_data
        self.oos_ratio = oos_ratio
        self.strategy_params = strategy_params

    def run(self, verbose: bool = True) -> OOSResult:
        """Execute OOS split validation.

        Args:
            verbose: Print results summary.

        Returns:
            OOSResult with IS/OOS metrics and degradation analysis.
        """
        # Split data
        split_index = int(len(self.market_data) * (1 - self.oos_ratio))
        is_data = self.market_data.iloc[:split_index].copy()
        oos_data = self.market_data.iloc[split_index:].copy()
        split_date = oos_data.index[0]

        # Run IS backtest
        is_metrics = self._run_backtest(is_data)

        # Run OOS backtest
        oos_metrics = self._run_backtest(oos_data)

        # Calculate degradation
        degradation = {}
        for metric in METRICS_TO_COMPARE:
            is_val = is_metrics.get(metric, 0)
            oos_val = oos_metrics.get(metric, 0)
            if abs(is_val) > 1e-10:
                pct_change = (oos_val - is_val) / abs(is_val) * 100
            elif abs(oos_val) > 1e-10:
                pct_change = float('inf')
            else:
                pct_change = 0.0
            degradation[metric] = {
                'is': is_val,
                'oos': oos_val,
                'pct_change': pct_change,
            }

        if verbose:
            print(f"\n=== OOS Split Validation ===")
            print(f"Split date: {split_date}")
            print(f"In-Sample: {len(is_data)} bars | Out-of-Sample: {len(oos_data)} bars\n")
            print(f"{'Metric':<25} {'IS':>10} {'OOS':>10} {'Change':>10}")
            print("-" * 57)
            for metric, vals in degradation.items():
                pct = vals['pct_change']
                pct_str = f"{pct:+.1f}%" if pct != float('inf') else "inf"
                print(f"{metric:<25} {vals['is']:>10.3f} {vals['oos']:>10.3f} {pct_str:>10}")

        return OOSResult(
            in_sample_metrics=is_metrics,
            out_of_sample_metrics=oos_metrics,
            split_date=split_date,
            is_size=len(is_data),
            oos_size=len(oos_data),
            degradation=degradation,
        )

    def _run_backtest(self, data: pd.DataFrame) -> dict:
        """Run a single backtest and return all_metrics dict."""
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                strategy = self.strategy_class(data=data, **self.strategy_params)
                runner = BacktestRunner(strategy)
                runner.run(verbose=False)
            return runner.metrics.all_metrics
        except Exception as e:
            if 'verbose' not in dir(self) or True:
                print(f"  Warning: backtest failed — {e}")
            return {'error': str(e)}
