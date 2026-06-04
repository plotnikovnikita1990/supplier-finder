import streamlit as st
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
import os

# Исправление сети: зеркало Hugging Face
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

st.set_page_config(page_title="AI Поиск поставщиков", layout="wide", page_icon="🍽️")
st.title("🍽️ AI-Сервис поиска поставщиков продуктов питания")
st.markdown("Использует **семантический поиск (Embeddings)** для понимания смысла запроса.")

# ==============================
# 1. ЗАГРУЗКА МОДЕЛИ
# ==============================
@st.cache_resource
def load_embedding_model():
    with st.spinner("Загрузка AI-модели (первый раз 5–10 мин)..."):
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
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
        st.info("Загрузите CSV-файл")
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
    with st.spinner("Индексация поставщиков..."):
        return model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

supplier_embeddings = compute_embeddings(df)

# ==============================
# 5. БОКОВАЯ ПАНЕЛЬ: ВЕСА 1–10
# ==============================
st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ Важность критериев (1–10)")
st.sidebar.caption("Чем выше значение, тем важнее этот критерий при выборе поставщика.")

# Инициализация весов в сессии (стандартные: 8,7,6,8,5,6)
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

# Слайдеры от 1 до 10
docs_w = st.sidebar.slider("📜 Сертификаты / документы", 1, 10, st.session_state.weights['docs'], help="Наличие сертификатов повышает доверие")
price_w = st.sidebar.slider("💰 Низкая цена", 1, 10, st.session_state.weights['price'], help="Чем ниже цена, тем лучше")
min_order_w = st.sidebar.slider("📦 Маленький минимальный заказ", 1, 10, st.session_state.weights['min_order'], help="Меньший заказ удобен для пробной партии")
delivery_w = st.sidebar.slider("🚚 Выгодная доставка", 1, 10, st.session_state.weights['delivery'], help="Бесплатная или недорогая доставка")
region_w = st.sidebar.slider("📍 Поставщик в моём регионе", 1, 10, st.session_state.weights['region'], help="Логистика и скорость")
rating_w = st.sidebar.slider("⭐ Высокий рейтинг", 1, 10, st.session_state.weights['rating'], help="Надёжность по отзывам")

# Обновляем сессию
st.session_state.weights = {
    'docs': docs_w,
    'price': price_w,
    'min_order': min_order_w,
    'delivery': delivery_w,
    'region': region_w,
    'rating': rating_w
}

# Кнопка сброса
if st.sidebar.button("🔄 Сбросить веса к стандартным (8,7,6,8,5,6)"):
    reset_weights()
    st.rerun()

# Нормализация весов (сумма → 100%)
def get_normalized_weights():
    w = st.session_state.weights
    total = sum(w.values())
    if total == 0:
        return {k: 0 for k in w}
    return {k: v / total * 100 for k, v in w.items()}

norm_weights = get_normalized_weights()

# Отображаем нормализованные проценты (для информации)
st.sidebar.caption("Итоговое влияние критериев (в %):")
for k, v in norm_weights.items():
    name = {'docs': 'Сертификаты', 'price': 'Цена', 'min_order': 'Мин. заказ', 'delivery': 'Доставка', 'region': 'Регион', 'rating': 'Рейтинг'}[k]
    st.sidebar.text(f"{name}: {v:.0f}%")

