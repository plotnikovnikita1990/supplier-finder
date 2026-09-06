from pathlib import Path
import pandas as pd
from .models import Supplier

REQUIRED_COLUMNS = [
    "supplier_id","name","category","subcategory","region","coverage",
    "products","description","price","price_unit","min_order","min_order_unit",
    "delivery_terms","delivery_score","certifications","certification_verified",
    "rating","phone","email","website","source_url","source_type",
    "last_verified","notes"
]

def load_suppliers(path: str) -> list[Supplier]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл поставщиков не найден: {p}")
    df = pd.read_csv(p)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"В CSV отсутствуют обязательные колонки: {missing}")

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["min_order"] = pd.to_numeric(df["min_order"], errors="coerce")
    df["delivery_score"] = pd.to_numeric(df["delivery_score"], errors="coerce").fillna(0.5)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["certification_verified"] = df["certification_verified"].astype(str).str.lower().isin(
        {"true","1","yes","да"}
    )

    if df["supplier_id"].duplicated().any():
        raise ValueError("supplier_id должен быть уникальным.")

    if df["price"].isna().any() or (df["price"] <= 0).any():
        raise ValueError("Все цены должны быть положительными числами.")
    if df["min_order"].isna().any() or (df["min_order"] < 0).any():
        raise ValueError("Минимальный заказ должен быть >= 0.")
    if df["rating"].isna().any() or ~df["rating"].between(0, 5).all():
        raise ValueError("Рейтинг должен находиться в диапазоне 0–5.")

    return [Supplier(**row) for row in df.to_dict(orient="records")]

def suppliers_dataframe(suppliers: list[Supplier]) -> pd.DataFrame:
    return pd.DataFrame([s.model_dump() for s in suppliers])
