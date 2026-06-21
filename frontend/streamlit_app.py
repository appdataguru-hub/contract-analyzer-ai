import os

import streamlit as st

from utils import check_health, upload_pdf, ask_question, fetch_metrics, get_app_info, BACKEND_URL

st.set_page_config(
    page_title="Contract Analyzer AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

app_info = get_app_info()

if "backend_url" not in st.session_state:
    st.session_state.backend_url = os.getenv("BACKEND_URL", BACKEND_URL)
if "collection_name" not in st.session_state:
    st.session_state.collection_name = os.getenv("COLLECTION_NAME", "contracts")
if "history" not in st.session_state:
    st.session_state.history = []
if "upload_state" not in st.session_state:
    st.session_state.upload_state = None
if "backend_connected" not in st.session_state:
    st.session_state.backend_connected = False
if "gigachat_warning" not in st.session_state:
    st.session_state.gigachat_warning = False


def check_connection():
    st.session_state.backend_connected = check_health(st.session_state.backend_url)


def render_sidebar():
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/contract.png",
            width=64,
        )
        st.markdown("## Contract Analyzer AI")
        st.caption(f"v{app_info['version']}")

        st.divider()

        with st.expander("⚙️ Настройки подключения", expanded=not st.session_state.backend_connected):
            st.text_input(
                "URL бэкенда",
                key="backend_url",
                on_change=check_connection,
                label_visibility="collapsed",
                placeholder="http://localhost:8000",
            )
            st.text_input("Коллекция", key="collection_name", label_visibility="collapsed", placeholder="contracts")

            if st.button("🔄 Проверить подключение", use_container_width=True):
                check_connection()

        status_icon = "✅" if st.session_state.backend_connected else "❌"
        status_text = "Бэкенд подключён" if st.session_state.backend_connected else "Бэкенд недоступен"
        st.markdown(f"{status_icon} **{status_text}**")

        if st.session_state.gigachat_warning:
            st.warning("⚠️ **GigaChat недоступен** — ответы формируются из найденных фрагментов")

        st.divider()

        st.markdown("### 📊 Метрики качества")
        metrics = fetch_metrics(st.session_state.backend_url) if st.session_state.backend_connected else None
        if metrics and metrics.get("total_evaluations", 0) > 0:
            col1, col2 = st.columns(2)

            f_score = metrics.get("faithfulness_mean")
            f_status = metrics.get("faithfulness_status", "N/A")
            r_score = metrics.get("answer_relevancy_mean")
            r_status = metrics.get("answer_relevancy_status", "N/A")

            with col1:
                st.metric("Faithfulness", f"{f_score:.2f}" if f_score is not None else "—", delta=f_status)
            with col2:
                st.metric("Relevancy", f"{r_score:.2f}" if r_score is not None else "—", delta=r_status)

            evals = metrics["total_evaluations"]
            st.caption(f"На {evals} {'ответ' if evals == 1 else 'ответа' if evals < 5 else 'ответов'}")

            with st.expander("📈 Подробно"):
                st.markdown(f"**Faithfulness:** min {metrics.get('faithfulness_min', '—')}  max {metrics.get('faithfulness_max', '—')}")
                st.markdown(f"**Relevancy:** min {metrics.get('answer_relevancy_min', '—')}  max {metrics.get('answer_relevancy_max', '—')}")
                st.markdown(f"**Порог:** {metrics.get('faithfulness_threshold', 0.7)}")
        elif metrics:
            st.info("Пока нет оценок. Задайте вопрос!")
        else:
            st.info("Метрики недоступны. Проверьте подключение.")

        st.divider()
        st.caption("Made with Streamlit + FastAPI")


