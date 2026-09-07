from pathlib import Path
import pandas as pd

from src.data import load_suppliers
from src.search import compare_suppliers, SemanticSearch


def test_data_loads():
    path = Path(__file__).resolve().parents[1] / "data" / "suppliers.csv"
    df = load_suppliers(path)
    assert len(df) >= 30
    assert df["supplier_id"].is_unique
    assert df["category"].notna().all()
    assert (df["orders_count"] >= 0).all()


def test_compare_returns_result():
    rows = pd.DataFrame({
        "name": ["A", "B"],
        "final_score": [0.8, 0.7],
    })
    verdict, details = compare_suppliers(rows)
    assert "A" in verdict
    assert "B" in details


def test_rank_filtered_creates_rating():
    path = Path(__file__).resolve().parents[1] / "data" / "suppliers.csv"
    df = load_suppliers(path)
    search = object.__new__(SemanticSearch)
    search.df = df.reset_index(drop=True).copy()
    results = search.rank_filtered(df.head(5), city="Москва")
    assert not results.empty
    assert "rating" in results.columns
    assert results["rating"].between(1, 5).all()
