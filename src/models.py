from typing import Any, Optional
from pydantic import BaseModel, Field

class SearchQuery(BaseModel):
    raw_text: str
    product: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    max_price: Optional[float] = Field(default=None, ge=0)
    max_moq: Optional[float] = Field(default=None, ge=0)
    certifications_required: bool = False
    delivery_required: bool = False
    hard_region: bool = False
    hard_certifications: bool = False

class Supplier(BaseModel):
    supplier_id: str
    name: str
    category: str
    subcategory: str
    region: str
    coverage: str
    products: str
    description: str
    price: float
    price_unit: str
    min_order: float
    min_order_unit: str
    delivery_terms: str
    delivery_score: float = Field(ge=0, le=1)
    certifications: str
    certification_verified: bool = False
    rating: float = Field(ge=0, le=5)
    phone: str = ""
    email: str = ""
    website: str = ""
    source_url: str = ""
    source_type: str = "demo_dataset"
    last_verified: str = ""
    notes: str = ""

    @property
    def text_for_embedding(self) -> str:
        return " ".join([
            self.name, self.category, self.subcategory, self.region,
            self.coverage, self.products, self.description,
            self.delivery_terms, self.certifications, self.notes
        ])

class ScoredSupplier(BaseModel):
    supplier: Supplier
    semantic_score: float
    final_score: float
    components: dict[str, float]
    matched: dict[str, bool]
    reasons: list[str]
    warnings: list[str]
