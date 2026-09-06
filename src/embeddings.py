import numpy as np
from sentence_transformers import SentenceTransformer

class SemanticIndex:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.matrix: np.ndarray | None = None

    def build(self, texts: list[str]) -> None:
        self.matrix = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

    def search(self, query: str, top_k: int = 30) -> list[tuple[int, float]]:
        if self.matrix is None:
            raise RuntimeError("Индекс не построен.")
        vector = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )[0]
        scores = self.matrix @ vector
        idx = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in idx]
