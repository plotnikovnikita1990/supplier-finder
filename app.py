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

st.markdown(
    """
<style>
.block-container { max-width: 1220px; padding-top: 2rem; }
.small-muted { color: #607070; font-size: 0.88rem; }
.best-card { border: 2px solid #2D7A6D; border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: .9rem; background: #F4FBF8; }
.normal-card { border: 1px solid #D9E3E3; border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: .9rem; background: #fff; }
.result-title { font-size: 1.08rem; font-weight: 650; margin-bottom: .15rem; }
.tag { display:inline-block; padding: 0.18rem .5rem; border-radius: 999px; background: #EEF7F5; color:#0F5F55; font-size:.78rem; margin-right:.3rem; }
.best-badge { display:inline-block; padding: .18rem .55rem; border-radius: 999px; background:#DDF3EA; color:#17634F; font-size:.78rem; font-weight:700; margin-bottom:.35rem; }
</style>
""",
    unsafe_allow_html=True,
)


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
st.caption("Семантический поиск + фильтры + автоматический рейтинг и сравнение")

with st.sidebar:
    st.subheader("Фильтры")
    categories = ["Все категории"] + sorted(df["category"].unique().tolist())
    cities = ["Все города"] + sorted(df["city"].unique().tolist())
    category = st.selectbox("Категория", categories)
    city = st.selectbox("Город", cities)

    st.divider()
    st.subheader("Сортировка")
    sort_option = st.selectbox(
        "Порядок результатов",
        [
            "Рейтинг: сначала лучшие",
            "Рейтинг: сначала ниже",
            "Мин. объем заказа: сначала меньше",
            "Мин. объем заказа: сначала больше",
            "Цена: сначала ниже",
            "Цена: сначала выше",
            "Заказы: сначала больше",
            "Заказы: сначала меньше",
        ],
    )

    st.divider()
    st.markdown("**Как работает сервис**")
    st.markdown(
        "Пишите запрос обычным языком — например, «томаты для ресторана в Москве». "
        "При выборе категории или города результаты появляются сразу. Лучший вариант определяется автоматически."
    )
    st.caption(f"Источник данных: демонстрационный датасет · {len(df)} поставщиков · поиск: {engine.mode}")

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
    st.subheader("Сравнение выбранных поставщиков")
    selected = df[df["supplier_id"].isin(st.session_state.selected_ids)].copy()
    if len(selected) < 2:
        st.info("Выберите минимум двух поставщиков для сравнения.")
    else:
        if query.strip():
            ranked_all = engine.search(query, df=selected, city=city if city != "Все города" else None, top_k=len(selected))
        else:
            ranked_all = engine.rank_filtered(selected, city=city if city != "Все города" else None)
        verdict, details = compare_suppliers(ranked_all)
        st.success(verdict)
        st.write(details)
        st.divider()
        display = ranked_all[[
            "name", "category", "city", "rating", "orders_count", "min_order_kg", "price_per_kg",
            "certifications", "delivery", "coverage_region", "phone", "email"
        ]].copy()
        display.columns = [
            "Поставщик", "Категория", "Город", "Рейтинг", "Заказов", "Мин. заказ, кг", "Цена, ₽/кг",
            "Документы", "Доставка", "Регион работы", "Телефон", "Email"
        ]
        st.dataframe(display, use_container_width=True, hide_index=True)
        if st.button("← Вернуться к поиску"):
            st.session_state.compare_mode = False
            st.rerun()
    st.stop()

# With a text query use semantic search. With filters but no text query, show results immediately.
if query.strip():
    results = engine.search(
        query.strip(),
        df=filtered,
        city=city if city != "Все города" else None,
        top_k=len(filtered),
    )
    mode_label = "по вашему запросу"
elif category != "Все категории" or city != "Все города":
    results = engine.rank_filtered(filtered, city=city if city != "Все города" else None)
    mode_label = "по выбранным фильтрам"
else:
    st.info("Введите, что нужно закупить, или выберите категорию/город — результаты появятся здесь автоматически.")
    st.stop()

if results.empty:
    st.warning("По текущим фильтрам поставщики не найдены.")
    st.stop()

# The best supplier is based on the internal score, independent of the user's display sorting.
best_supplier_id = results.sort_values("final_score", ascending=False).iloc[0]["supplier_id"]

sort_map = {
    "Рейтинг: сначала лучшие": ("rating", False),
    "Рейтинг: сначала ниже": ("rating", True),
    "Мин. объем заказа: сначала меньше": ("min_order_kg", True),
    "Мин. объем заказа: сначала больше": ("min_order_kg", False),
    "Цена: сначала ниже": ("price_per_kg", True),
    "Цена: сначала выше": ("price_per_kg", False),
    "Заказы: сначала больше": ("orders_count", False),
    "Заказы: сначала меньше": ("orders_count", True),
}
sort_column, ascending = sort_map[sort_option]
results = results.sort_values(sort_column, ascending=ascending).reset_index(drop=True)

left, right = st.columns([4, 1])
with left:
    st.subheader(f"Подходящие поставщики · {len(results)}")
    st.caption(f"Показаны результаты {mode_label}. Лучший вариант определяется автоматически.")
with right:
    if st.session_state.selected_ids:
        if st.button(f"Сравнить ({len(st.session_state.selected_ids)})", use_container_width=True):
            st.session_state.compare_mode = True
            st.rerun()

for _, row in results.iterrows():
    is_best = row["supplier_id"] == best_supplier_id
    card_class = "best-card" if is_best else "normal-card"

    with st.container(border=True):
        if is_best:
            st.markdown("<span class='best-badge'>★ Лучший вариант</span>", unsafe_allow_html=True)

        c1, c2 = st.columns([4.8, 1.2])
        with c1:
            st.markdown(f"**{row['name']}**")
            st.caption(f"{row['category']} · {row['city']} · {row['region']}")
            st.markdown(
                f"{row['product_description']}  \n"
                f"**Рейтинг:** {row['rating']:.1f}/5 · "
                f"**Заказов выполнено:** {int(row['orders_count'])} · "
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
    "Рейтинг формируется автоматически. Пользователь может менять только порядок отображения: рейтинг, минимальный объем, цену или количество заказов."
)
