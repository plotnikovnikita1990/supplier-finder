from dataclasses import dataclass
import numpy as np
from .models import SearchQuery, Supplier, ScoredSupplier

@dataclass
class RankingConfig:
    weights: dict[str, float]

def _minmax(values: list[float], lower_is_better: bool = False) -> dict[int, float]:
    arr = np.array(values, dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    if np.isclose(lo, hi):
        scores = np.ones(len(arr))
    elif lower_is_better:
        scores = (hi - arr) / (hi - lo)
    else:
        scores = (arr - lo) / (hi - lo)
    return {i: float(np.clip(scores[i], 0, 1)) for i in range(len(arr))}

def apply_hard_filters(
    suppliers: list[Supplier], query: SearchQuery
) -> tuple[list[Supplier], list[str]]:
    filtered = []
    reasons = []
    for s in suppliers:
        if query.hard_region and query.region and query.region.lower() not in s.coverage.lower() and query.region.lower() not in s.region.lower():
            continue
        if query.hard_certifications and not s.certifications.strip():
            continue
        filtered.append(s)
    if not filtered:
        reasons.append("По обязательным условиям кандидаты не найдены. Показываем мягкий поиск.")
        return suppliers, reasons
    return filtered, reasons

def rank(
    suppliers: list[Supplier],
    semantic_scores: dict[str, float],
    query: SearchQuery,
    config: RankingConfig,
) -> list[ScoredSupplier]:
    if not suppliers:
        return []

    price_scores = _minmax([s.price for s in suppliers], lower_is_better=True)
    moq_scores = _minmax([s.min_order for s in suppliers], lower_is_better=True)
    rating_scores = _minmax([s.rating for s in suppliers], lower_is_better=False)

    results = []
    for i, s in enumerate(suppliers):
        sem = float(np.clip((semantic_scores.get(s.supplier_id, 0.0) + 1) / 2, 0, 1))
        price = price_scores[i]
        moq = moq_scores[i]
        cert = 1.0 if s.certifications.strip() else 0.0
        if s.certification_verified and cert:
            cert = 1.0
        delivery = float(np.clip(s.delivery_score, 0, 1))
        region = 1.0 if query.region and (
            query.region.lower() in s.region.lower() or query.region.lower() in s.coverage.lower()
        ) else 0.0
        rating = rating_scores[i]

        components = {
            "semantic": sem,
            "price": price,
            "moq": moq,
            "certifications": cert,
            "delivery": delivery,
            "region": region,
            "rating": rating,
        }
        final = sum(components[k] * config.weights.get(k, 0) for k in components)
        final *= 100

        matched = {
            "region": bool(region),
            "certifications": bool(cert),
            "delivery": bool(delivery >= 0.7),
            "price": bool(query.max_price is None or s.price <= query.max_price),
            "moq": bool(query.max_moq is None or s.min_order <= query.max_moq),
        }

        reasons = []
        warnings = []
        if sem >= 0.75:
            reasons.append("Хорошо соответствует смыслу запроса")
        if query.region and region:
            reasons.append("Работает в выбранном регионе")
        if query.max_price is not None and s.price <= query.max_price:
            reasons.append("Цена укладывается в заданный лимит")
        if query.max_moq is not None and s.min_order <= query.max_moq:
            reasons.append("Минимальный заказ укладывается в лимит")
        if s.certifications:
            reasons.append("Есть информация о документах/сертификатах")
        if s.delivery_score >= 0.7:
            reasons.append("Хорошие условия доставки")
        if s.rating >= 4.7:
            reasons.append("Высокий рейтинг")

        if query.max_price is not None and s.price > query.max_price:
            warnings.append("Цена выше указанного пользователем лимита")
        if query.max_moq is not None and s.min_order > query.max_moq:
            warnings.append("Минимальный заказ выше указанного пользователем лимита")
        if not s.certification_verified:
            warnings.append("Сертификаты не проверены системой")
        if s.source_type == "demo_dataset":
            warnings.append("Используются демонстрационные данные")

        results.append(ScoredSupplier(
            supplier=s,
            semantic_score=sem,
            final_score=float(final),
            components=components,
            matched=matched,
            reasons=reasons[:6],
            warnings=warnings[:5],
        ))

    return sorted(results, key=lambda x: x.final_score, reverse=True)
