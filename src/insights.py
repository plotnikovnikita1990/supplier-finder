"""
Модуль для генерации инсайтов и рекомендаций по поставщикам
Помогает пользователю принять решение: кому звонить и что спрашивать
"""

import re
from typing import Dict, List, Optional


def generate_supplier_insights(supplier: Dict, query: str = "", rank: int = 1) -> Dict:
    """
    Генерация аналитики и рекомендаций по поставщику
    
    Args:
        supplier: Данные поставщика
        query: Поисковый запрос пользователя
        rank: Позиция в выдаче
    
    Returns:
        Dict с инсайтами, рекомендациями и вопросами
    """
    
    # 1. Определяем сильные стороны
    strengths = _analyze_strengths(supplier)
    
    # 2. Формируем рекомендацию
    recommendation = _build_recommendation(supplier, strengths)
    
    # 3. Генерируем вопросы для звонка
    questions = _generate_questions(supplier)
    
    # 4. Выявляем риски
    risks = _identify_risks(supplier)
    
    # 5. Определяем лучший сценарий использования
    best_use_case = _determine_best_use_case(supplier, strengths)
    
    return {
        'strengths': strengths[:5],  # Топ-5 сильных сторон
        'recommendation_reason': recommendation,
        'questions_to_ask': questions[:5],  # Топ-5 вопросов
        'risks': risks[:3],  # Топ-3 риска
        'best_use_case': best_use_case
    }


def _analyze_strengths(supplier: Dict) -> List[tuple]:
    """Анализ сильных сторон поставщика"""
    strengths = []
    
    # 1. Ценовой фактор
    price = supplier.get('price_range', '').lower()
    if 'низк' in price or 'дешев' in price:
        strengths.append(("💰 Цена", "Ниже рынка", "✅", 90))
    elif 'средн' in price:
        strengths.append(("💰 Цена", "Рыночная", "➖", 60))
    elif price and price != 'не указано':
        strengths.append(("💰 Цена", "Указана", "✅", 70))
    else:
        strengths.append(("💰 Цена", "Требует уточнения", "❓", 30))
    
    # 2. Логистика и доставка
    delivery = supplier.get('delivery_conditions', '').lower()
    if 'день' in delivery:
        # Ищем количество дней
        days = re.findall(r'\d+', delivery)
        if days and int(days[0]) <= 3:
            strengths.append(("🚚 Доставка", f"Быстрая ({days[0]} дня)", "✅", 95))
        elif days and int(days[0]) <= 7:
            strengths.append(("🚚 Доставка", f"Стандартная ({days[0]} дн.)", "➖", 65))
        else:
            strengths.append(("🚚 Доставка", "Есть условия", "✅", 70))
    elif delivery and delivery != 'не указано':
        strengths.append(("🚚 Доставка", "Указана", "✅", 60))
    else:
        strengths.append(("🚚 Доставка", "Не указана", "❓", 20))
    
    # 3. Минимальный заказ
    min_order = supplier.get('min_order', '').lower()
    if 'нет' in min_order or 'от 1' in min_order or 'без' in min_order:
        strengths.append(("📦 Заказ", "Нет ограничений", "✅", 100))
    elif 'от' in min_order:
        numbers = re.findall(r'\d+', min_order)
        if numbers:
            amount = int(numbers[0])
            if amount < 1000:
                strengths.append(("📦 Заказ", f"Доступный (от {amount})", "✅", 85))
            elif amount < 5000:
                strengths.append(("📦 Заказ", f"Средний (от {amount})", "➖", 55))
            else:
                strengths.append(("📦 Заказ", f"Крупный (от {amount})", "⚠️", 30))
    elif min_order and min_order != 'не указано':
        strengths.append(("📦 Заказ", "Указан", "✅", 60))
    else:
        strengths.append(("📦 Заказ", "Не указан", "❓", 20))
    
    # 4. Документы и сертификаты
    docs = supplier.get('documents', '')
    if docs and docs != 'не указано':
        doc_list = [d.strip() for d in docs.split(';') if d.strip()]
        if len(doc_list) >= 3:
            strengths.append(("📋 Документы", f"{len(doc_list)} сертификатов", "✅", 90))
        else:
            strengths.append(("📋 Документы", f"{len(doc_list)} документа", "✅", 70))
    else:
        strengths.append(("📋 Документы", "Не указаны", "❓", 20))
    
    # 5. Регион работы
    region = supplier.get('region', '')
    city = supplier.get('city', '')
    if region and region != 'не указано':
        strengths.append(("📍 Регион", region, "✅", 70))
    elif city and city != 'не указано':
        strengths.append(("📍 Город", city, "✅", 60))
    else:
        strengths.append(("📍 Регион", "Не указан", "❓", 20))
    
    # 6. Контакты
    contacts = supplier.get('contacts', '')
    website = supplier.get('website', '')
    if contacts and contacts != 'не указано' and website and website != 'не указано':
        strengths.append(("📞 Контакты", "Есть телефон и сайт", "✅", 90))
    elif contacts and contacts != 'не указано':
        strengths.append(("📞 Контакты", "Есть телефон", "✅", 70))
    elif website and website != 'не указано':
        strengths.append(("📞 Контакты", "Есть сайт", "✅", 60))
    else:
        strengths.append(("📞 Контакты", "Нет", "❓", 20))
    
    # Сортируем по важности (score)
    strengths.sort(key=lambda x: x[3], reverse=True)
    
    return strengths


