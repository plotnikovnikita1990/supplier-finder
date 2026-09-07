import streamlit as st
import pandas as pd

# Импорты с диагностикой
try:
    from src.data import load_data
    print("✅ data.py загружен успешно")
except ImportError as e:
    st.error(f"❌ Ошибка импорта data.py: {e}")
    st.stop()

try:
    from src.search import search_suppliers
    print("✅ search.py загружен успешно")
except ImportError as e:
    st.error(f"❌ Ошибка импорта search.py: {e}")
    st.stop()

try:
    from src.insights import generate_supplier_insights
    print("✅ insights.py загружен успешно")
except ImportError as e:
    st.warning(f"⚠️ Модуль insights не загружен: {e}")
    def generate_supplier_insights(supplier, query="", rank=1):
        return {
            'strengths': [],
            'recommendation_reason': "Модуль анализа недоступен",
            'questions_to_ask': ["Уточните детали сотрудничества"],
            'risks': [],
            'best_use_case': "Требуется ручной анализ"
        }


def display_supplier_card(supplier, rank, query=""):
    """Отображение карточки поставщика с аналитикой"""
    with st.container():
        # Заголовок
        if rank <= 3:
            st.markdown(f"### 🏆 {rank}. {supplier.get('name', 'Без названия')}")
        else:
            st.markdown(f"### {rank}. {supplier.get('name', 'Без названия')}")
        
        # Основная информация
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**🏷️ Категория:** {supplier.get('category', '-')}")
            st.markdown(f"**📍 Город:** {supplier.get('city', '-')}")
            if supplier.get('region'):
                st.markdown(f"**🌍 Регион:** {supplier['region']}")
        with col2:
            st.markdown(f"**💰 Цена:** {supplier.get('price_range', 'не указано')}")
            st.markdown(f"**📦 Мин. заказ:** {supplier.get('min_order', 'не указано')}")
            st.markdown(f"**🚚 Доставка:** {supplier.get('delivery_conditions', 'не указано')}")
        with col3:
            st.markdown(f"**📞 Контакты:** {supplier.get('contacts', 'не указано')}")
            if supplier.get('website'):
                st.markdown(f"**🌐 Сайт:** {supplier['website']}")
            if 'total_score' in supplier:
                st.markdown(f"**⭐ Рейтинг:** {supplier['total_score']:.2f}")
        
        # Документы
        docs = supplier.get('documents', '')
        if docs and docs != 'не указано':
            doc_list = [d.strip() for d in docs.split(';') if d.strip()]
            if doc_list:
                st.markdown(f"**📋 Документы:** {', '.join(doc_list)}")
        
        # Анализ
        with st.expander("🧠 Анализ поставщика", expanded=(rank <= 3)):
            try:
                insights = generate_supplier_insights(supplier, query, rank)
                
                # Сильные стороны
                if insights.get('strengths'):
                    st.markdown("#### 📊 Сильные стороны")
                    for label, value, icon, _ in insights['strengths'][:4]:
                        st.write(f"{icon} **{label}:** {value}")
                
                # Рекомендация
                st.markdown("#### 💡 Почему стоит связаться")
                st.info(insights.get('recommendation_reason', 'Информация недоступна'))
                
                # Вопросы
                if insights.get('questions_to_ask'):
                    st.markdown("#### 📋 Что уточнить при звонке")
                    for i, question in enumerate(insights['questions_to_ask'][:3], 1):
                        st.write(f"{i}. {question}")
                
                # Риски
                if insights.get('risks'):
                    st.markdown("#### ⚠️ На что обратить внимание")
                    for risk in insights['risks'][:3]:
                        st.warning(risk)
                        
            except Exception as e:
                st.error(f"Ошибка при генерации анализа: {e}")
        
        st.divider()


def main():
    st.set_page_config(
        page_title="Food Supplier Finder",
        page_icon="🍽️",
        layout="wide"
    )
    
    st.title("🍽️ Поиск поставщиков продуктов питания")
    st.caption("Найдите лучших поставщиков с интеллектуальным анализом")
    
    # Загрузка данных
    with st.spinner("Загрузка данных..."):
        try:
            df = load_data()
            st.success(f"✅ Загружено {len(df)} поставщиков")
        except Exception as e:
            st.error(f"❌ Ошибка загрузки данных: {e}")
            st.write("Детали ошибки:", str(e))
            return
    
    # Поисковая форма
    with st.form(key='search_form'):
        query = st.text_input(
            "🔍 Что ищете?", 
            placeholder="Например: куриное филе, молоко, упаковка...",
            value=st.session_state.get('last_query', '')
        )
        
        col1, col2 = st.columns(2)
        with col1:
            categories = ["Все"] + sorted(df['category'].unique().tolist())
            category_filter = st.selectbox("🏷️ Категория", categories)
        with col2:
            cities = ["Все"] + sorted(df['city'].unique().tolist())
            city_filter = st.selectbox("📍 Город", cities)
        
        submitted = st.form_submit_button("🔍 Найти", type="primary")
    
    # Обработка поиска
    if submitted and query:
        st.session_state['last_query'] = query
        
        with st.spinner("🔍 Ищем поставщиков..."):
            try:
                results = search_suppliers(query, df, category_filter, city_filter)
            except Exception as e:
                st.error(f"❌ Ошибка поиска: {e}")
                st.write("Детали ошибки:", str(e))
                return
        
        if not results:
            st.warning("❌ Поставщики не найдены. Попробуйте изменить запрос.")
            return
        
        st.success(f"✅ Найдено **{len(results)}** поставщиков")
        
        # Рекомендуемый поставщик
        if results:
            best = results[0]
            with st.container():
                st.markdown("---")
                st.markdown("## 🏆 Лучший вариант для звонка")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {best.get('name', 'Без названия')}")
                    st.markdown(f"**Рейтинг:** {best.get('total_score', 0):.2f}")
                    st.markdown(f"**Категория:** {best.get('category', '-')} | **Город:** {best.get('city', '-')}")
                    
                    try:
                        insights = generate_supplier_insights(best, query, 1)
                        st.info(f"💡 {insights.get('recommendation_reason', 'Информация недоступна')}")
                    except:
                        st.info("💡 Рекомендуемый поставщик — свяжитесь для уточнения деталей")
                    
                with col2:
                    if st.button("📞 Связаться", type="primary"):
                        st.success(f"Контакт: {best.get('contacts', 'контакты не указаны')}")
            
            st.markdown("---")
        
        # Все поставщики
        st.subheader("📋 Все поставщики")
        
        # Пагинация
        per_page = 10
        total_pages = (len(results) + per_page - 1) // per_page
        
        if total_pages > 1:
            page = st.selectbox("Страница", range(1, total_pages + 1))
            start = (page - 1) * per_page
            end = min(start + per_page, len(results))
            page_results = results[start:end]
        else:
            page_results = results[:per_page]
        
        for idx, supplier in enumerate(page_results, 1):
            display_supplier_card(supplier, idx, query)


if __name__ == "__main__":
    main()