# ==============================
# 6. ФИЛЬТРЫ И ПОИСК
# ==============================
st.sidebar.markdown("---")
st.sidebar.header("🔍 Фильтры и Поиск")
search_term = st.sidebar.text_input("🧠 Семантический поиск", "")
categories = ["Все"] + sorted(df["category"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Категория", categories)
regions = ["Все"] + sorted(df["region"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Регион", regions)

search_clicked = st.sidebar.button("🚀 Найти и ранжировать", type="primary")
reset_clicked = st.sidebar.button("🔄 Сбросить результаты")

# ==============================
# 7. ФУНКЦИИ РАСЧЁТА С НОРМАЛИЗОВАННЫМИ ВЕСАМИ
# ==============================
def calculate_supplier_rating(row, target_region, norm):
    """Итоговая оценка от 0 до 100."""
    score = 0.0
    # Документы
    if str(row["documents"]).strip():
        score += norm['docs']
    # Цена
    try:
        price = float(str(row["price"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (price / 10000.0)))
        score += norm['price'] * factor
    except:
        pass
    # Мин. заказ
    try:
        mo = float(str(row["min_order"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (mo / 5000.0)))
        score += norm['min_order'] * factor
    except:
        pass
    # Доставка
    delivery = str(row["delivery_terms"]).lower()
    if "бесплатно" in delivery:
        score += norm['delivery']
    elif delivery.strip():
        score += norm['delivery'] * 0.6
    # Регион
    if target_region != "Все" and str(row["region"]).strip() == target_region:
        score += norm['region']
    # Рейтинг
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
    # Документы
    if str(row["documents"]).strip():
        total += norm['docs']
        explanations.append(f"✅ Есть сертификаты/документы (+{norm['docs']:.1f})")
    # Цена
    try:
        price = float(str(row["price"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (price / 10000.0)))
        pts = norm['price'] * factor
        if pts > 0:
            total += pts
            explanations.append(f"💰 Цена (ниже = лучше) +{pts:.1f}")
    except:
        pass
    # Мин. заказ
    try:
        mo = float(str(row["min_order"]).replace(',', '.'))
        factor = max(0.0, min(1.0, 1.0 - (mo / 5000.0)))
        pts = norm['min_order'] * factor
        if pts > 0:
            total += pts
            explanations.append(f"📦 Мин. заказ (чем меньше, тем лучше) +{pts:.1f}")
    except:
        pass
    # Доставка
    delivery = str(row["delivery_terms"]).lower()
    if "бесплатно" in delivery:
        total += norm['delivery']
        explanations.append(f"🚚 Бесплатная доставка (+{norm['delivery']:.1f})")
    elif delivery.strip():
        pts = norm['delivery'] * 0.6
        total += pts
        explanations.append(f"🚚 Есть условия доставки (+{pts:.1f})")
    # Регион
    if target_region != "Все" and str(row["region"]).strip() == target_region:
        total += norm['region']
        explanations.append(f"📍 Совпадает регион (+{norm['region']:.1f})")
    # Рейтинг
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
# 8. ЛОГИКА ПОИСКА И СОХРАНЕНИЯ РЕЗУЛЬТАТОВ
# ==============================
if reset_clicked:
    if 'results' in st.session_state:
        del st.session_state['results']
    st.rerun()

if search_clicked:
    filtered_df = df.copy()
    if selected_cat != "Все":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]
    if selected_region != "Все":
        filtered_df = filtered_df[filtered_df["region"] == selected_region]

    if not filtered_df.empty and search_term.strip():
        with st.spinner("Семантический поиск..."):
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
        st.warning("Поставщики не найдены. Измените запрос или фильтры.")
    else:
        st.subheader(f"📋 Найдено {len(results_df)} поставщиков")
        for idx, row in results_df.iterrows():
            rating_txt = f"{row['final_rating']:.1f}"
            ai_match = f" | 🤖 AI совпадение: {row['semantic_score']*100:.0f}%" if "semantic_score" in row else ""
            with st.expander(f"🏢 **{row['name']}** | Рейтинг: {rating_txt}{ai_match}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Категория:** {row['category']}")
                    st.markdown(f"**Регион:** {row['region']}")
                    st.markdown(f"**Контакты:** {row['contact']}")
                    st.markdown(f"**Телефон:** {row['phone']}")
                    st.markdown(f"**Email:** {row['email']}")
                    if row['website'].startswith('http'):
                        st.markdown(f"**Сайт:** [{row['website']}]({row['website']})")
                with col2:
                    st.markdown(f"**Мин. заказ:** {row['min_order']}")
                    st.markdown(f"**Цена:** {row['price']}")
                    st.markdown(f"**Доставка:** {row['delivery_terms']}")
                    st.markdown(f"**Сертификаты:** {row['documents']}")
                    st.markdown(f"**Рейтинг:** {row['rating']}")
                if row['notes']:
                    st.info(f"📝 Заметки: {row['notes']}")

                norm = get_normalized_weights()
                business_rating, explanations = explain_score(row, selected_region, norm)
                st.markdown("**📊 Как мы оценили поставщика:**")
                for expl in explanations:
                    st.markdown(f"- {expl}")
                st.markdown(f"**Итоговая оценка: {business_rating:.1f}**")
                
                recommendation = generate_recommendation(row)
                st.info(recommendation)

        # Сравнение
        st.markdown("---")
        st.subheader("🔁 Сравнение поставщиков")
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
            
            # График сравнения (без дополнительных библиотек)
            st.subheader("⭐ Сравнение итогового рейтинга")
            chart_df = compare_df[["name", "Общая оценка"]].copy()
            st.bar_chart(chart_df.set_index("name"))
        elif len(selected_for_compare) > 0:
            st.info("Выберите ещё хотя бы одного поставщика для сравнения.")
else:
    st.info("👈 Настройте фильтры, введите запрос и нажмите 'Найти и ранжировать'")
    st.markdown("### 📂 Превью данных")
    st.dataframe(df.head(5), use_container_width=True)