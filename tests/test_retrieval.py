import pytest
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from app.retrieval import build_ensemble_retriever, BM25Cache, bm25_cache
from app.config import TOP_K


class TestBM25Cache:
    def test_get_or_build_creates_retriever(self):
        cache = BM25Cache()
        docs = [Document(page_content="test"), Document(page_content="test2")]
        r = cache.get_or_build("col", docs, k=3)
        assert r is not None
        assert r.k == 3

    def test_cache_hit_returns_same_object(self):
        cache = BM25Cache()
        docs = [Document(page_content="test")]
        r1 = cache.get_or_build("col", docs, k=1)
        r2 = cache.get_or_build("col", docs, k=2)
        assert r2 is r1
        assert r2.k == 2

    def test_invalidate_removes_cache(self):
        cache = BM25Cache()
        docs = [Document(page_content="test")]
        r1 = cache.get_or_build("col", docs, k=1)
        cache.invalidate("col")
        r2 = cache.get_or_build("col", docs, k=1)
        assert r2 is not r1

    def test_invalidate_nonexistent_does_not_crash(self):
        cache = BM25Cache()
        cache.invalidate("nonexistent")

    def test_multiple_collections_isolated(self):
        cache = BM25Cache()
        docs_a = [Document(page_content="aaa")]
        docs_b = [Document(page_content="bbb")]
        ra = cache.get_or_build("A", docs_a, k=1)
        rb = cache.get_or_build("B", docs_b, k=2)
        assert ra is not rb

    def test_singleton_exists(self):
        assert isinstance(bm25_cache, BM25Cache)

    def test_russian_search(self):
        cache = BM25Cache()
        docs = [
            Document(page_content="Арендатор обязуется оплачивать арендную плату ежемесячно."),
            Document(page_content="Стороны пришли к соглашению о расторжении договора."),
        ]
        r = cache.get_or_build("ru", docs, k=2)
        results = r.invoke("арендная плата")
        assert len(results) >= 1
        assert any("арендн" in doc.page_content for doc in results)

    def test_empty_documents_list_raises(self):
        cache = BM25Cache()
        with pytest.raises(ValueError):
            cache.get_or_build("empty", [], k=5)

    def test_single_document(self):
        cache = BM25Cache()
        docs = [Document(page_content="Единственный документ в коллекции.")]
        r = cache.get_or_build("single", docs, k=5)
        results = r.invoke("единственный")
        assert len(results) == 1

    def test_many_documents_scale(self):
        cache = BM25Cache()
        docs = [Document(page_content=f"Документ номер {i}.") for i in range(100)]
        r = cache.get_or_build("scale", docs, k=5)
        results = r.invoke("номер")
        assert len(results) == 5

    def test_rebuild_after_clear(self):
        cache = BM25Cache()
        docs1 = [Document(page_content="Первая версия")]
        docs2 = [Document(page_content="Вторая версия")]
        r1 = cache.get_or_build("update", docs1, k=1)
        cache.invalidate("update")
        r2 = cache.get_or_build("update", docs2, k=1)
        results = r2.invoke("Вторая")
        assert len(results) == 1

    def test_identical_collections_return_same_object(self):
        cache = BM25Cache()
        docs = [Document(page_content="test")]
        r1 = cache.get_or_build("same", docs, k=1)
        r2 = cache.get_or_build("same", docs, k=1)
        assert r2 is r1


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

    def test_build_retriever_returns_runnable(self):
        from app.retrieval import build_retriever
        from unittest.mock import MagicMock
        from langchain_core.documents import Document
        mock_vs = MagicMock()
        mock_retriever = MagicMock(spec=Runnable)
        mock_vs.as_retriever.return_value = mock_retriever
        docs = [Document(page_content="test document")]
        retriever = build_retriever(mock_vs, docs, k=2, collection_name="test")
        assert isinstance(retriever, Runnable)


class TestHybridSearch:
    def test_hybrid_search_propagates_errors(self):
        from app.retrieval import hybrid_search
        with pytest.raises(Exception):
            hybrid_search("test", [], collection_name="nonexistent_should_fail", k=1)
