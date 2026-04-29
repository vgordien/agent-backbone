from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import List

DOCS_TEXT = """
1. Переводы до 100 000 RUB бесплатны.
2. Блокировка счёта при 3 неудачных попытках ввода PIN.
3. Кредитная карта: грейс-период 50 дней, кэшбэк 1% на всё.
"""

def init_retriever():
    from langchain_core.documents import Document
    docs = [Document(page_content=DOCS_TEXT)]
    chunks = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20).split_documents(docs)
    
    # Fallback: если Ollama не запущен, вернёт пустой контекст, но не упадёт
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vs = Chroma.from_documents(chunks, embeddings, collection_name="bank", persist_directory=None)
        return vs.as_retriever(search_kwargs={"k": 1})
    except Exception:
        return lambda query: chunks  # простой fallback

# from langchain_core.documents import Document
# from langchain_core.retrievers import BaseRetriever
# from typing import List

# DOCS_TEXT = """
# 1. Переводы до 100 000 RUB бесплатны.
# 2. Блокировка счёта при 3 неудачных попытках ввода PIN.
# 3. Кредитная карта: грейс-период 50 дней, кэшбэк 1% на всё.
# """

# class FallbackRetriever(BaseRetriever):
#     def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
#         q = query.lower()
#         if any(kw in q for kw in ["перевод", "комиссия", "бесплат", "100"]):
#             return [Document(page_content="Переводы до 100 000 RUB бесплатны.")]
#         if any(kw in q for kw in ["пин", "блокир", "попыт"]):
#             return [Document(page_content="Блокировка счёта при 3 неудачных попытках ввода PIN.")]
#         return [Document(page_content="Информация по запросу не найдена в локальной базе.")]

# def init_retriever():
#     return FallbackRetriever()