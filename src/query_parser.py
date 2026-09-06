import re
from .models import SearchQuery

REGIONS = [
    "Москва", "Московская область", "Санкт-Петербург", "Ленинградская область",
    "Екатеринбург", "Свердловская область", "Казань", "Республика Татарстан",
    "Новосибирск", "Новосибирская область", "Краснодар", "Краснодарский край",
    "Омск", "Омская область", "Самара", "Ростов-на-Дону", "Россия"
]

CATEGORIES = {
    "молочная": "Молочные продукты",
    "молоко": "Молочные продукты",
    "сыр": "Молочные продукты",
    "мяс": "Мясо и птица",
    "птиц": "Мясо и птица",
    "овощ": "Овощи и фрукты",
    "фрукт": "Овощи и фрукты",
    "бакале": "Бакалея",
    "круп": "Бакалея",
    "масл": "Бакалея",
    "напит": "Напитки",
    "кофе": "Напитки",
    "чай": "Напитки",
    "упаков": "Упаковка",
    "соус": "Соусы и специи",
    "спец": "Соусы и специи",
    "заморож": "Замороженные продукты",
    "полуфаб": "Замороженные продукты",
    "кондитер": "Кондитерские изделия",
    "слад": "Кондитерские изделия",
}

CERT_WORDS = ("сертифик", "хассп", "haccp", "iso", "документ", "декларац")
DELIVERY_WORDS = ("доставк", "привез", "логист", "доставка")
HARD_WORDS = ("только", "обязательно", "нужен", "нужны", "требуется", "требуются")

def _number_after(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            try:
                return float(m.group(1).replace(" ", "").replace(",", "."))
            except ValueError:
                return None
    return None

def parse_query(text: str) -> SearchQuery:
    raw = text.strip()
    low = raw.lower()

    region = next((r for r in REGIONS if r.lower() in low), None)
    category = next((v for k, v in CATEGORIES.items() if k in low), None)

    max_price = _number_after(low, [
        r"(?:до|не дороже|максимум)\s*([\d\s]+(?:[.,]\d+)?)\s*(?:₽|руб|рублей)?",
    ])
    max_moq = _number_after(low, [
        r"(?:moq|минимальн\w*\s+заказ\w*|парт\w*|объ[её]м\w*)\s*(?:до)?\s*([\d\s]+(?:[.,]\d+)?)\s*(?:кг|шт|л|руб)?",
        r"до\s*([\d\s]+(?:[.,]\d+)?)\s*(?:кг|шт|л)",
    ])

    cert = any(w in low for w in CERT_WORDS)
    delivery = any(w in low for w in DELIVERY_WORDS)
    hard = any(w in low for w in HARD_WORDS)

    return SearchQuery(
        raw_text=raw,
        product=raw if category is None else None,
        category=category,
        region=region,
        max_price=max_price,
        max_moq=max_moq,
        certifications_required=cert,
        delivery_required=delivery,
        hard_region=bool(region and hard),
        hard_certifications=bool(cert and hard),
    )
