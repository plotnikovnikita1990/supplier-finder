import streamlit as st
import pandas as pd
from src.data import load_data
from src.search import search_suppliers, compare_suppliers
from src.insights import generate_supplier_insights, get_comparison_insights


def display_supplier_card_with_insights(supplier, rank, total_suppliers, query=""):
    """Отображение карточки поставщика с аналитикой и рекомендациями"""
    
    with st.container():
        # Заголовок с рейтингом
        if rank <= 3:
            st.markdown(f"### 🏆 {rank}. {supplier['name']} (Рекомендуемый)")
        else:
            st.markdown(f"### {rank}. {supplier['name']}")
        
        # Основная информация в колонках
        col1, col2, col3 = st.columns([2, 1, 1])
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
            if 'total_score' in supplier:
                st.markdown(f"**⭐ Рейтинг:** {supplier['total_score']:.2f}")
            st.markdown(f"**📞 Контакты:** {supplier.get('contacts', 'не указано')}")
            if supplier.get('website'):
                st.markdown(f"**🌐 Сайт:** {supplier['website']}")
        
        # Документы
        if supplier.get('documents') and supplier['documents'] != 'не указано':
            docs = [d.strip() for d in supplier['documents'].split(';') if d.strip()]
            st.markdown(f"**📋 Документы:** {', '.join(docs)}")
        
        # Интеллектуальный анализ
        with st.expander("🧠 Анализ поставщика", expanded=(rank <= 3)):
            insights = generate_supplier_insights(supplier, query, rank)
            
            # Лучший сценарий использования
            st.info(f"💡 **Идеально подходит для:** {insights['best_use_case']}")
            
            # Визуализация сильных сторон
            st.markdown("#### 📊 Сильные стороны")
            cols = st.columns(min(len(insights['strengths']), 4))
            for i, (label, value, icon, _) in enumerate(insights['strengths'][:4]):
                with cols[i % len(cols)]:
                    st.metric(label, value, delta=icon)
            
            # Рекомендация
            st.markdown("#### 💡 Почему стоит связаться")
            st.info(insights['recommendation_reason'])
            
            # Вопросы для поставщика
            st.markdown("#### 📋 Что уточнить при звонке")
            for i, question in enumerate(insights['questions_to_ask'][:3], 1):
                st.write(f"{i}. {question}")
            
            # Риски
            if insights['risks']:
                st.markdown("#### ⚠️ На что обратить внимание")
                for risk in insights['risks']:
                    st.warning(risk)
            
            # Кнопка для экспорта отчета
            if st.button(f"📥 Скачать отчет по {supplier['name']}", key=f"report_{rank}"):
                report_text = f"""
📋 ОТЧЕТ ПО ПОСТАВЩИКУ
=====================

Название: {supplier['name']}
Категория: {supplier.get('category', '-')}
Город: {supplier.get('city', '-')}
Регион: {supplier.get('region', '-')}

📊 СИЛЬНЫЕ СТОРОНЫ:
{chr(10).join([f"- {label}: {value}" for label, value, _, _ in insights['strengths'][:5]])}

💡 РЕКОМЕНДАЦИЯ:
{insights['recommendation_reason']}

📋 ВОПРОСЫ ДЛЯ ЗВОНКА:
{chr(10).join([f"- {q}" for q in insights['questions_to_ask']])}

⚠️ РИСКИ:
{chr(10).join([f"- {r}" for r in insights['risks']]) if insights['risks'] else "- Нет явных рисков"}

🏆 ЛУЧШИЙ СЦЕНАРИЙ:
{insights['best_use_case']}

КОНТАКТЫ:
Телефон: {supplier.get('contacts', 'не указаны')}
Сайт: {supplier.get('website', 'не указан')}

Дата: {pd.Timestamp.now().strftime('%d.%m.%Y')}
"""
                st.download_button(
                    label="⬇️ Скачать",
                    data=report_text,
                    file_name=f"отчет_{supplier['name']}.txt",
                    mime="text/plain",
                    key=f"download_{rank}"
                )
        
        st.divider()