def render_upload_section():
    st.markdown("### 📤 Загрузка договора")
    st.caption("Загрузите PDF-файл для анализа")

    uploaded_file = st.file_uploader(
        "Выберите PDF-файл",
        type=["pdf"],
        label_visibility="collapsed",
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name

        file_size_mb = len(file_bytes) / (1024 * 1024)
        st.caption(f"Файл: **{filename}** ({file_size_mb:.1f} МБ)")

        if st.button("📄 Загрузить и обработать", type="primary", use_container_width=True):
            with st.status("Обработка документа...", expanded=True) as status:
                st.write("📡 Отправка файла на сервер...")
                try:
                    result = upload_pdf(
                        file_bytes=file_bytes,
                        filename=filename,
                        backend_url=st.session_state.backend_url,
                    )
                    st.write(f"✅ Чанков создано: {result['chunks']}")
                    st.write(f"📁 Коллекция: {result['collection_name']}")
                    status.update(label="✅ Документ успешно обработан", state="complete")
                    st.session_state.upload_state = result
                    st.session_state.gigachat_warning = False
                    st.rerun()
                except ValueError as e:
                    status.update(label="❌ Ошибка при загрузке", state="error")
                    st.error(str(e))
                except Exception as e:
                    status.update(label="❌ Ошибка сервера", state="error")
                    st.error(f"Не удалось обработать файл: {e}")

    if st.session_state.upload_state:
        st.success(
            f"✅ Договор **{st.session_state.upload_state['filename']}** загружен. "
            f"Создано {st.session_state.upload_state['chunks']} фрагментов."
        )


def render_qa_section():
    st.markdown("### 💬 Вопрос по договору")
    st.caption("Задайте вопрос о содержании загруженного документа")

    col1, col2 = st.columns([5, 1])
    with col1:
        question = st.text_input(
            "Введите ваш вопрос",
            placeholder="Например: Какая цена договора?",
            label_visibility="collapsed",
            key="question_input",
        )
    with col2:
        ask_btn = st.button("🚀 Спросить", type="primary", use_container_width=True, disabled=not question)

    if ask_btn and question:
        if not st.session_state.upload_state:
            st.warning("⚠️ Сначала загрузите документ через форму выше.")
        else:
            with st.spinner("🔍 Анализирую документ и генерирую ответ..."):
                try:
                    result = ask_question(
                        question=question,
                        collection_name=st.session_state.collection_name,
                        backend_url=st.session_state.backend_url,
                    )
                    st.session_state.history.append({
                        "question": question,
                        "answer": result["answer"],
                        "sources": result.get("sources", []),
                        "faithfulness_score": result.get("faithfulness_score"),
                        "faithfulness_reason": result.get("faithfulness_reason"),
                        "answer_relevancy_score": result.get("answer_relevancy_score"),
                        "answer_relevancy_reason": result.get("answer_relevancy_reason"),
                    })
                    if "временно недоступен" in result["answer"]:
                        st.session_state.gigachat_warning = True
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Ошибка при получении ответа: {e}")

    if st.session_state.history:
        st.divider()
        st.markdown("### 📋 История вопросов и ответов")

        for i, entry in enumerate(reversed(st.session_state.history), 1):
            with st.container(border=True):
                col_q, col_a = st.columns([1, 5])
                with col_q:
                    st.markdown(f"**Вопрос #{len(st.session_state.history) - i + 1}**")
                with col_a:
                    st.markdown(f"{entry['question']}")

                st.markdown("**Ответ:**")
                st.markdown(entry["answer"])

                f_score = entry.get("faithfulness_score")
                r_score = entry.get("answer_relevancy_score")
                if f_score is not None and r_score is not None:
                    cols = st.columns(4)
                    with cols[0]:
                        f_color = "🟢" if f_score >= 0.7 else "🔴"
                        st.markdown(f"{f_color} **Faithfulness:** {f_score:.2f}")
                    with cols[1]:
                        r_color = "🟢" if r_score >= 0.7 else "🔴"
                        st.markdown(f"{r_color} **Relevancy:** {r_score:.2f}")
                    with cols[2]:
                        pass
                    with cols[3]:
                        pass
                elif f_score is not None:
                    st.markdown(f"**Faithfulness:** {f_score:.2f}")
                elif r_score is not None:
                    st.markdown(f"**Relevancy:** {r_score:.2f}")

                if entry.get("sources"):
                    st.markdown("**Источники:**")
                    for src in set(entry["sources"]):
                        st.markdown(f"- `{src}`")

            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[-20:]

        if st.button("🗑️ Очистить историю"):
            st.session_state.history = []
            st.rerun()


def main():
    check_connection()

    render_sidebar()

    st.title("📄 Contract Analyzer AI")
    st.markdown(
        "Загрузите PDF-договор и задавайте вопросы на естественном языке. "
        "Система найдёт релевантные фрагменты и сформирует ответ с помощью GigaChat."
    )

    st.divider()

    tab1, tab2 = st.tabs(["📄 Анализ договора", "ℹ️ О проекте"])

    with tab1:
        if not st.session_state.backend_connected:
            st.warning(
                "⚠️ **Бэкенд недоступен.**\n\n"
                "Убедитесь, что сервер запущен. "
                "Укажите правильный URL в боковой панели (⚙️ Настройки подключения)."
            )

        render_upload_section()
        st.divider()
        render_qa_section()

    with tab2:
        st.markdown("""
        ### О проекте

        **Contract Analyzer AI** — сервис анализа договоров на базе гибридного RAG.

        **Технологический стек:**
        - **FastAPI** — REST API
        - **Streamlit** — веб-интерфейс
        - **Qdrant** — векторная база данных
        - **GigaChat** — генерация ответов
        - **LangChain** — RAG-пайплайн
        - **Docker** — инфраструктура
        - **DeepEval** — оценка качества RAG (Faithfulness + Answer Relevancy)

        **Как это работает:**
        1. Загрузите PDF с договором
        2. Текст извлекается и разбивается на фрагменты
        3. Фрагменты векторизуются и сохраняются в Qdrant
        4. При вопросе выполняется гибридный поиск (векторный + BM25)
        5. GigaChat формирует ответ на основе найденного контекста
        6. Каждый ответ автоматически оценивается по метрикам Faithfulness и Relevancy

        **Метрики качества:**
        - **Faithfulness** — насколько ответ соответствует контексту документа
        - **Answer Relevancy** — насколько ответ релевантен вопросу
        - Каждый ответ оценивается в реальном времени через DeepEval (gpt-4o)

        [📖 Документация API](http://localhost:8000/docs)
        """)


if __name__ == "__main__":
    main()
