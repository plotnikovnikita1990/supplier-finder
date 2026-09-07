from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = [
    "supplier_id", "name", "category", "city", "region", "product_description",
    "min_order_kg", "price_per_kg", "orders_count", "certifications", "delivery", "coverage_region",
    "contact_name", "phone", "email", "website", "source", "notes"
]


def load_suppliers(path: str | Path = "data/suppliers.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"В CSV отсутствуют обязательные поля: {', '.join(missing)}")

    for col in ["min_order_kg", "price_per_kg", "orders_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["orders_count"] = df["orders_count"].fillna(0).astype(int)
    df["search_text"] = (
        df["name"].fillna("") + " "
        + df["category"].fillna("") + " "
        + df["city"].fillna("") + " "
        + df["region"].fillna("") + " "
        + df["product_description"].fillna("") + " "
        + df["certifications"].fillna("") + " "
        + df["delivery"].fillna("") + " "
        + df["coverage_region"].fillna("") + " "
        + df["notes"].fillna("")
    )
    return df
