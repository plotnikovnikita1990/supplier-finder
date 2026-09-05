import streamlit as st
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
import os

# Исправление сети: зеркало Hugging Face
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

st.set_page_config(page_title="AI Поиск поставщиков", layout="wide", page_icon="🍽️")

# ==============================
# ЗАГОЛОВОК
# ==============================
st.title("🍽️ AI-Сервис поиска поставщиков продуктов питания")
st.markdown("""
    <div style="background-color: #1e293b; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
        <b>🤖 Как это работает:</b> Система понимает <b>смысл</b> вашего запроса, а не просто ищет слова.
        Введите запрос на естественном языке — например, <i>«молочная продукция с сертификатом»</i>.
    </div>
""", unsafe_allow_html=True)

# ==============================
# 1. ЗАГРУЗКА МОДЕЛИ
# ==============================
@st.cache_resource
def load_embedding_model():
    with st.spinner("⏳ Загрузка AI-модели для семантического поиска..."):
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        st.toast("⏳ Первая загрузка может занять 3–5 минут. Следующие запуски — моментальные.", icon="⏳")
        return SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

model = load_embedding_model()

# ==============================
# 2. ЗАГРУЗКА ДАННЫХ
# ==============================
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return None

st.sidebar.header("📂 Источник данных")
uploaded_file = st.sidebar.file_uploader("Загрузить свой CSV", type=["csv"])

if uploaded_file:
    df = load_data(uploaded_file)
else:
    if os.path.exists("suppliers.csv"):
        df = load_data("suppliers.csv")
    else:
        st.info("📂 Загрузите CSV-файл с поставщиками")
        st.stop()

if df is None:
    st.stop()

st.sidebar.success(f"✅ Загружено {len(df)} поставщиков")

# ==============================
# 3. ПОДГОТОВКА КОЛОНОК
# ==============================
required_cols = ["name", "category", "region", "contact", "phone", "email", "website",
                 "min_order", "price", "delivery_terms", "documents", "rating", "notes"]
for col in required_cols:
    if col not in df.columns:
        df[col] = ""
df = df.fillna("")

# ==============================
# 4. ВЫЧИСЛЕНИЕ ЭМБЕДДИНГОВ
# ==============================
@st.cache_data
def compute_embeddings(dataframe):
    texts = (dataframe['name'] + " " + dataframe['category'] + " " + dataframe['notes']).tolist()
    with st.spinner("🧠 Индексация поставщиков..."):
        return model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

supplier_embeddings = compute_embeddings(df)

# ==============================
# 5. БОКОВАЯ ПАНЕЛЬ: ВЕСА 1–10
# ==============================
st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ Важность критериев (1–10)")
st.sidebar.caption("""
**Как это работает:**  
Каждый критерий получает вес от 1 до 10.  
Система автоматически пересчитывает их в проценты.  
Чем выше вес, тем больше критерий влияет на итоговую оценку поставщика.
""")

# Инициализация весов
if 'weights' not in st.session_state:
    st.session_state.weights = {
        'docs': 8,
        'price': 7,
        'min_order': 6,
        'delivery': 8,
        'region': 5,
        'rating': 6
    }

def reset_weights():
    st.session_state.weights = {
        'docs': 8,
        'price': 7,
        'min_order': 6,
        'delivery': 8,
        'region': 5,
        'rating': 6
    }

def reset_all_filters():
    st.session_state['search_term'] = ""
    st.session_state['selected_cat'] = "Все"
    st.session_state['selected_region'] = "Все"
    reset_weights()
    if 'results' in st.session_state:
        del st.session_state['results']

# Слайдеры
docs_w = st.sidebar.slider("📜 Сертификаты / документы", 1, 10, st.session_state.weights['docs'], 
                           help="Наличие сертификатов повышает доверие к поставщику")
price_w = st.sidebar.slider("💰 Низкая цена", 1, 10, st.session_state.weights['price'],
                            help="Чем ниже цена, тем больше баллов получает поставщик")
min_order_w = st.sidebar.slider("📦 Маленький минимальный заказ", 1, 10, st.session_state.weights['min_order'],
                                 help="Меньший минимальный заказ удобен для пробной партии")
delivery_w = st.sidebar.slider("🚚 Выгодная доставка", 1, 10, st.session_state.weights['delivery'],
                               help="Бесплатная или недорогая доставка — важный фактор")
region_w = st.sidebar.slider("📍 Поставщик в моём регионе", 1, 10, st.session_state.weights['region'],
                             help="Близость поставщика упрощает логистику")
rating_w = st.sidebar.slider("⭐ Высокий рейтинг", 1, 10, st.session_state.weights['rating'],
                             help="Высокий рейтинг говорит о надёжности")

