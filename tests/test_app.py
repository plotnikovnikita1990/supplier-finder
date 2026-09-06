from pathlib import Path
import pandas as pd

from src.data import load_suppliers
from src.search import compare_suppliers


def test_data_loads():
    path = Path(__file__).resolve().parents[1] / "data" / "suppliers.csv"
    df = load_suppliers(path)
    assert len(df) >= 30
    assert df["supplier_id"].is_unique
    assert df["category"].notna().all()


def test_compare_returns_result():
    rows = pd.DataFrame({
        "name": ["A", "B"],
        "final_score": [0.8, 0.7],
    })
    verdict, details = compare_suppliers(rows)
    assert "A" in verdict
    assert "B" in details
