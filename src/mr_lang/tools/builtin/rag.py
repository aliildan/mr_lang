"""RAG tools — give the agent access to a plugin-level knowledge base."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool, tool

if TYPE_CHECKING:
    from langchain_core.vectorstores import VectorStore


def create_rag_tools(vector_store: VectorStore) -> list[BaseTool]:
    """Create RAG tools bound to a specific vector store."""
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    @tool
    async def search_knowledge(query: str) -> str:
        """Search the knowledge base for relevant documents. Use a natural language query."""
        results = await retriever.ainvoke(query)
        if not results:
            return "No relevant documents found in the knowledge base."
        sections = []
        for doc in results:
            source = doc.metadata.get("source", "unknown")
            sections.append(f"[{source}]\n{doc.page_content}")
        return "\n\n---\n\n".join(sections)

    @tool
    async def add_to_knowledge(content: str, source: str) -> str:
        """Add a document to the knowledge base. Provide the content and a source label."""
        await vector_store.aadd_texts([content], metadatas=[{"source": source}])
        return f"Added to knowledge base from: {source}"

    return [search_knowledge, add_to_knowledge]
