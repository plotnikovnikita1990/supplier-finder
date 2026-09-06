import streamlit as st
import pandas as pd

from src.config import Settings, DEFAULT_WEIGHTS, WEIGHT_LABELS
from src.data import load_suppliers
from src.embeddings import SemanticIndex
from src.query_parser import parse_query
from src.llm_parser import parse_with_openai
from src.ranking import RankingConfig, apply_hard_filters, rank
from src.rfq import generate_rfq

st.set_page_config(
    page_title="AI Supplier Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

SETTINGS = Settings()

st.markdown("""
<style>
:root { --accent:#0f766e; }
.block-container { max-width: 1320px; padding-top: 1.2rem; }
.hero { padding: 28px 30px; border-radius: 20px; background: linear-gradient(135deg,#ecfdf5,#f8fafc); border:1px solid #d1fae5; margin-bottom:18px; }
.hero h1 { margin:0; font-size:2.35rem; }
.hero p { color:#475569; font-size:1.05rem; margin:.5rem 0 0; }
.card { padding:18px; border:1px solid #e2e8f0; border-radius:16px; background:#fff; margin-bottom:12px; }
.score { font-size:1.65rem; font-weight:800; color:#0f766e; }
.muted { color:#64748b; }
.tag { display:inline-block; padding:4px 9px; border-radius:999px; background:#f1f5f9; margin:2px; font-size:.82rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    return load_suppliers(SETTINGS.data_path)

@st.cache_resource
def build_index(suppliers_tuple):
    suppliers = list(suppliers_tuple)
    idx = SemanticIndex(SETTINGS.embedding_model)
    idx.build([s.text_for_embedding for s in suppliers])
    return idx

try:
    suppliers = load_data()
except Exception as exc:
    st.error(f"Не удалось загрузить данные: {exc}")
    st.stop()

supplier_tuple = tuple(s.model_dump_json() for s in suppliers)

@st.cache_resource
def cached_index(serialized):
    from src.models import Supplier
    restored = [Supplier.model_validate_json(x) for x in serialized]
    idx = SemanticIndex(SETTINGS.embedding_model)
    idx.build([s.text_for_embedding for s in restored])
    return idx

index = cached_index(supplier_tuple)

if "query" not in st.session_state:
    st.session_state.query = ""
if "results" not in st.session_state:
    st.session_state.results = []
if "selected" not in st.session_state:
    st.session_state.selected = []
if "rfq_supplier" not in st.session_state:
    st.session_state.rfq_supplier = None

st.markdown("""
<div class="hero">
<h1>🛒 AI Supplier Intelligence</h1>
<p>Найдите подходящих поставщиков продуктов питания, сравните условия и получите объяснимый shortlist за несколько секунд.</p>
</div>
""", unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2 = st.columns([5, 1])
    with col1:
        query_text = st.text_input(
            "Что вы ищете?",
            value=st.session_state.query,
            placeholder="Например: сыр в Екатеринбурге, нужны сертификаты, партия до 500 кг",
            label_visibility="collapsed",
        )
    with col2:
        submitted = st.form_submit_button("🔎 Найти", use_container_width=True, type="primary")

example_cols = st.columns(4)
examples = [
    "Сыр в Екатеринбурге с сертификатами",
    "Молочная продукция до 1000 ₽",
    "Овощи с доставкой в Екатеринбург",
    "Упаковка для HoReCa",
]
for c, example in zip(example_cols, examples):
    if c.button(example, use_container_width=True):
        st.session_state.query = example
        st.rerun()

with st.sidebar:
    st.header("Настройки поиска")
    st.caption("Жёсткие условия исключают кандидатов. Остальные критерии влияют на ranking.")
    use_llm = st.checkbox("Точнее разбирать запрос через LLM", value=False, help="Опционально. Требуется OPENAI_API_KEY. Без ключа используется локальный parser.")
    weights = {}
    for key, default in DEFAULT_WEIGHTS.items():
        weights[key] = st.slider(WEIGHT_LABELS[key], 0, 10, max(1, round(default/10)), key=f"w_{key}")
    if st.button("Сбросить веса", use_container_width=True):
        for key in DEFAULT_WEIGHTS:
            st.session_state[f"w_{key}"] = max(1, round(DEFAULT_WEIGHTS[key]/10))
        st.rerun()

    st.divider()
    st.subheader("Фильтры")
    categories = sorted({s.category for s in suppliers})
    regions = sorted({s.region for s in suppliers})
    category_filter = st.multiselect("Категория", categories)
    region_filter = st.multiselect("Регион", regions)
    min_rating = st.slider("Рейтинг от", 0.0, 5.0, 0.0, 0.1)
    only_verified = st.checkbox("Только проверенные документы")
    only_with_delivery = st.checkbox("Только с доставкой")

if submitted:
    st.session_state.query = query_text.strip()
    if not st.session_state.query:
        st.warning("Введите товар или задачу закупки.")
    else:
        q = parse_with_openai(st.session_state.query) if use_llm else None
        q = q or parse_query(st.session_state.query)
        candidates = suppliers
        if category_filter:
            candidates = [s for s in candidates if s.category in category_filter]
        if region_filter:
            candidates = [s for s in candidates if s.region in region_filter]
        candidates = [s for s in candidates if s.rating >= min_rating]
        if only_verified:
            candidates = [s for s in candidates if s.certification_verified]
        if only_with_delivery:
            candidates = [s for s in candidates if s.delivery_score >= 0.7]

        candidates, hard_messages = apply_hard_filters(candidates, q)
        retrieved = index.search(q.raw_text, SETTINGS.top_k_retrieval)
        semantic = {suppliers[i].supplier_id: score for i, score in retrieved if suppliers[i] in candidates}
        # Ensure every candidate has a semantic score; 0 is neutral for filtered-out vectors.
        if not semantic:
            semantic = {s.supplier_id: 0.0 for s in candidates}

        total = sum(weights.values()) or 1
        normalized = {k: v/total for k, v in weights.items()}
        scored = rank(candidates, semantic, q, RankingConfig(normalized))
        st.session_state.results = scored[:SETTINGS.top_k_results]
        st.session_state.selected = []
        st.session_state.query_struct = q.model_dump()
        st.session_state.hard_messages = hard_messages

results = st.session_state.results

if results:
    q = parse_with_openai(st.session_state.query) if use_llm else None
    q = q or parse_query(st.session_state.query)
    st.success(f"Найдено {len(results)} подходящих вариантов. Результаты отсортированы по гибридному score.")
    if st.session_state.get("hard_messages"):
        for msg in st.session_state.hard_messages:
            st.info(msg)

    with st.expander("Как система поняла запрос"):
        qdf = pd.DataFrame([{
            "Параметр": k,
            "Значение": v if v not in (None, False, "") else "—"
        } for k,v in q.model_dump().items() if k != "raw_text"])
        st.dataframe(qdf, hide_index=True, use_container_width=True)

    st.subheader("Лучшие поставщики")
    st.caption("Score — не вероятность и не гарантия качества поставщика. Это объяснимый ranking по выбранным критериям.")

    for rank_no, item in enumerate(results, 1):
        s = item.supplier
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                st.markdown(f"### {rank_no}. {s.name}")
                st.write(f"**{s.category}** · {s.subcategory} · {s.region}")
                tags = [
                    f"от {s.price:,.0f} ₽/{s.price_unit}",
                    f"MOQ {s.min_order:,.0f} {s.min_order_unit}",
                    f"⭐ {s.rating:.1f}/5",
                ]
                st.markdown(" ".join(f'<span class="tag">{t}</span>' for t in tags), unsafe_allow_html=True)
            with c2:
                st.metric("Match", f"{item.final_score:.0f}/100")
            with c3:
                checked = s.supplier_id in st.session_state.selected
                if st.checkbox("Сравнить", value=checked, key=f"sel_{s.supplier_id}"):
                    if s.supplier_id not in st.session_state.selected:
                        st.session_state.selected.append(s.supplier_id)
                elif s.supplier_id in st.session_state.selected:
                    st.session_state.selected.remove(s.supplier_id)

            st.write(s.description)
            cols = st.columns(4)
            cols[0].write(f"**Доставка**\n{s.delivery_terms}")
            cols[1].write(f"**Документы**\n{s.certifications or 'Нет данных'}")
            cols[2].write(f"**Регион работы**\n{s.coverage}")
            cols[3].write(f"**Источник**\n{s.source_type}")

            with st.expander("Почему этот поставщик в выдаче?"):
                breakdown = pd.DataFrame([
                    {"Критерий": WEIGHT_LABELS[k], "Вклад": f"{item.components[k]*100:.1f}%", "Вес": f"{weights[k]/(sum(weights.values()) or 1)*100:.0f}%"}
                    for k in item.components
                ])
                st.dataframe(breakdown, hide_index=True, use_container_width=True)
                if item.reasons:
                    st.markdown("**Плюсы:** " + " · ".join(item.reasons))
                if item.warnings:
                    st.warning("**Проверить:** " + " · ".join(item.warnings))

                a, b, c = st.columns(3)
                if s.website:
                    a.link_button("🌐 Сайт", s.website, use_container_width=True)
                if s.email:
                    b.link_button("✉️ Email", f"mailto:{s.email}", use_container_width=True)
                if s.phone:
                    c.write(f"☎️ {s.phone}")
                st.caption(f"Источник: {s.source_url or 'демонстрационный набор'} · Проверено: {s.last_verified or 'не указано'}")

                if st.button("✍️ Сформировать запрос", key=f"rfq_{s.supplier_id}"):
                    st.session_state.rfq_supplier = s.supplier_id
                    st.rerun()

    if len(st.session_state.selected) >= 2:
        selected = [r for r in results if r.supplier.supplier_id in st.session_state.selected][:4]
        st.divider()
        st.subheader("Сравнение")
        compare_df = pd.DataFrame([{
            "Поставщик": r.supplier.name,
            "Score": round(r.final_score,1),
            "Цена, ₽": r.supplier.price,
            "MOQ": f"{r.supplier.min_order:g} {r.supplier.min_order_unit}",
            "Доставка": r.supplier.delivery_terms,
            "Документы": r.supplier.certifications or "Нет данных",
            "Рейтинг": r.supplier.rating,
            "Регион": r.supplier.region,
        } for r in selected])
        st.dataframe(compare_df, hide_index=True, use_container_width=True)
        st.bar_chart(compare_df.set_index("Поставщик")["Score"])

if st.session_state.get("rfq_supplier"):
    sid = st.session_state.rfq_supplier
    supplier = next((s for s in suppliers if s.supplier_id == sid), None)
    if supplier:
        st.divider()
        st.subheader("Запрос поставщику")
        q = parse_with_openai(st.session_state.query) if use_llm else None
        q = q or parse_query(st.session_state.query)
        rfq = generate_rfq(q, supplier)
        st.text_area("Готовый текст", rfq, height=420)
        st.download_button(
            "⬇️ Скачать .txt",
            rfq,
            file_name=f"rfq_{supplier.supplier_id}.txt",
            mime="text/plain",
        )

with st.expander("ℹ️ Как работает сервис"):
    st.markdown("""
**1. Понимание запроса.** Текст преобразуется в структурированные параметры: товар, категория, регион, лимиты, документы и доставка.

**2. Hard filters.** Обязательные условия применяются отдельно от ranking.

**3. Semantic retrieval.** Мультиязычная embedding-модель ищет поставщиков по смыслу, а не только по совпадению слов.

**4. Hybrid ranking.** Semantic relevance объединяется с ценой, MOQ, документами, доставкой, регионом и рейтингом.

**5. Explainability.** Для каждого результата показывается вклад критериев и предупреждения.

**6. Decision support.** Можно сравнить поставщиков и сразу подготовить запрос коммерческого предложения.
""")

st.caption("Демо-прототип. Данные поставщиков требуют проверки перед коммерческим использованием.")
