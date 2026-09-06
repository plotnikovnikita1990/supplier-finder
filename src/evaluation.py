import math
from .models import Supplier, SearchQuery
from .ranking import RankingConfig, rank

def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)

def dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))

def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    rel = [1 if x in relevant_ids else 0 for x in ranked_ids[:k]]
    ideal = sorted(rel, reverse=True)
    ideal_dcg = dcg(ideal)
    return 0.0 if ideal_dcg == 0 else dcg(rel) / ideal_dcg

def evaluate_fixture(results: dict[str, list[str]], relevant: dict[str, set[str]], k: int = 5) -> dict[str, float]:
    recalls, ndcgs = [], []
    for q, ranked in results.items():
        recalls.append(recall_at_k(ranked, relevant.get(q, set()), k))
        ndcgs.append(ndcg_at_k(ranked, relevant.get(q, set()), k))
    return {
        f"Recall@{k}": sum(recalls) / len(recalls) if recalls else 0,
        f"NDCG@{k}": sum(ndcgs) / len(ndcgs) if ndcgs else 0,
    }
