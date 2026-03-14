"""Validation module for detecting overfitting in backtested strategies."""
from .results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)

try:
    from .monte_carlo import MonteCarloValidator
except ImportError:
    pass

try:
    from .oos_split import OOSSplitValidator
except ImportError:
    pass

try:
    from .walk_forward import WalkForwardValidator
except ImportError:
    pass

try:
    from .validation_suite import ValidationSuite
except ImportError:
    pass
