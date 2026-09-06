from dataclasses import dataclass
import os

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

@dataclass(frozen=True)
class Settings:
    data_path: str = "data/suppliers.csv"
    embedding_model: str = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    top_k_retrieval: int = 30
    top_k_results: int = 12

DEFAULT_WEIGHTS = {
    "semantic": 35,
    "price": 15,
    "moq": 15,
    "certifications": 15,
    "delivery": 10,
    "region": 5,
    "rating": 5,
}

WEIGHT_LABELS = {
    "semantic": "Соответствие запросу",
    "price": "Цена",
    "moq": "Минимальный заказ",
    "certifications": "Документы и сертификаты",
    "delivery": "Доставка",
    "region": "Регион",
    "rating": "Рейтинг",
}
