"""CLI command: mr-lang rag — index files into a plugin's knowledge base."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from mr_lang.exceptions import PluginError

console = Console(stderr=True)


def run_rag_index(
    plugin: str,
    paths: list[str],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> None:
    """Index files into a plugin's RAG knowledge base.

    Reads text/markdown/PDF files, splits them into chunks,
    and adds them to the plugin's vector store.
    """
    from mr_lang.plugins.loader import PluginLoader

    manifests = PluginLoader.discover_plugins()
    manifest = next((m for m in manifests if m.name == plugin), None)
    if not manifest:
        available = [m.name for m in manifests]
        raise PluginError(
            f"Plugin '{plugin}' not found. Available: {', '.join(available) or 'none'}"
        )

    if not manifest.rag:
        raise PluginError(
            f"Plugin '{plugin}' has no [plugin.rag] config. "
            f"Add it to mr_lang_plugin.toml to enable RAG."
        )

    rag_cfg = manifest.rag
    cs = chunk_size or rag_cfg.chunk_size
    co = chunk_overlap or rag_cfg.chunk_overlap

    # Resolve persist directory
    persist_dir = str(
        (manifest.base_path / rag_cfg.persist_dir).resolve()
        if manifest.base_path
        else rag_cfg.persist_dir
    )

    # Load embeddings
    from mr_lang.config import MrLangConfig
    from mr_lang.providers.embeddings import get_embeddings

    config = MrLangConfig()
    embed_kwargs: dict = {}
    if config.embedding_provider == "ollama" and config.ollama_base_url:
        embed_kwargs["base_url"] = config.ollama_base_url
    embeddings = get_embeddings(config.embedding_provider, config.embedding_model, **embed_kwargs)

    # Create vector store
    if rag_cfg.backend == "chroma":
        from langchain_chroma import Chroma

        vector_store = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name=plugin,
        )
    elif rag_cfg.backend == "faiss":
        from langchain_community.vectorstores import FAISS

        vector_store = FAISS.from_texts([""], embedding=embeddings)
    else:
        raise PluginError(f"Unknown RAG backend: {rag_cfg.backend}")

    # Collect files
    files: list[Path] = []
    for p in paths:
        path = Path(p).resolve()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for ext in ("*.txt", "*.md", "*.markdown", "*.pdf", "*.rst", "*.html"):
                files.extend(path.rglob(ext))
        else:
            console.print(f"[yellow]Skipping:[/yellow] {p} (not found)")

    if not files:
        console.print("[red]No files found to index.[/red]")
        return

    console.print(f"[green]Found {len(files)} file(s) to index[/green]")

    # Split and index
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=cs, chunk_overlap=co)
    total_chunks = 0

    for file_path in sorted(files):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            console.print(f"[yellow]Skipping binary file:[/yellow] {file_path.name}")
            continue

        if not text.strip():
            continue

        chunks = splitter.split_text(text)
        metadatas = [{"source": file_path.name}] * len(chunks)
        vector_store.add_texts(chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        console.print(f"  {file_path.name} -> {len(chunks)} chunks")

    console.print(f"\n[green]Indexed {total_chunks} chunks from {len(files)} file(s)[/green]")
    console.print(f"[dim]Store: {persist_dir}[/dim]")
