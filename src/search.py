from functools import lru_cache
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def load_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


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
    def _commercial_score(df: pd.DataFrame) -> np.ndarray:
        min_order = df["min_order_kg"].fillna(df["min_order_kg"].median()).to_numpy(float)
        price = df["price_per_kg"].fillna(df["price_per_kg"].median()).to_numpy(float)
        min_order_score = 1 - (min_order - min_order.min()) / max(np.ptp(min_order), 1)
        price_score = 1 - (price - price.min()) / max(np.ptp(price), 1)
        return 0.55 * min_order_score + 0.45 * price_score

    @staticmethod
    def _operational_score(df: pd.DataFrame, city: str | None) -> np.ndarray:
        score = np.full(len(df), 0.5)
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
        present = np.column_stack([df[c].fillna("").str.strip().ne("").to_numpy() for c in cols])
        return present.mean(axis=1)

    def search(self, query: str, df: pd.DataFrame | None = None, city: str | None = None,
               top_k: int = 8) -> pd.DataFrame:
        work = (self.df if df is None else df).reset_index(drop=True).copy()
        if work.empty:
            return work

        sims = self._semantic_similarity(query)
        # Maps the selected subset back to the master frame by supplier_id.
        sim_by_id = dict(zip(self.df["supplier_id"], sims))
        work["semantic_score"] = work["supplier_id"].map(sim_by_id).fillna(0.0)
        work["commercial_score"] = self._commercial_score(work)
        work["operational_score"] = self._operational_score(work, city)
        work["completeness_score"] = self._completeness_score(work)

        # Internal decision model. The weights are deliberately hidden from UI.
        work["final_score"] = (
            0.60 * work["semantic_score"]
            + 0.20 * work["commercial_score"]
            + 0.12 * work["operational_score"]
            + 0.08 * work["completeness_score"]
        )
        return work.sort_values(["final_score", "semantic_score"], ascending=False).head(top_k)


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