st.session_state.weights = {
    'docs': docs_w,
    'price': price_w,
    'min_order': min_order_w,
    'delivery': delivery_w,
    'region': region_w,
    'rating': rating_w
}

# Показываем текущее распределение весов
st.sidebar.markdown("---")
st.sidebar.caption("📊 **Текущее влияние критериев:**")
norm = get_normalized_weights() if 'get_normalized_weights' in dir() else {}
for key, name in [('docs', 'Сертификаты'), ('price', 'Цена'), ('min_order', 'Мин. заказ'),
                  ('delivery', 'Доставка'), ('region', 'Регион'), ('rating', 'Рейтинг')]:
    if key in norm:
        st.sidebar.text(f"{name}: {norm[key]:.0f}%")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("🔄 Сбросить веса"):
        reset_weights()
        st.rerun()
with col2:
    if st.sidebar.button("🗑️ Сбросить всё"):
        reset_all_filters()
        st.rerun()

# ==============================
# 6. ФИЛЬТРЫ И ПОИСК
# ==============================
st.sidebar.markdown("---")
st.sidebar.header("🔍 Фильтры и Поиск")

# Примеры запросов
st.sidebar.markdown("**📌 Примеры запросов (кликните):**")
example_cols = st.sidebar.columns(2)
with example_cols[0]:
    if st.button("🍼 Молочка с сертификатом", use_container_width=True):
        st.session_state['search_example'] = "молочная продукция с сертификатом"
        st.rerun()
    if st.button("📦 Упаковка для продуктов", use_container_width=True):
        st.session_state['search_example'] = "упаковка для пищевых продуктов"
        st.rerun()
with example_cols[1]:
    if st.button("🌾 Ингредиенты для выпечки", use_container_width=True):
        st.session_state['search_example'] = "ингредиенты для выпечки"
        st.rerun()
    if st.button("🥩 Мясо оптом", use_container_width=True):
        st.session_state['search_example'] = "мясо оптом с доставкой"
        st.rerun()

# Поле ввода запроса
if 'search_example' in st.session_state:
    default_search = st.session_state['search_example']
    del st.session_state['search_example']
else:
    default_search = ""

search_term = st.sidebar.text_input("🧠 Семантический поиск", value=default_search,
                                    help="Введите запрос на русском языке. Система поймёт смысл, а не просто ищет слова.")

categories = ["Все"] + sorted(df["category"].dropna().unique().tolist())
if 'selected_cat' not in st.session_state:
    st.session_state['selected_cat'] = "Все"
selected_cat = st.sidebar.selectbox("Категория", categories, index=categories.index(st.session_state['selected_cat']))
st.session_state['selected_cat'] = selected_cat

regions = ["Все"] + sorted(df["region"].dropna().unique().tolist())
if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = "Все"
selected_region = st.sidebar.selectbox("Регион", regions, index=regions.index(st.session_state['selected_region']))
st.session_state['selected_region'] = selected_region

search_clicked = st.sidebar.button("🚀 Найти и ранжировать", type="primary", use_container_width=True)

# ==============================
# 7. ФУНКЦИИ РАСЧЁТА
# ==============================
def get_normalized_weights():
    w = st.session_state.weights
    total = sum(w.values())
    if total == 0:
        return {k: 0 for k in w}
    return {k: v / total * 100 for k, v in w.items()}