def _build_recommendation(supplier: Dict, strengths: List[tuple]) -> str:
    """Формирование рекомендации по поставщику"""
    parts = []
    
    # Находим топ-3 сильных стороны
    top_strengths = strengths[:3]
    
    for label, value, icon, _ in top_strengths:
        if label == "💰 Цена":
            if "Ниже рынка" in value:
                parts.append("🔝 **Лучший по цене** — это самый экономичный вариант")
            elif "Рыночная" in value:
                parts.append("💰 **Адекватная цена** — соответствует рынку")
            elif "Указана" in value:
                parts.append("💰 **Цена известна** — можно сразу оценить бюджет")
        
        elif label == "🚚 Доставка":
            if "Быстрая" in value:
                parts.append("🚀 **Быстрая доставка** — идеально для срочных заказов")
            elif "Стандартная" in value:
                parts.append("📦 **Стандартная доставка** — надежный вариант")
            elif "Есть условия" in value:
                parts.append("📦 **Доставка прописана** — условия известны заранее")
        
        elif label == "📦 Заказ":
            if "Нет ограничений" in value:
                parts.append("🆓 **Гибкий заказ** — можно заказать любой объем")
            elif "Доступный" in value:
                parts.append("👍 **Низкий порог входа** — подходит для тестовой партии")
            elif "Средний" in value:
                parts.append("📊 **Стандартный заказ** — типичные условия на рынке")
        
        elif label == "📋 Документы":
            if "сертификатов" in value:
                parts.append(f"📄 **Документы в порядке** — {value} упрощают проверку")
        
        elif label == "📍 Регион" or label == "📍 Город":
            parts.append(f"📍 **Локальный поставщик** — работа в {value}")
        
        elif label == "📞 Контакты":
            if "Есть телефон и сайт" in value:
                parts.append("📱 **Легко связаться** — все контакты доступны")
    
    if not parts:
        parts.append("ℹ️ **Требуется уточнение деталей** — свяжитесь для получения полной информации")
    
    # Добавляем контекст на основе ранга
    if strengths and strengths[0][3] > 80:
        parts.insert(0, "🏆 **Сильный кандидат** — явные преимущества перед конкурентами")
    
    return " ".join(parts)


def _generate_questions(supplier: Dict) -> List[str]:
    """Генерация вопросов для звонка поставщику"""
    questions = []
    price = supplier.get('price_range', '').lower()
    delivery = supplier.get('delivery_conditions', '').lower()
    docs = supplier.get('documents', '')
    min_order = supplier.get('min_order', '').lower()
    category = supplier.get('category', '').lower()
    
    # Базовые вопросы по цене
    if not price or price == 'не указано' or 'уточн' in price:
        questions.append("Какая точная цена за единицу товара? Есть ли оптовые скидки при объеме от 1000 единиц?")
    else:
        questions.append("Какая цена за единицу при заказе от 1000 единиц? Есть ли система скидок?")
    
    # Вопросы по доставке
    if not delivery or delivery == 'не указано' or 'уточн' in delivery:
        questions.append("Какие условия доставки: стоимость, сроки, минимальный заказ для бесплатной доставки?")
    else:
        questions.append("Какая стоимость доставки? Есть ли самовывоз?")
    
    # Вопросы по минимальному заказу
    if not min_order or min_order == 'не указано' or min_order == '':
        questions.append("Какой минимальный объем заказа? Можно ли заказать пробную партию?")
    elif 'от' in min_order:
        numbers = re.findall(r'\d+', min_order)
        if numbers and int(numbers[0]) > 5000:
            questions.append(f"Такой большой минимальный заказ ({min_order}) — можно ли договориться о меньшей партии для теста?")
    
    # Вопросы по документам
    if not docs or docs == 'не указано':
        questions.append("Какие сертификаты и документы качества у вас есть?")
    else:
        doc_list = [d.strip() for d in docs.split(';') if d.strip()]
        if len(doc_list) < 2:
            questions.append("Какие еще сертификаты качества есть помимо указанных?")
    
    # Специфические вопросы по категории
    if 'мясо' in category or 'рыб' in category:
        questions.append("Как обеспечивается свежесть и условия хранения продукции? Какой срок годности?")
    elif 'молочн' in category:
        questions.append("Какие сроки годности и условия хранения? Есть ли система контроля температуры?")
    elif 'упаковк' in category:
        questions.append("Есть ли возможность кастомизации упаковки под наш бренд?")
    elif 'овощ' in category or 'фрукт' in category:
        questions.append("Какой срок годности? Есть ли возможность закупки сезонных продуктов?")
    
    # Общие вопросы, если мало специфических
    if len(questions) < 3:
        if 'оплата' not in str(questions).lower():
            questions.append("Какие формы оплаты вы принимаете? Есть ли отсрочка платежа?")
        if 'образец' not in str(questions).lower():
            questions.append("Есть ли у вас образцы для тестирования? Какие условия предоставления образцов?")
        if 'гарант' not in str(questions).lower():
            questions.append("Предоставляете ли вы гарантию качества? Есть ли система возврата брака?")
    
    return questions


