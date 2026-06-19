import pytest
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from app.retrieval import build_ensemble_retriever
from app.config import TOP_K


class TestBuildEnsembleRetriever:
    def test_ensemble_retriever_creation(self):
        docs = [
            Document(page_content="Договор аренды помещения."),
            Document(page_content="Договор оказания услуг."),
            Document(page_content="Соглашение о конфиденциальности."),
        ]

        from unittest.mock import MagicMock
        mock_retriever = MagicMock(spec=Runnable)
        mock_retriever.invoke.return_value = docs[:2]

        mock_vs = MagicMock()
        mock_vs.as_retriever.return_value = mock_retriever

        retriever = build_ensemble_retriever(mock_vs, docs, k=TOP_K)
        assert retriever is not None
        result = retriever.invoke("test")
        assert len(result) > 0

    def test_bm25_works_with_russian(self):
        docs = [
            Document(page_content="Арендатор обязуется оплачивать арендную плату ежемесячно."),
            Document(page_content="Стороны пришли к соглашению о расторжении договора."),
        ]
        from langchain_community.retrievers import BM25Retriever
        bm25 = BM25Retriever.from_documents(docs)
        bm25.k = 2
        results = bm25.invoke("арендная плата")
        assert len(results) >= 1
        assert any("арендн" in r.page_content for r in results)
