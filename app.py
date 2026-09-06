from pathlib import Path
import pandas as pd
import streamlit as st

from src.data import load_suppliers
from src.search import SemanticSearch, compare_suppliers

st.set_page_config(
    page_title="Food Supplier Finder",
    page_icon="🥕",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "suppliers.csv"

st.markdown("""
<style>
.block-container { max-width: 1220px; padding-top: 2rem; }
.small-muted { color: #607070; font-size: 0.88rem; }
.result-card { border: 1px solid #D9E3E3; border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: 0.8rem; background: #fff; }
.result-title { font-size: 1.08rem; font-weight: 650; margin-bottom: .15rem; }
.tag { display:inline-block; padding: 0.18rem .5rem; border-radius: 999px; background: #EEF7F5; color:#0F5F55; font-size:.78rem; margin-right:.3rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_data

def get_data():
    return load_suppliers(DATA_PATH)

@st.cache_resource

def get_search_engine(df: pd.DataFrame):
    return SemanticSearch(df)

try:
    df = get_data()
    engine = get_search_engine(df)
except Exception as exc:
    st.error(f"Не удалось загрузить данные: {exc}")
    st.stop()

if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []
if "compare_mode" not in st.session_state:
    st.session_state.compare_mode = False

st.title("🥕 Поиск поставщиков продуктов")
st.caption("Поиск по смыслу запроса + фильтры + автоматическое сравнение поставщиков")

with st.sidebar:
    st.subheader("Фильтры")
    categories = ["Все категории"] + sorted(df["category"].unique().tolist())
    cities = ["Все города"] + sorted(df["city"].unique().tolist())
    category = st.selectbox("Категория", categories)
    city = st.selectbox("Город", cities)
    st.divider()
    st.markdown("**Как работает сервис**")
    st.markdown(
        "Пишите запрос обычным языком — например, «охлажденные томаты для ресторана в Москве». "
        "Сервис ищет похожие предложения и автоматически ранжирует поставщиков."
    )
    st.caption(f"Источник данных: демонстрационный датасет · {len(df)} поставщиков")

query = st.text_input(
    "Поиск",
    placeholder="Например: органические томаты оптом для ресторана",
    label_visibility="visible",
)

filtered = df.copy()
if category != "Все категории":
    filtered = filtered[filtered["category"] == category]
if city != "Все города":
    filtered = filtered[filtered["city"] == city]

if st.session_state.compare_mode:
    st.subheader("Сравнение")
    selected = df[df["supplier_id"].isin(st.session_state.selected_ids)].copy()
    if len(selected) < 2:
        st.info("Выберите минимум двух поставщиков для сравнения.")
    else:
        if query.strip():
            ranked_all = engine.search(query, df=selected, city=None, top_k=len(selected))
            verdict, details = compare_suppliers(ranked_all)
        else:
            ranked_all = selected.copy()
            ranked_all["final_score"] = 0.5
            verdict = f"Лучший вариант для контакта: {selected.iloc[0]['name']}"
            details = "Для точного сравнения лучше задать поисковый запрос."

        st.success(verdict)
        st.write(details)
        st.divider()
        display = ranked_all[[
            "name", "category", "city", "min_order_kg", "price_per_kg",
            "certifications", "delivery", "coverage_region", "phone", "email"
        ]].copy()
        display.columns = [
            "Поставщик", "Категория", "Город", "Мин. заказ, кг", "Цена, ₽/кг",
            "Документы", "Доставка", "Регион работы", "Телефон", "Email"
        ]
        st.dataframe(display, use_container_width=True, hide_index=True)
        if st.button("← Вернуться к поиску"):
            st.session_state.compare_mode = False
            st.rerun()
    st.stop()

if not query.strip():
    st.info("Введите, что нужно закупить. Например: «рыба и морепродукты для ресторана в Санкт-Петербурге». ")
    st.stop()

results = engine.search(query.strip(), df=filtered, city=None, top_k=8)

if results.empty:
    st.warning("По текущим фильтрам поставщики не найдены.")
    st.stop()

left, right = st.columns([4, 1])
with left:
    st.subheader(f"Подходящие поставщики · {len(results)}")
with right:
    if st.session_state.selected_ids:
        if st.button(f"Сравнить ({len(st.session_state.selected_ids)})", use_container_width=True):
            st.session_state.compare_mode = True
            st.rerun()

for _, row in results.iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([4.8, 1.2])
        with c1:
            st.markdown(f"**{row['name']}**")
            st.caption(f"{row['category']} · {row['city']} · {row['region']}")
            st.markdown(
                f"{row['product_description']}  \n"
                f"**Мин. заказ:** {int(row['min_order_kg'])} кг · "
                f"**Цена:** от {int(row['price_per_kg'])} ₽/кг"
            )
            st.markdown(
                f"<span class='tag'>{row['certifications'].split(';')[0].strip()}</span>"
                f"<span class='tag'>{row['delivery'].split(';')[0].strip()}</span>",
                unsafe_allow_html=True,
            )
        with c2:
            checked = row["supplier_id"] in st.session_state.selected_ids
            if st.checkbox("Сравнить", value=checked, key=f"select_{row['supplier_id']}"):
                if row["supplier_id"] not in st.session_state.selected_ids:
                    st.session_state.selected_ids.append(row["supplier_id"])
            else:
                if row["supplier_id"] in st.session_state.selected_ids:
                    st.session_state.selected_ids.remove(row["supplier_id"])
            st.write(f"**Контакт:** {row['contact_name']}")
            st.write(row["phone"])
            st.write(row["email"])
            st.link_button("Сайт", row["website"], use_container_width=True)
            with st.expander("Подробнее", expanded=False):
                st.write(f"**Регион работы:** {row['coverage_region']}")
                st.write(f"**Комментарий:** {row['notes']}")
                st.write(f"**Источник:** {row['source']}")

st.caption(
    "Рейтинг формируется автоматически по соответствию запросу, коммерческим условиям, логистике и полноте карточки."
)
