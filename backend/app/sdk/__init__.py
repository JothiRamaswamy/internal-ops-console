"""Feature-flag SDK — dependency-free flag evaluation for application code.

Import the evaluator or the lightweight client:

    from app.sdk import FeatureFlagClient, evaluate, is_enabled
"""

from app.sdk.feature_flags import (
    Evaluation,
    FeatureFlagClient,
    evaluate,
    is_enabled,
)

__all__ = ["Evaluation", "FeatureFlagClient", "evaluate", "is_enabled"]
