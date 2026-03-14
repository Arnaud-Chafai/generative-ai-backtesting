"""ValidationSuite — orchestrator for all validation methods."""
import contextlib
import io

import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import ValidationReport
from validation.oos_split import OOSSplitValidator
from validation.monte_carlo import MonteCarloValidator
from validation.walk_forward import WalkForwardValidator


class ValidationSuite:
    """Run OOS Split, Monte Carlo, and Walk-Forward validation in sequence.

    Each validator can be skipped by setting its control parameter to 0.

    Args:
        strategy_class: Strategy class inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        **strategy_params: Fixed kwargs for strategy.
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        **strategy_params,
    ):
        self.strategy_class = strategy_class
        self.market_data = market_data
        self.strategy_params = strategy_params

    def run_all(
        self,
        # OOS params
        oos_ratio: float = 0.3,
        # Monte Carlo params
        mc_simulations: int = 1000,
        mc_seed: int | None = None,
        mc_confidence: float = 0.95,
        # Walk-Forward params
        wf_windows: int = 5,
        wf_oos_ratio: float = 0.25,
        wf_anchored: bool = False,
        # Walk-Forward optimization
        param_ranges: dict | None = None,
        optimization_metric: str = 'sharpe_ratio',
        wf_min_trades: int = 10,
        # General
        verbose: bool = True,
    ) -> ValidationReport:
        """Execute selected validators and produce consolidated report.

        Skip a validator by setting its control param to 0:
        - oos_ratio=0 -> skip OOS
        - mc_simulations=0 -> skip Monte Carlo
        - wf_windows=0 -> skip Walk-Forward
        """
        oos_result = None
        mc_result = None
        wf_result = None

        # 1. OOS Split
        if oos_ratio > 0:
            if verbose:
                print("=" * 55)
                print("STEP 1/3: Out-of-Sample Split")
                print("=" * 55)
            oos_validator = OOSSplitValidator(
                strategy_class=self.strategy_class,
                market_data=self.market_data,
                oos_ratio=oos_ratio,
                **self.strategy_params,
            )
            oos_result = oos_validator.run(verbose=verbose)

        # 2. Monte Carlo (needs trades from full backtest)
        if mc_simulations > 0:
            if verbose:
                print("\n" + "=" * 55)
                print("STEP 2/3: Monte Carlo Simulation")
                print("=" * 55)
            with contextlib.redirect_stdout(io.StringIO()):
                strategy_full = self.strategy_class(
                    data=self.market_data, **self.strategy_params
                )
                runner_full = BacktestRunner(strategy_full)
                runner_full.run(verbose=False)

            mc_validator = MonteCarloValidator(
                trades_df=runner_full.metrics.trade_metrics_df,
                initial_capital=strategy_full.initial_capital,
            )
            mc_result = mc_validator.run(
                n_simulations=mc_simulations,
                confidence_level=mc_confidence,
                seed=mc_seed,
                verbose=verbose,
            )

        # 3. Walk-Forward
        if wf_windows > 0:
            if verbose:
                print("\n" + "=" * 55)
                print("STEP 3/3: Walk-Forward Validation")
                print("=" * 55)
            wf_validator = WalkForwardValidator(
                strategy_class=self.strategy_class,
                market_data=self.market_data,
                n_windows=wf_windows,
                oos_ratio=wf_oos_ratio,
                anchored=wf_anchored,
                **self.strategy_params,
            )
            wf_result = wf_validator.run(
                param_ranges=param_ranges,
                optimization_metric=optimization_metric,
                min_trades=wf_min_trades,
                verbose=verbose,
            )

        # 4. Summary
        summary = self._generate_summary(oos_result, mc_result, wf_result)

        if verbose:
            print("\n" + "=" * 55)
            print("VALIDATION SUMMARY")
            print("=" * 55)
            if summary['is_robust']:
                print("Result: ROBUST — no significant issues detected")
            else:
                print("Result: ISSUES DETECTED")
                for issue in summary['issues']:
                    print(f"  ! {issue}")
            print(f"Scores: {summary['scores']}")

        return ValidationReport(
            oos=oos_result,
            monte_carlo=mc_result,
            walk_forward=wf_result,
            summary=summary,
        )

    @staticmethod
    def _generate_summary(oos, mc, wf) -> dict:
        """Analyze results and flag issues."""
        issues = []
        scores = {}

        if oos is not None:
            sharpe_deg = oos.degradation.get('sharpe_ratio', {})
            oos_degradation = sharpe_deg.get('pct_change', 0)
            scores['oos_degradation'] = oos_degradation
            if isinstance(oos_degradation, (int, float)) and oos_degradation < -50:
                issues.append(
                    f"OOS: sharpe_ratio degraded {oos_degradation:.1f}% vs in-sample"
                )

        if mc is not None:
            scores['mc_p_value'] = mc.p_value
            if mc.p_value < 0.2:
                issues.append(
                    f"MC: equity depends on trade order (p-value={mc.p_value:.2f})"
                )

        if wf is not None:
            scores['wf_efficiency'] = wf.efficiency_ratio
            if wf.efficiency_ratio < 0.3:
                issues.append(
                    f"WF: low efficiency ratio ({wf.efficiency_ratio:.2f}), "
                    f"possible overfitting"
                )
            if wf.param_stability:
                unstable = [
                    p for p, s in wf.param_stability.items()
                    if s['cv'] > 0.5
                ]
                if unstable:
                    issues.append(
                        f"WF: unstable parameters across windows: {unstable}"
                    )

        return {
            'is_robust': len(issues) == 0,
            'issues': issues,
            'scores': scores,
        }
