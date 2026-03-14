"""Monte Carlo validator — tests equity curve robustness via trade permutation."""
import numpy as np
import pandas as pd

from validation.results import MonteCarloResult


class MonteCarloValidator:
    """Validate equity curve robustness by permuting trade order.

    Shuffles the P&L sequence N times to generate a distribution of
    equity curves. If the real result sits comfortably within the
    distribution, the strategy is robust to trade ordering.

    Args:
        trades_df: DataFrame with 'net_pnl' or 'net_profit_loss' column.
        initial_capital: Starting capital for equity curves.
    """

    def __init__(self, trades_df: pd.DataFrame, initial_capital: float = 1000.0):
        # Detect P&L column
        if 'net_pnl' in trades_df.columns:
            self._pnl_col = 'net_pnl'
        elif 'net_profit_loss' in trades_df.columns:
            self._pnl_col = 'net_profit_loss'
        else:
            raise ValueError(
                f"trades_df must have 'net_pnl' or 'net_profit_loss' column. "
                f"Found columns: {list(trades_df.columns)}"
            )

        if len(trades_df) < 2:
            raise ValueError(
                f"trades_df must have at least 2 trades for permutation. "
                f"Got {len(trades_df)}."
            )

        self.trades_df = trades_df
        self.initial_capital = initial_capital

    def run(
        self,
        n_simulations: int = 1000,
        confidence_level: float = 0.95,
        seed: int | None = None,
        verbose: bool = True,
    ) -> MonteCarloResult:
        """Run Monte Carlo permutation analysis.

        Args:
            n_simulations: Number of random permutations.
            confidence_level: For confidence intervals (e.g. 0.95 = 95%).
            seed: Random seed for reproducibility.
            verbose: Print results summary.

        Returns:
            MonteCarloResult with equity distributions and statistics.
        """
        pnl_series = self.trades_df[self._pnl_col].values.astype(float)
        n_trades = len(pnl_series)

        # Original equity curve
        original_equity = self.initial_capital + np.cumsum(pnl_series)
        original_final = float(original_equity[-1])

        # Generate permutations
        rng = np.random.default_rng(seed)
        simulated_equities = np.zeros((n_simulations, n_trades))
        max_drawdowns = np.zeros(n_simulations)

        for i in range(n_simulations):
            shuffled = rng.permutation(pnl_series)
            equity = self.initial_capital + np.cumsum(shuffled)
            simulated_equities[i] = equity

            running_max = np.maximum.accumulate(equity)
            drawdown_pct = np.where(
                running_max > 0,
                (running_max - equity) / running_max,
                0.0,
            )
            max_drawdowns[i] = float(drawdown_pct.max())

        # Statistics
        final_equities = simulated_equities[:, -1]
        percentiles = {
            p: float(np.percentile(final_equities, p))
            for p in [5, 25, 50, 75, 95]
        }

        p_value = float(np.mean(final_equities >= original_final))

        alpha = 1 - confidence_level
        lower_pct = (alpha / 2) * 100
        upper_pct = (1 - alpha / 2) * 100
        confidence_intervals = {
            'final_equity': (
                float(np.percentile(final_equities, lower_pct)),
                float(np.percentile(final_equities, upper_pct)),
            ),
            'max_drawdown': (
                float(np.percentile(max_drawdowns, lower_pct)),
                float(np.percentile(max_drawdowns, upper_pct)),
            ),
        }

        if verbose:
            print(f"\n=== Monte Carlo Validation ({n_simulations} simulations) ===")
            print(f"Original final equity: ${original_final:,.2f}")
            print(f"\nSimulated equity distribution:")
            print(f"  P5:  ${percentiles[5]:,.2f}  |  P25: ${percentiles[25]:,.2f}  |  "
                  f"P50: ${percentiles[50]:,.2f}  |  P75: ${percentiles[75]:,.2f}  |  "
                  f"P95: ${percentiles[95]:,.2f}")
            label = "ROBUST" if p_value > 0.4 else ("ACCEPTABLE" if p_value > 0.2 else "FRAGILE")
            print(f"\np-value: {p_value:.2f} ({label})")
            lo_eq, hi_eq = confidence_intervals['final_equity']
            lo_dd, hi_dd = confidence_intervals['max_drawdown']
            print(f"\n{confidence_level:.0%} Confidence Intervals:")
            print(f"  Final equity: [${lo_eq:,.2f}, ${hi_eq:,.2f}]")
            print(f"  Max drawdown: [{lo_dd:.1%}, {hi_dd:.1%}]")

        return MonteCarloResult(
            original_final_equity=original_final,
            simulated_equities=simulated_equities,
            percentiles=percentiles,
            p_value=p_value,
            max_drawdowns=max_drawdowns,
            confidence_intervals=confidence_intervals,
        )
