import streamlit as st
import pandas as pd
from src.data import load_data
from src.search import search_suppliers, compare_suppliers
from src.insights import generate_supplier_insights


def display_supplier_card(supplier, rank, query=""):
    """Отображение карточки поставщика с аналитикой"""
    
    with st.container():
        # Заголовок
        if rank <= 3:
            st.markdown(f"### 🏆 {rank}. {supplier.get('name', 'Без названия')} (Рекомендуемый)")
        else:
            st.markdown(f"### {rank}. {supplier.get('name', 'Без названия')}")
        
        # Основная информация
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**🏷️ Категория:** {supplier.get('category', '-')}")
            st.markdown(f"**📍 Город:** {supplier.get('city', '-')}")
            if supplier.get('region'):
                st.markdown(f"**🌍 Регион:** {supplier['region']}")
        with col2:
            st.markdown(f"**💰 Цена:** {supplier.get('price_range', 'не указано')}")
            st.markdown(f"**📦 Мин. заказ:** {supplier.get('min_order', 'не указано')}")
            st.markdown(f"**🚚 Доставка:** {supplier.get('delivery_conditions', 'не указано')}")
        
        # Контакты
        st.markdown(f"**📞 Контакты:** {supplier.get('contacts', 'не указано')}")
        if supplier.get('website'):
            st.markdown(f"**🌐 Сайт:** {supplier['website']}")
        
        # Документы
        if supplier.get('documents') and supplier['documents'] != 'не указано':
            docs = [d.strip() for d in supplier['documents'].split(';') if d.strip()]
            st.markdown(f"**📋 Документы:** {', '.join(docs)}")
        
        # Рейтинг
        if 'total_score' in supplier:
            st.markdown(f"**⭐ Рейтинг:** {supplier['total_score']:.2f}")
        
        # Анализ поставщика (НОВОЕ!)
        with st.expander("🧠 Анализ поставщика", expanded=(rank <= 3)):
            try:
                insights = generate_supplier_insights(supplier, query, rank)
                
                # Лучший сценарий
                st.info(f"💡 **Идеально подходит для:** {insights.get('best_use_case', 'Уточните')}")
                
                # Сильные стороны
                if insights.get('strengths'):
                    st.markdown("**📊 Сильные стороны:**")
                    for label, value, icon, _ in insights['strengths'][:4]:
                        st.write(f"{icon} **{label}:** {value}")
                
                # Рекомендация
                st.markdown("**💡 Почему стоит связаться:**")
                st.info(insights.get('recommendation_reason', 'Информация недоступна'))
                
                # Вопросы
                if insights.get('questions_to_ask'):
                    st.markdown("**📋 Что уточнить при звонке:**")
                    for i, question in enumerate(insights['questions_to_ask'][:3], 1):
                        st.write(f"{i}. {question}")
                
                # Риски
                if insights.get('risks'):
                    st.markdown("**⚠️ На что обратить внимание:**")
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
    st.caption("Найдите лучших поставщиков с интеллектуальным анализом и рекомендациями")
    
    # Загрузка данных
    with st.spinner("Загрузка данных..."):
        try:
            df = load_data()
            st.success(f"✅ Загружено {len(df)} поставщиков")
        except Exception as e:
            st.error(f"❌ Ошибка загрузки данных: {e}")
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
        
        # Список поставщиков
        st.subheader("📋 Все поставщики")
        
        selected_for_comparison = []
        
        for idx, supplier in enumerate(results[:10], 1):
            display_supplier_card(supplier, idx, query)
            
            if st.checkbox(f"➕ Сравнить", key=f"compare_{idx}"):
                selected_for_comparison.append(supplier)
        
        # Сравнение
        if selected_for_comparison:
            st.markdown("---")
            st.subheader("📊 Сравнение выбранных поставщиков")
            
            comparison = compare_suppliers(selected_for_comparison)
            st.dataframe(comparison, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
