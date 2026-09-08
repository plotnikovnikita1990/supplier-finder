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
    .block-container { max-width: 1220px; padding-top: 2rem; padding-bottom: 3rem; }
    .app-subtitle { color: #607070; margin-top: -0.6rem; margin-bottom: 1.3rem; }
    .best-badge { display:inline-block; padding:.22rem .6rem; border-radius:999px;
        background:#DDF3EA; color:#17634F; font-size:.78rem; font-weight:700; margin-bottom:.45rem; }
    .hint-badge { display:inline-block; padding:.18rem .5rem; border-radius:999px;
        background:#EEF7F5; color:#0F5F55; font-size:.76rem; margin-right:.25rem; margin-bottom:.2rem; }
    .metric-label { color:#607070; font-size:.82rem; margin-bottom:.08rem; }
    .metric-value { font-size:1.08rem; font-weight:700; margin-bottom:.55rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_data() -> pd.DataFrame:
    return load_suppliers(DATA_PATH)


@st.cache_resource
def get_search_engine(df: pd.DataFrame) -> SemanticSearch:
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

st.title("🥕 Food Supplier Finder")
st.markdown(
    '<div class="app-subtitle">Поиск и сравнение поставщиков для менеджера по закупкам</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Фильтры")
    categories = ["Все категории"] + sorted(df["category"].dropna().unique().tolist())
    cities = ["Все города"] + sorted(df["city"].dropna().unique().tolist())
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
        "1. Введите запрос или выберите фильтры.  \n"
        "2. Система ищет релевантных поставщиков.  \n"
        "3. Внутренний ranking определяет лучший вариант.  \n"
        "4. При необходимости можно сравнить поставщиков."
    )
    st.caption(
        f"Демонстрационный датасет · {len(df)} поставщиков · режим поиска: {engine.mode}"
    )

query = st.text_input(
    "Поиск",
    placeholder="Например: органические томаты оптом для ресторана",
)

filtered = df.copy()
if category != "Все категории":
    filtered = filtered[filtered["category"] == category]
if city != "Все города":
    filtered = filtered[filtered["city"] == city]


# ---------- Head-to-Head comparison ----------
if st.session_state.compare_mode:
    st.subheader("Сравнение поставщиков")
    selected = df[df["supplier_id"].isin(st.session_state.selected_ids)].copy()

    if len(selected) < 2:
        st.info("Выберите минимум двух поставщиков для сравнения.")
    else:
        if query.strip():
            ranked_selected = engine.search(
                query.strip(),
                df=selected,
                city=city if city != "Все города" else None,
                top_k=len(selected),
            )
        else:
            ranked_selected = engine.rank_filtered(
                selected,
                city=city if city != "Все города" else None,
            )

        verdict, details = compare_suppliers(ranked_selected)
        st.success(verdict)
        st.write(details)

        compare_order = ranked_selected.sort_values(
            "final_score", ascending=False
        ).reset_index(drop=True)
        columns = st.columns(min(len(compare_order), 4))

        for idx, (_, row) in enumerate(compare_order.head(4).iterrows()):
            with columns[idx]:
                is_best = idx == 0
                with st.container(border=True):
                    if is_best:
                        st.markdown(
                            '<span class="best-badge">★ Лучший вариант</span>',
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"### {row['name']}")
                    st.caption(f"{row['category']} · {row['city']}")
                    st.markdown(f"**Рейтинг:** {row['rating']:.1f}/5")
                    st.markdown(
                        f"<div class='metric-label'>Заказов выполнено</div>"
                        f"<div class='metric-value'>{int(row['orders_count'])}</div>"
                        f"<div class='metric-label'>Минимальный заказ</div>"
                        f"<div class='metric-value'>{int(row['min_order_kg'])} кг</div>"
                        f"<div class='metric-label'>Цена</div>"
                        f"<div class='metric-value'>от {int(row['price_per_kg'])} ₽/кг</div>",
                        unsafe_allow_html=True,
                    )

                    has_certs = str(row["certifications"]).strip() not in {"", "nan"}
                    delivery_text = str(row["delivery"]).lower()
                    fast_delivery = any(
                        token in delivery_text
                        for token in ("1-2 дня", "1–2 дня", "ежедневно", "24 часа")
                    )
                    high_moq = float(row["min_order_kg"]) >= 500

                    st.write("✅ Есть сертификаты" if has_certs else "❌ Сертификаты не указаны")
                    st.write("🚚 Быстрая доставка" if fast_delivery else "ℹ️ Стандартная доставка")
                    st.write("❌ Мин. заказ большой" if high_moq else "✅ Умеренный мин. заказ")

                    st.markdown(
                        f"**Регион:** {row['coverage_region']}  \n"
                        f"**Контакт:** {row['contact_name']}  \n"
                        f"**Телефон:** {row['phone']}  \n"
                        f"**Email:** {row['email']}"
                    )

                    if str(row["website"]).strip():
                        st.link_button(
                            "Открыть сайт",
                            row["website"],
                            use_container_width=True,
                        )

                    with st.expander("Подробнее"):
                        st.write(row["product_description"])
                        st.write(f"**Комментарий:** {row['notes']}")
                        st.write(f"**Источник:** {row['source']}")

        if st.button("← Вернуться к поиску", use_container_width=True):
            st.session_state.compare_mode = False
            st.rerun()

    st.stop()


# ---------- Search results ----------
if query.strip():
    results = engine.search(
        query.strip(),
        df=filtered,
        city=city if city != "Все города" else None,
        top_k=len(filtered),
    )
    mode_label = "по вашему запросу"
elif category != "Все категории" or city != "Все города":
    results = engine.rank_filtered(
        filtered,
        city=city if city != "Все города" else None,
    )
    mode_label = "по выбранным фильтрам"
else:
    st.info(
        "Введите, что нужно закупить, или выберите категорию/город — "
        "результаты появятся здесь автоматически."
    )
    st.stop()

if results.empty:
    st.warning("По текущим фильтрам поставщики не найдены.")
    st.stop()

best_supplier_id = (
    results.sort_values("final_score", ascending=False).iloc[0]["supplier_id"]
)

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
    st.caption(
        f"Показаны результаты {mode_label}. Лучший вариант определяется автоматически."
    )
with right:
    if len(st.session_state.selected_ids) >= 2:
        if st.button(
            f"Сравнить ({len(st.session_state.selected_ids)})",
            use_container_width=True,
        ):
            st.session_state.compare_mode = True
            st.rerun()


# ---------- Supplier cards ----------
for _, row in results.iterrows():
    is_best = row["supplier_id"] == best_supplier_id

    with st.container(border=True):
        c1, c2 = st.columns([5, 1.2])

        with c1:
            if is_best:
                st.markdown(
                    '<span class="best-badge">★ Лучший вариант</span>',
                    unsafe_allow_html=True,
                )

            st.markdown(f"### {row['name']}")
            st.caption(f"{row['category']} · {row['city']} · {row['region']}")
            st.write(row["product_description"])

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Рейтинг", f"{row['rating']:.1f}/5")
            with m2:
                st.metric("Заказов", int(row["orders_count"]))
            with m3:
                st.metric("Мин. заказ", f"{int(row['min_order_kg'])} кг")
            with m4:
                st.metric("Цена", f"{int(row['price_per_kg'])} ₽/кг")

            certs = str(row["certifications"]).strip()
            delivery = str(row["delivery"]).strip()
            st.markdown(
                (
                    f'<span class="hint-badge">✅ {certs.split(";")[0].strip()}</span>'
                    if certs
                    else '<span class="hint-badge">❌ Сертификаты не указаны</span>'
                ),
                unsafe_allow_html=True,
            )
            if delivery:
                st.markdown(
                    f'<span class="hint-badge">🚚 {delivery.split(";")[0].strip()}</span>',
                    unsafe_allow_html=True,
                )

        with c2:
            checked = row["supplier_id"] in st.session_state.selected_ids
            selected = st.checkbox(
                "Сравнить",
                value=checked,
                key=f"select_{row['supplier_id']}",
            )
            if selected and row["supplier_id"] not in st.session_state.selected_ids:
                st.session_state.selected_ids.append(row["supplier_id"])
            elif not selected and row["supplier_id"] in st.session_state.selected_ids:
                st.session_state.selected_ids.remove(row["supplier_id"])

        st.markdown("---")
        contact1, contact2 = st.columns(2)
        with contact1:
            st.write(f"**Контакт:** {row['contact_name']}")
            st.write(f"**Телефон:** {row['phone']}")
            st.write(f"**Email:** {row['email']}")
        with contact2:
            st.write(f"**Регион работы:** {row['coverage_region']}")
            if str(row["website"]).strip():
                st.link_button("Сайт поставщика", row["website"], use_container_width=True)

        with st.expander("Подробнее"):
            st.write(f"**Комментарий:** {row['notes']}")
            st.write(f"**Источник:** {row['source']}")
            st.caption(
                "Внутренний ranking скрыт от пользователя: система сама определяет "
                "наиболее подходящий вариант."
            )
