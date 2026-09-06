from .models import SearchQuery, Supplier

def generate_rfq(query: SearchQuery, supplier: Supplier, sender_name: str = "Команда закупок") -> str:
    product = query.category or query.product or "интересующая продукция"
    region = query.region or "наш регион"
    lines = [
        f"Тема: Запрос коммерческого предложения — {product}",
        "",
        f"Здравствуйте, {supplier.name}!",
        "",
        f"Мы рассматриваем поставщиков продукции категории «{product}» для бизнеса.",
        f"Регион поставки: {region}.",
    ]
    if query.max_price is not None:
        lines.append(f"Ориентир по цене: до {query.max_price:,.0f} ₽.")
    if query.max_moq is not None:
        lines.append(f"Желаемый минимальный заказ: до {query.max_moq:,.0f}.")
    if query.certifications_required:
        lines.append("Необходимо предоставить информацию о сертификатах и декларациях соответствия.")
    if query.delivery_required:
        lines.append("Просьба описать условия и сроки доставки.")
    lines += [
        "",
        "Просьба предоставить:",
        "1. Актуальный прайс-лист и единицы измерения;",
        "2. Минимальный объём/сумму заказа;",
        "3. Условия оплаты и доставки;",
        "4. Доступные сертификаты и сопроводительные документы;",
        "5. Сроки поставки и контакт менеджера.",
        "",
        f"С уважением,\n{sender_name}",
    ]
    return "\n".join(lines)
