from functools import lru_cache
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Common Russian stop words that do not describe the requested product.
STOP_WORDS = {
    "для", "в", "во", "на", "и", "или", "с", "со", "из", "от", "по", "под", "при",
    "как", "нужны", "нужен", "нужна", "ищу", "найти", "поставщик", "поставщики", "оптом",
    "оптовые", "оптовый", "оптовая", "заказать", "заказ", "купить", "поставка", "поставки",
    "цена", "цены", "стоимость", "кг", "кг.", "тонн", "тонна", "для ресторана", "ресторан",
}


@lru_cache(maxsize=1)
def load_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[а-яa-zё0-9-]+", str(text).lower()) if t not in STOP_WORDS]


def _token_matches(query_tokens: list[str], text: str) -> int:
    doc_tokens = _tokens(text)
    if not query_tokens or not doc_tokens:
        return 0
    matched = 0
    for q in query_tokens:
        if len(q) < 4:
            continue
        # Prefix matching handles basic Russian inflections: капуста/капусту/капустой.
        if any((d.startswith(q[:5]) or q.startswith(d[:5])) for d in doc_tokens if len(d) >= 4):
            matched += 1
    return matched


class SemanticSearch:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True).copy()
        self._mode = "semantic"
        try:
            self.encoder = load_encoder()
            self.embeddings = self.encoder.encode(
                self.df["search_text"].tolist(),
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception:
            self._mode = "fallback"
            self.encoder = None
            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=20000
            )
            self.embeddings = self.vectorizer.fit_transform(self.df["search_text"])

    @property
    def mode(self) -> str:
        return self._mode

    def _semantic_similarity(self, query: str) -> np.ndarray:
        if self._mode == "semantic":
            q = self.encoder.encode([query], normalize_embeddings=True, show_progress_bar=False)
            return np.clip(self.embeddings @ q[0], 0, 1)
        q = self.vectorizer.transform([query])
        return np.clip(cosine_similarity(self.embeddings, q).ravel(), 0, 1)

    @staticmethod
    def _lexical_score(query: str, df: pd.DataFrame) -> np.ndarray:
        query_tokens = _tokens(query)
        scores = []
        for _, row in df.iterrows():
            # Product-relevant fields carry the strongest signal.
            product_text = " ".join(
                [
                    str(row.get("name", "")),
                    str(row.get("category", "")),
                    str(row.get("product_description", "")),
                    str(row.get("notes", "")),
                ]
            )
            matched = _token_matches(query_tokens, product_text)
            scores.append(matched / max(len([t for t in query_tokens if len(t) >= 4]), 1))
        return np.array(scores, dtype=float)

    @staticmethod
    def _commercial_score(df: pd.DataFrame) -> np.ndarray:
        min_order = df["min_order_kg"].fillna(df["min_order_kg"].median()).to_numpy(float)
        price = df["price_per_kg"].fillna(df["price_per_kg"].median()).to_numpy(float)
        min_order_score = 1 - (min_order - min_order.min()) / max(np.ptp(min_order), 1)
        price_score = 1 - (price - price.min()) / max(np.ptp(price), 1)
        return 0.55 * min_order_score + 0.45 * price_score

    @staticmethod
    def _operational_score(df: pd.DataFrame, city: str | None) -> np.ndarray:
        score = np.full(len(df), 0.5, dtype=float)
        delivery = df["delivery"].fillna("").str.lower()
        score += delivery.str.contains("1-2 дня|ежедневно", regex=True).to_numpy() * 0.25
        if city:
            city_mask = df["city"].str.casefold().eq(city.casefold()).to_numpy()
            coverage = df["coverage_region"].fillna("").str.contains(city, case=False, regex=False).to_numpy()
            score += city_mask * 0.2 + coverage * 0.05
        return np.clip(score, 0, 1)

    @staticmethod
    def _completeness_score(df: pd.DataFrame) -> np.ndarray:
        cols = ["certifications", "delivery", "coverage_region", "phone", "email", "website"]
        present = np.column_stack(
            [df[c].fillna("").str.strip().ne("").to_numpy() for c in cols]
        )
        return present.mean(axis=1)

    @staticmethod
    def add_rating(df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result["rating"] = (1 + 4 * result["final_score"].clip(0, 1)).round(1)
        return result

    def rank_filtered(self, df: pd.DataFrame, city: str | None = None) -> pd.DataFrame:
        work = df.reset_index(drop=True).copy()
        if work.empty:
            return work
        work["semantic_score"] = 0.5
        work["lexical_score"] = 0.0
        work["commercial_score"] = self._commercial_score(work)
        work["operational_score"] = self._operational_score(work, city)
        work["completeness_score"] = self._completeness_score(work)
        work["final_score"] = (
            0.55 * work["commercial_score"]
            + 0.27 * work["operational_score"]
            + 0.18 * work["completeness_score"]
        )
        return self.add_rating(work).sort_values(
            ["final_score", "orders_count"], ascending=[False, False]
        )

    def search(
        self,
        query: str,
        df: pd.DataFrame | None = None,
        city: str | None = None,
        top_k: int = 8,
    ) -> pd.DataFrame:
        work = (self.df if df is None else df).reset_index(drop=True).copy()
        if work.empty:
            return work

        semantic = self._semantic_similarity(query)
        semantic_by_id = dict(zip(self.df["supplier_id"], semantic))
        work["semantic_score"] = work["supplier_id"].map(semantic_by_id).fillna(0.0)
        work["lexical_score"] = self._lexical_score(query, work)

        # Critical relevance gate: when at least one supplier explicitly contains
        # the requested product term, unrelated suppliers are removed from the pool.
        explicit_matches = work["lexical_score"] > 0
        if explicit_matches.any():
            work = work.loc[explicit_matches].copy()

        work["commercial_score"] = self._commercial_score(work)
        work["operational_score"] = self._operational_score(work, city)
        work["completeness_score"] = self._completeness_score(work)

        # Product match dominates semantic similarity; semantics resolves ordering
        # between suppliers that really offer the requested product.
        work["final_score"] = (
            0.55 * work["lexical_score"]
            + 0.25 * work["semantic_score"]
            + 0.10 * work["commercial_score"]
            + 0.07 * work["operational_score"]
            + 0.03 * work["completeness_score"]
        )
        work = self.add_rating(work)
        return work.sort_values(["final_score", "orders_count"], ascending=[False, False]).head(top_k)


def compare_suppliers(rows: pd.DataFrame) -> tuple[str, str]:
    if len(rows) < 2:
        raise ValueError("Для сравнения нужно минимум два поставщика")
    ordered = rows.sort_values("final_score", ascending=False).reset_index(drop=True)
    winner = ordered.iloc[0]
    second = ordered.iloc[1]
    delta = float(winner["final_score"] - second["final_score"])

    if delta >= 0.08:
        verdict = f"Рекомендуемый поставщик: {winner['name']}"
    elif delta >= 0.03:
        verdict = f"Небольшое преимущество: {winner['name']}"
    else:
        verdict = f"Поставщики сопоставимы; небольшой перевес у {winner['name']}"

    details = (
        f"{winner['name']} лучше подходит под текущий запрос по совокупности соответствия ассортименту, "
        f"условий закупки, логистики и полноты данных. {second['name']} — ближайшая альтернатива."
    )
    return verdict, details
