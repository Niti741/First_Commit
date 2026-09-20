from typing import Dict, Any
from backend.app.config import settings


class ExemplarScorer:
    """
    Statistically sound scoring for exemplars using Bayesian smoothing.
    Prevents low-sample flukes (e.g. 1 rescue out of 1 trial = 100%)
    from outranking battle-tested exemplars (e.g. 48 rescues out of 50 trials = 96%).
    """

    PRIOR_SUCCESS = 2.5
    PRIOR_WEIGHT = 5.0  # Equivalent to 5 pseudo-observations centered at 0.50

    @classmethod
    def compute_quality_score(cls, successful_rescues: int, times_selected: int) -> float:
        if times_selected <= 0:
            return 0.50
        smoothed = (successful_rescues + cls.PRIOR_SUCCESS) / (times_selected + cls.PRIOR_WEIGHT)
        return round(float(smoothed), 4)

    @classmethod
    def compute_impact_score(
        cls,
        quality_score: float,
        successful_rescues: int,
        recency_weight: float = 1.0
    ) -> float:
        """
        Impact accounts for both quality and absolute volume of successful rescues.
        """
        raw_impact = quality_score * (1.0 + (successful_rescues * 0.1)) * recency_weight
        return round(float(raw_impact), 4)

    @classmethod
    def determine_status(cls, times_selected: int, quality_score: float) -> str:
        if times_selected < settings.EXEMPLAR_MIN_EVALUATIONS:
            return "active"
        if quality_score < 0.35:
            return "candidate_for_pruning"
        return "active"