def calculate_supplier_rating(row, target_region, norm):
    score = 0.0
    if str(row["documents"]).strip():
        score += norm['docs']
    try:
        price = float(str(row["price"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (price / 10000.0)))
        score += norm['price'] * factor
    except:
        pass
    try:
        mo = float(str(row["min_order"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (mo / 5000.0)))
        score += norm['min_order'] * factor
    except:
        pass
    delivery = str(row["delivery_terms"]).lower()
    if "бесплатно" in delivery:
        score += norm['delivery']
    elif delivery.strip():
        score += norm['delivery'] * 0.6
    if target_region != "Все" and str(row["region"]).strip() == target_region:
        score += norm['region']
    try:
        r = float(str(row["rating"]).replace(',', '.'))
        r_norm = r / 2.0 if r > 5.0 else r
        score += norm['rating'] * (r_norm / 5.0)
    except:
        pass
    return round(min(score, 100), 1)

def explain_score(row, target_region, norm):
    explanations = []
    total = 0.0
    if str(row["documents"]).strip():
        total += norm['docs']
        explanations.append(f"✅ Есть сертификаты/документы (+{norm['docs']:.1f})")
    try:
        price = float(str(row["price"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (price / 10000.0)))
        pts = norm['price'] * factor
        if pts > 0:
            total += pts
            explanations.append(f"💰 Цена (ниже = лучше) +{pts:.1f}")
    except:
        pass
    try:
        mo = float(str(row["min_order"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (mo / 5000.0)))
        pts = norm['min_order'] * factor
        if pts > 0:
            total += pts
            explanations.append(f"📦 Мин. заказ (чем меньше, тем лучше) +{pts:.1f}")
    except:
        pass
    delivery = str(row["delivery_terms"]).lower()
    if "бесплатно" in delivery:
        total += norm['delivery']
        explanations.append(f"🚚 Бесплатная доставка (+{norm['delivery']:.1f})")
    elif delivery.strip():
        pts = norm['delivery'] * 0.6
        total += pts
        explanations.append(f"🚚 Есть условия доставки (+{pts:.1f})")
    if target_region != "Все" and str(row["region"]).strip() == target_region:
        total += norm['region']
        explanations.append(f"📍 Совпадает регион (+{norm['region']:.1f})")
    try:
        r = float(str(row["rating"]).replace(',', '.'))
        r_norm = r / 2.0 if r > 5.0 else r
        pts = norm['rating'] * (r_norm / 5.0)
        if pts > 0:
            total += pts
            explanations.append(f"⭐ Рейтинг {r}/5 (+{pts:.1f})")
    except:
        pass
    return total, explanations

def generate_recommendation(row):
    has_docs = bool(str(row["documents"]).strip())
    try:
        rating = float(str(row["rating"]).replace(',', '.'))
        rating_norm = rating / 2.0 if rating > 5.0 else rating
    except:
        rating_norm = 0
    try:
        min_order = float(str(row["min_order"]).replace(',', '.'))
    except:
        min_order = float('inf')
    delivery = str(row["delivery_terms"]).lower()

    if has_docs and rating_norm >= 4 and min_order < 1000:
        return "✅ **Рекомендуется для малого и среднего бизнеса.** Есть сертификаты, высокий рейтинг и невысокий минимальный заказ."
    elif has_docs and rating_norm >= 4:
        return "✅ **Надёжный поставщик.** Есть сертификаты и высокий рейтинг. Обратите внимание на условия минимального заказа."
    elif rating_norm < 3:
        return "⚠️ **Требует дополнительной проверки перед сотрудничеством.** Низкий рейтинг. Рекомендуется запросить пробную партию."
    elif "бесплатно" in delivery and min_order < 2000:
        return "📦 **Выгодные условия доставки.** Бесплатная доставка при небольшом заказе – хороший вариант для тестирования."
    elif min_order > 5000:
        return "💰 **Крупный опт.** Высокий минимальный заказ. Подходит для больших объёмов, но требует значительных вложений."
    else:
        return "ℹ️ **Стандартный поставщик.** Проверьте условия на сайте или свяжитесь для уточнения деталей."

# ==============================
# 8. ЛОГИКА ПОИСКА
# ==============================
if search_clicked:
    filtered_df = df.copy()
    if selected_cat != "Все":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]
    if selected_region != "Все":
        filtered_df = filtered_df[filtered_df["region"] == selected_region]

    if not filtered_df.empty and search_term.strip():
        with st.spinner("🔍 Выполняю семантический поиск..."):
            query_emb = model.encode(search_term, convert_to_tensor=True)
            indices = filtered_df.index
            current_embeddings = supplier_embeddings[indices]
            cosine_scores = util.cos_sim(query_emb, current_embeddings)[0].cpu().numpy()
            filtered_df = filtered_df.copy()
            filtered_df["semantic_score"] = cosine_scores
            filtered_df = filtered_df[filtered_df["semantic_score"] > 0.1]
    elif not filtered_df.empty:
        filtered_df["semantic_score"] = 0.0

    if filtered_df.empty:
        st.session_state['results'] = pd.DataFrame()
    else:
        norm = get_normalized_weights()
        filtered_df["business_rating"] = filtered_df.apply(lambda row: calculate_supplier_rating(row, selected_region, norm), axis=1)
        if "semantic_score" in filtered_df.columns:
            filtered_df["final_rating"] = (filtered_df["semantic_score"] * 70) + (filtered_df["business_rating"] / 100 * 30)
            filtered_df = filtered_df.sort_values("final_rating", ascending=False)
        else:
            filtered_df["final_rating"] = filtered_df["business_rating"]
            filtered_df = filtered_df.sort_values("business_rating", ascending=False)
        st.session_state['results'] = filtered_df

# ==============================
# 9. ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==============================
if 'results' in st.session_state:
    results_df = st.session_state['results']
    if results_df.empty:
        st.warning("😕 Поставщики не найдены.")
        st.markdown("""
        **💡 Попробуйте:**
        - Сделать запрос **более общим** (например, вместо *«молоко 3.2% жирности»* → *«молочные продукты»*)
        - **Убрать фильтр** по региону или категории
        - Использовать **более короткий** запрос
        - Проверить, что в данных есть поставщики из выбранной категории
        """)
    else:
        st.subheader(f"📋 Найдено {len(results_df)} поставщиков")

        # Отображение статистики
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Средняя оценка", f"{results_df['final_rating'].mean():.1f}")
        with col2:
            st.metric("Максимальная оценка", f"{results_df['final_rating'].max():.1f}")
        with col3:
            st.metric("Количество", len(results_df))

        for idx, row in results_df.iterrows():
            rating_txt = f"{row['final_rating']:.1f}"
            ai_match = f" | 🤖 AI совпадение: {row['semantic_score']*100:.0f}%" if "semantic_score" in row else ""

            # Цветовая индикация
            if row['final_rating'] >= 70:
                status_icon = "⭐"
                status_text = "Отличный поставщик"
            elif row['final_rating'] >= 40:
                status_icon = "📊"
                status_text = "Хороший вариант, есть нюансы"
            else:
                status_icon = "⚠️"
                status_text = "Требуется проверка"

            with st.expander(f"🏢 **{row['name']}** | {status_icon} {status_text} | Оценка: {rating_txt}{ai_match}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📂 Категория:** {row['category']}")
                    st.markdown(f"**📍 Регион:** {row['region']}")
                    st.markdown(f"**👤 Контакты:** {row['contact']}")
                    st.markdown(f"**📞 Телефон:** {row['phone']}")
                    st.markdown(f"**✉️ Email:** {row['email']}")
                    if row['website'].startswith('http'):
                        st.markdown(f"**🌐 Сайт:** [{row['website']}]({row['website']})")
                with col2:
                    st.markdown(f"**📦 Мин. заказ:** {row['min_order']}")
                    st.markdown(f"**💰 Цена:** {row['price']}")
                    st.markdown(f"**🚚 Доставка:** {row['delivery_terms']}")
                    st.markdown(f"**📜 Сертификаты:** {row['documents']}")
                    st.markdown(f"**⭐ Рейтинг:** {row['rating']}")
                if row['notes']:
                    st.info(f"📝 **Заметки:** {row['notes']}")

                # Прозрачность
                norm = get_normalized_weights()
                business_rating, explanations = explain_score(row, selected_region, norm)
                with st.expander("📊 Как мы оценили поставщика?"):
                    for expl in explanations:
                        st.markdown(f"- {expl}")
                    st.markdown(f"**Итоговая оценка: {business_rating:.1f}**")

                # Рекомендация
                recommendation = generate_recommendation(row)
                st.info(recommendation)

        # Сравнение
        st.markdown("---")
        st.subheader("🔁 Сравнение поставщиков")
        st.caption("Выберите до 4 поставщиков для сравнения")

        max_compare = min(4, len(results_df))
        cols = st.columns(max_compare)
        selected_for_compare = []
        for i, (idx, row) in enumerate(results_df.iterrows()):
            if i < max_compare:
                if cols[i].checkbox(f"{row['name']}", key=f"compare_{idx}"):
                    selected_for_compare.append(row)

        if len(selected_for_compare) >= 2:
            st.subheader("📊 Таблица сравнения")
            compare_df = pd.DataFrame(selected_for_compare)
            cols_show = ["name", "category", "region", "price", "min_order", "delivery_terms", "documents", "rating"]
            if "final_rating" in compare_df.columns:
                compare_df = compare_df.rename(columns={'final_rating': 'Общая оценка'})
                cols_show.append("Общая оценка")
            st.dataframe(compare_df[cols_show], use_container_width=True)

            # График
            st.subheader("⭐ Сравнение итогового рейтинга")
            chart_df = compare_df[["name", "Общая оценка"]].copy()
            st.bar_chart(chart_df.set_index("name"))
        elif len(selected_for_compare) > 0:
            st.info("Выберите ещё хотя бы одного поставщика для сравнения.")

# ==============================
# 10. ПРИВЕТСТВЕННЫЙ ЭКРАН (если поиск не выполнен)
# ==============================
else:
    st.info("""
    🔍 **Как искать поставщиков:**

    1️⃣ Введите запрос в поле **«Семантический поиск»** (например, *«молочка с сертификатом»*).  
    2️⃣ Уточните **категорию** и **регион**, если нужно.  
    3️⃣ Настройте **важность критериев** — чем выше вес, тем важнее этот фактор.  
    4️⃣ Нажмите **«Найти и ранжировать»**.

    💡 Система понимает смысл запроса, а не только ключевые слова!  
    Попробуйте: *«дешёвая упаковка для продуктов»* или *«поставщик свежих овощей»*.
    """)

    st.markdown("### 📂 Превью данных")
    st.dataframe(df.head(5), use_container_width=True)

    # Краткая статистика
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего поставщиков", len(df))
    with col2:
        st.metric("Категорий", len(df["category"].unique()))
    with col3:
        st.metric("Регионов", len(df["region"].unique()))
