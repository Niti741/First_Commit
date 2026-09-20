
import pytest
from backend.app.exemplars.scoring import ExemplarScorer
from backend.app.exemplars.pruning import ExemplarPruner


def test_bayesian_scoring():
    # 1 win out of 1 trial = 100% raw win rate
    score_1_of_1 = ExemplarScorer.compute_quality_score(successful_rescues=1, times_selected=1)
    
    # 48 wins out of 50 trials = 96% raw win rate
    score_48_of_50 = ExemplarScorer.compute_quality_score(successful_rescues=48, times_selected=50)

    # Bayesian smoothed: 48/50 has much more evidence, so smoothed score is higher than 1/1
    # score_1_of_1 = (1 + 2.5) / (1 + 5.0) = 3.5 / 6.0 = ~0.5833
    # score_48_of_50 = (48 + 2.5) / (50 + 5.0) = 50.5 / 55.0 = ~0.9182
    assert score_48_of_50 > score_1_of_1
    assert score_1_of_1 == 0.5833
    assert score_48_of_50 == 0.9182


def test_diversity_protecting_pruner():
    exemplars = []
    # Add 20 general items with high score
    for i in range(20):
        exemplars.append({
            "id": f"gen-{i}",
            "question": f"General question {i}",
            "category": "general",
            "language": "en",
            "quality_score": 0.95
        })

    # Add 2 fees exemplars with slightly lower score
    for i in range(2):
        exemplars.append({
            "id": f"fees-{i}",
            "question": f"Fees question {i}",
            "category": "fees",
            "language": "en",
            "quality_score": 0.70
        })

    # Add 5 hinglish exemplars with lower score
    for i in range(5):
        exemplars.append({
            "id": f"hin-{i}",
            "question": f"Hinglish sawal {i}",
            "category": "hostel",
            "language": "hinglish",
            "quality_score": 0.65
        })

    # Prune down to 10
    pruned = ExemplarPruner.prune(exemplars, max_capacity=10)
    assert len(pruned) == 10

    # Ensure fees and hinglish were protected despite lower individual quality score
    categories = [x["category"] for x in pruned]
    languages = [x["language"] for x in pruned]
    assert "fees" in categories
    assert "hinglish" in languages