def show_comparison_with_insights(selected_suppliers):
    """Расширенное сравнение поставщиков с аналитикой"""
    
    if len(selected_suppliers) < 2:
        st.warning("Выберите минимум 2 поставщика для сравнения")
        return
    
    st.subheader("📊 Сравнение поставщиков")
    
    # Создаем DataFrame для сравнения
    comparison_data = []
    for supplier in selected_suppliers:
        row = {
            'Название': supplier['name'],
            'Категория': supplier.get('category', '-'),
            'Город': supplier.get('city', '-'),
            'Цена': supplier.get('price_range', '-'),
            'Мин. заказ': supplier.get('min_order', '-'),
            'Доставка': supplier.get('delivery_conditions', '-'),
            'Документы': supplier.get('documents', '-'),
            'Контакты': supplier.get('contacts', '-'),
            'Рейтинг': supplier.get('total_score', 0)
        }
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    
    # Отображаем таблицу
    st.dataframe(
        df,
        column_config={
            "Рейтинг": st.column_config.NumberColumn("Рейтинг", format="%.2f"),
            "Цена": st.column_config.TextColumn("Цена"),
            "Мин. заказ": st.column_config.TextColumn("Мин. заказ"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Анализ сравнения
    st.subheader("🧠 Рекомендация по выбору")
    
    comparison = get_comparison_insights(selected_suppliers)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"💰 **Лучшая цена:**\n{comparison['best_price']['name']}")
        st.caption(f"Цена: {comparison['best_price'].get('price_range', '-')}")
    with col2:
        st.success(f"🚚 **Быстрая доставка:**\n{comparison['best_delivery']['name']}")
        st.caption(f"Условия: {comparison['best_delivery'].get('delivery_conditions', '-')}")
    with col3:
        st.success(f"📦 **Минимальный заказ:**\n{comparison['best_min_order']['name']}")
        st.caption(f"Заказ: {comparison['best_min_order'].get('min_order', '-')}")
    
    st.markdown("---")
    
    # Общая рекомендация
    winner = comparison['winner']
    winner_insights = generate_supplier_insights(winner, "", 1)
    
    st.markdown(f"""
    ### 🏆 Лучший выбор для звонка: **{winner['name']}**
    
    **Почему:**
    {winner_insights['recommendation_reason']}
    
    **Лучший сценарий:**
    {winner_insights['best_use_case']}
    
    **Что спросить в первую очередь:**
    {winner_insights['questions_to_ask'][0] if winner_insights['questions_to_ask'] else 'Уточните детали сотрудничества'}
    """)
    
    # Кнопка для быстрого действия
    if st.button("📞 Позвонить этому поставщику", type="primary"):
        st.success(f"📱 Контакт: {winner.get('contacts', 'контакты не указаны')}")
        if winner.get('website'):
            st.info(f"🌐 Сайт: {winner['website']}")


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
        df = load_data()
    
    # Поисковая форма
    with st.form(key='search_form'):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "🔍 Что ищете?", 
                placeholder="Например: куриное филе, молоко, упаковка для пиццы...",
                value=st.session_state.get('last_query', '')
            )
        with col2:
            st.write("")  # Отступ
            submitted = st.form_submit_button("🔍 Найти", type="primary")
        
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            categories = ["Все"] + sorted(df['category'].unique().tolist())
            category_filter = st.selectbox("🏷️ Категория", categories)
        with col2:
            cities = ["Все"] + sorted(df['city'].unique().tolist())
            city_filter = st.selectbox("📍 Город", cities)
    
    # Обработка поиска
    if submitted and query:
        st.session_state['last_query'] = query
        
        # Поиск
        with st.spinner("🔍 Ищем поставщиков..."):
            results = search_suppliers(query, df, category_filter, city_filter)
        
        if not results:
            st.warning("❌ Поставщики не найдены. Попробуйте изменить запрос или снять фильтры.")
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
                    st.markdown(f"### {best['name']}")
                    st.markdown(f"**Рейтинг:** {best.get('total_score', 0):.2f}")
                    st.markdown(f"**Категория:** {best.get('category', '-')} | **Город:** {best.get('city', '-')}")
                    
                    insights = generate_supplier_insights(best, query, 1)
                    st.info(f"💡 {insights['recommendation_reason']}")
                with col2:
                    st.markdown("### 📞")
                    if st.button("📞 Связаться", type="primary"):
                        st.success(f"Контакт: {best.get('contacts', 'контакты не указаны')}")
                        if best.get('website'):
                            st.info(f"🌐 {best['website']}")
            
            st.markdown("---")
        
        # Все поставщики с аналитикой
        st.subheader("📋 Все поставщики")
        st.caption("Изучите детальную информацию о каждом поставщике")
        
        # Чекбоксы для сравнения
        selected_for_comparison = []
        
        # Пагинация
        suppliers_per_page = 10
        total_pages = (len(results) + suppliers_per_page - 1) // suppliers_per_page
        
        if total_pages > 1:
            page = st.selectbox("Страница", range(1, total_pages + 1), key="page_selector")
            start_idx = (page - 1) * suppliers_per_page
            end_idx = min(start_idx + suppliers_per_page, len(results))
            page_results = results[start_idx:end_idx]
        else:
            page_results = results
        
        for idx, supplier in enumerate(page_results, start=1):
            # Показываем карточку с инсайтами
            current_rank = idx + (page - 1) * suppliers_per_page if total_pages > 1 else idx
            display_supplier_card_with_insights(
                supplier, 
                current_rank,
                len(results),
                query
            )
            
            # Чекбокс для сравнения
            if st.checkbox(f"➕ Сравнить", key=f"compare_{supplier.get('id', idx)}"):
                selected_for_comparison.append(supplier)
        
        # Сравнение выбранных
        if selected_for_comparison:
            st.markdown("---")
            show_comparison_with_insights(selected_for_comparison)


if __name__ == "__main__":
    main()
