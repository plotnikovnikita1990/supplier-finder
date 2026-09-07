import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Добавляем текущую папку в путь поиска модулей
sys.path.insert(0, str(Path(__file__).parent))

# Пытаемся импортировать с подробной диагностикой
try:
    from src.data import load_data
    print("✅ data.py загружен")
except ImportError as e:
    st.error(f"❌ Ошибка импорта data.py: {e}")
    st.write("Проверьте, что файл src/data.py существует и в папке src есть __init__.py")
    st.stop()

try:
    from src.search import search_suppliers, compare_suppliers
    print("✅ search.py загружен")
except ImportError as e:
    st.error(f"❌ Ошибка импорта search.py: {e}")
    st.stop()

try:
    from src.insights import generate_supplier_insights
    print("✅ insights.py загружен")
except ImportError as e:
    st.warning(f"⚠️ Модуль insights не загружен: {e}")
    # Создаем заглушку
    def generate_supplier_insights(supplier, query="", rank=1):
        return {
            'strengths': [],
            'recommendation_reason': "Модуль анализа не загружен. Проверьте файл src/insights.py",
            'questions_to_ask': ["Уточните детали сотрудничества"],
            'risks': ["Нет данных для анализа"],
            'best_use_case': "Требуется ручной анализ"
        }


def display_supplier_card(supplier, rank, query=""):
    """Отображение карточки поставщика"""
    with st.container():
        if rank <= 3:
            st.markdown(f"### 🏆 {rank}. {supplier.get('name', 'Без названия')}")
        else:
            st.markdown(f"### {rank}. {supplier.get('name', 'Без названия')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Категория:** {supplier.get('category', '-')}")
            st.markdown(f"**Город:** {supplier.get('city', '-')}")
            st.markdown(f"**Цена:** {supplier.get('price_range', 'не указано')}")
        with col2:
            st.markdown(f"**Мин. заказ:** {supplier.get('min_order', 'не указано')}")
            st.markdown(f"**Доставка:** {supplier.get('delivery_conditions', 'не указано')}")
            st.markdown(f"**Контакты:** {supplier.get('contacts', 'не указано')}")
        
        if 'total_score' in supplier:
            st.markdown(f"**Рейтинг:** {supplier['total_score']:.2f}")
        
        # Анализ
        with st.expander("🧠 Анализ поставщика", expanded=(rank <= 3)):
            try:
                insights = generate_supplier_insights(supplier, query, rank)
                
                if insights.get('strengths'):
                    st.markdown("**Сильные стороны:**")
                    for label, value, icon, _ in insights['strengths'][:4]:
                        st.write(f"{icon} {label}: {value}")
                
                st.info(f"💡 {insights.get('recommendation_reason', 'Нет рекомендаций')}")
                
                if insights.get('questions_to_ask'):
                    st.markdown("**Вопросы для звонка:**")
                    for q in insights['questions_to_ask'][:3]:
                        st.write(f"• {q}")
                
                if insights.get('risks'):
                    st.markdown("**⚠️ Риски:**")
                    for risk in insights['risks'][:3]:
                        st.warning(risk)
                        
            except Exception as e:
                st.error(f"Ошибка анализа: {e}")
        
        st.divider()


def main():
    st.set_page_config(page_title="Food Supplier Finder", layout="wide")
    st.title("🍽️ Поиск поставщиков продуктов питания")
    st.caption("Найдите лучших поставщиков с интеллектуальным анализом")
    
    # Загрузка данных
    with st.spinner("Загрузка данных..."):
        try:
            df = load_data()
            st.success(f"✅ Загружено {len(df)} поставщиков")
        except Exception as e:
            st.error(f"❌ Ошибка загрузки данных: {e}")
            return
    
    # Поиск
    with st.form(key='search_form'):
        query = st.text_input("🔍 Что ищете?", placeholder="Например: куриное филе, молоко...")
        col1, col2 = st.columns(2)
        with col1:
            categories = ["Все"] + sorted(df['category'].unique().tolist())
            category_filter = st.selectbox("Категория", categories)
        with col2:
            cities = ["Все"] + sorted(df['city'].unique().tolist())
            city_filter = st.selectbox("Город", cities)
        submitted = st.form_submit_button("🔍 Найти", type="primary")
    
    if submitted and query:
        with st.spinner("Ищем..."):
            try:
                results = search_suppliers(query, df, category_filter, city_filter)
            except Exception as e:
                st.error(f"Ошибка поиска: {e}")
                return
        
        if not results:
            st.warning("Поставщики не найдены.")
            return
        
        st.success(f"Найдено {len(results)} поставщиков")
        
        # Лучший вариант
        if results:
            best = results[0]
            st.markdown("---")
            st.markdown(f"## 🏆 Лучший вариант: {best.get('name', 'Без названия')}")
            st.markdown(f"**Рейтинг:** {best.get('total_score', 0):.2f}")
            if st.button("📞 Связаться с этим поставщиком", type="primary"):
                st.success(f"Контакт: {best.get('contacts', 'не указаны')}")
            st.markdown("---")
        
        # Список
        st.subheader("📋 Все поставщики")
        for idx, supplier in enumerate(results[:10], 1):
            display_supplier_card(supplier, idx, query)


if __name__ == "__main__":
    main()