def _identify_risks(supplier: Dict) -> List[str]:
    """Выявление рисков при работе с поставщиком"""
    risks = []
    
    # Проверка наличия критической информации
    contacts = supplier.get('contacts', '')
    website = supplier.get('website', '')
    docs = supplier.get('documents', '')
    min_order = supplier.get('min_order', '').lower()
    
    if not contacts or contacts == 'не указано':
        risks.append("❌ **Нет контактов** — потребуется найти актуальный номер/email через другие источники")
    
    if not website or website == 'не указано':
        risks.append("❌ **Нет сайта** — сложно проверить надежность компании и историю работы")
    
    if not docs or docs == 'не указано':
        risks.append("⚠️ **Нет документов** — потребуется запросить сертификаты и проверить легальность продукции")
    
    # Проверка минимального заказа
    if min_order and 'от' in min_order:
        numbers = re.findall(r'\d+', min_order)
        if numbers and int(numbers[0]) > 5000:
            risks.append(f"⚠️ **Высокий минимальный заказ** ({min_order}) — может не подойти для тестовой партии")
        elif numbers and int(numbers[0]) > 10000:
            risks.append(f"⚠️ **Очень крупный заказ** ({min_order}) — серьезная финансовая нагрузка на старте")
    
    # Проверка цены
    price = supplier.get('price_range', '').lower()
    if price and 'высок' in price:
        risks.append("⚠️ **Высокая цена** — может быть неконкурентоспособной на рынке")
    elif not price or price == 'не указано':
        risks.append("❓ **Цена неизвестна** — нужно уточнить, чтобы оценить бюджет")
    
    # Проверка доставки
    delivery = supplier.get('delivery_conditions', '').lower()
    if delivery and 'нет' in delivery:
        risks.append("⚠️ **Нет доставки** — нужно будет организовать самовывоз или свою логистику")
    elif not delivery or delivery == 'не указано':
        risks.append("❓ **Условия доставки неизвестны** — нужно уточнить")
    
    return risks


def _determine_best_use_case(supplier: Dict, strengths: List[tuple]) -> str:
    """Определение лучшего сценария использования поставщика"""
    use_cases = []
    
    # Проверяем сильные стороны
    for label, value, _, score in strengths:
        if label == "💰 Цена" and "Ниже рынка" in value and score > 80:
            use_cases.append("🔸 **Для регулярных закупок** — экономия на масштабе")
        
        if label == "📦 Заказ" and "Нет ограничений" in value:
            use_cases.append("🔸 **Для тестовых партий** — можно заказать немного")
        elif label == "📦 Заказ" and "Доступный" in value:
            use_cases.append("🔸 **Для пробных закупок** — невысокий порог входа")
        
        if label == "🚚 Доставка" and "Быстрая" in value:
            use_cases.append("🔸 **Для срочных заказов** — быстрая поставка")
        
        if label == "📍 Регион" and score > 60:
            use_cases.append(f"🔸 **Для локальных закупок** — поставщик в вашем регионе")
    
    if not use_cases:
        use_cases.append("🔸 **Для уточнения** — свяжитесь для получения деталей и оценки")
    
    return " ".join(use_cases[:2])


def get_comparison_insights(suppliers: List[Dict]) -> Dict:
    """
    Анализ сравнения нескольких поставщиков
    
    Args:
        suppliers: Список поставщиков для сравнения
    
    Returns:
        Dict с результатами сравнения и рекомендациями
    """
    if len(suppliers) < 2:
        return {'error': 'Нужно минимум 2 поставщика для сравнения'}
    
    # Находим лучшего по каждому критерию
    best_by_price = min(suppliers, key=lambda x: 
                       _extract_numeric_value(x.get('price_range', '999999'), 'price'))
    
    best_by_delivery = min(suppliers, key=lambda x: 
                          _extract_numeric_value(x.get('delivery_conditions', '30'), 'days'))
    
    best_by_min_order = min(suppliers, key=lambda x: 
                           _extract_numeric_value(x.get('min_order', '999999'), 'order'))
    
    # Общий победитель
    winner = max(suppliers, key=lambda x: x.get('total_score', 0))
    
    return {
        'best_price': best_by_price,
        'best_delivery': best_by_delivery,
        'best_min_order': best_by_min_order,
        'winner': winner,
        'total_count': len(suppliers)
    }


def _extract_numeric_value(value: str, field_type: str) -> int:
    """Извлечение числового значения из строки"""
    if not value or value == 'не указано':
        if field_type == 'price':
            return 999999
        elif field_type == 'days':
            return 30
        elif field_type == 'order':
            return 999999
    
    numbers = re.findall(r'\d+', str(value))
    if numbers:
        return int(numbers[0])
    
    if field_type == 'price':
        return 999999
    elif field_type == 'days':
        return 30
    elif field_type == 'order':
        return 999999
