from typing import List, Dict, Any
from backend.app.config import settings


class ExemplarPruner:
    """
    Self-pruning manager for exemplar store.
    When approaching MAX_EXEMPLARS capacity, prunes low-impact exemplars while
    strictly safeguarding category and language diversity:
      - Protected categories: fees, hostel, exams, attendance, placements, library, scholarships, academic, services
      - Protected languages: English and Hinglish proportional distribution
      - Safeguards top-performing high-impact exemplars
    """

    PROTECTED_CATEGORIES = [
        "fees", "hostel", "mess", "exams", "academic", "attendance",
        "placements", "library", "scholarships", "services"
    ]

    MIN_PER_CATEGORY = 2
    MIN_HINGLISH = 5

    @classmethod
    def prune(cls, exemplars: List[Dict[str, Any]], max_capacity: int = settings.MAX_EXEMPLARS) -> List[Dict[str, Any]]:
        if len(exemplars) <= max_capacity:
            return exemplars

        # Group by category
        category_buckets = {}
        for ex in exemplars:
            cat = ex.get("category", "general")
            category_buckets.setdefault(cat, []).append(ex)

        # Sort each bucket by quality_score descending
        for cat in category_buckets:
            category_buckets[cat].sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)

        protected = []
        candidates = []

        # Retain minimum quota for each protected category
        for cat, items in category_buckets.items():
            quota = cls.MIN_PER_CATEGORY
            protected.extend(items[:quota])
            candidates.extend(items[quota:])

        # Ensure minimum Hinglish representation
        hinglish_in_protected = sum(1 for x in protected if x.get("language") == "hinglish")
        if hinglish_in_protected < cls.MIN_HINGLISH:
            extra_needed = cls.MIN_HINGLISH - hinglish_in_protected
            hinglish_candidates = [x for x in candidates if x.get("language") == "hinglish"]
            for h_ex in hinglish_candidates[:extra_needed]:
                protected.append(h_ex)
                if h_ex in candidates:
                    candidates.remove(h_ex)

        # Fill remaining slots up to max_capacity based on impact/quality score
        remaining_slots = max_capacity - len(protected)
        if remaining_slots > 0:
            candidates.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)
            protected.extend(candidates[:remaining_slots])

        return protected
