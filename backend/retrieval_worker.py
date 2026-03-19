"""
Pure Semantic Retrieval Worker
==============================

This module provides a lightweight retrieval pipeline that bypasses the LLM entirely.
Instead of routing ChromaDB results through LLM response generation, it uses
LlamaIndex's VectorIndexRetriever to perform pure semantic document retrieval
and returns the raw scored nodes directly to the caller.

Key advantages over the LLM-based query pipeline:
    - Dramatically lower latency (no LLM inference required)
    - Zero GPU compute for generation (only embedding + reranking)
    - Direct access to raw document chunks with relevance scores
    - Ideal for document search / exploration workflows

Usage:
    The worker is designed to run in a QThread via moveToThread(). Connect
    the thread's started signal to worker.run(), then listen for finished
    or error signals to receive results asynchronously.

Typical signal wiring:
    thread.started  -> worker.run
    worker.finished -> handler(results: list[dict])
    worker.error    -> handler(error_msg: str)
"""

from PySide6.QtCore import QObject, Signal
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import QueryBundle
from ui.config import cfg


class RetrievalWorker(QObject):
    """
    Background worker that executes a pure semantic retrieval query.

    Unlike QueryWorker (which feeds results into an LLM for response generation),
    this worker retrieves the top-k most semantically similar document chunks
    from the vector index and returns them as structured result dictionaries.

    Signals:
        finished (list): Emitted with a list of result dicts, each containing:
            - title (str):     Document file name or 'Untitled'
            - file_path (str): Absolute path to the source file (may be None)
            - score (float):   Relevance score from retriever or reranker
            - text (str):      Full text content of the retrieved chunk
            - metadata (dict): Complete metadata dictionary from the node
        error (str): Emitted when an exception occurs during retrieval.
    """

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, index, query_text, reranker=None):
        """
        Initialize the retrieval worker.

        Args:
            index: A LlamaIndex VectorStoreIndex instance to retrieve from.
            query_text: The user's natural language search query string.
            reranker: Optional SentenceTransformerRerank postprocessor. When provided,
                      the retrieved nodes are re-scored using a cross-encoder model
                      for significantly improved ranking quality.
        """
        super().__init__()
        self.index = index
        self.query_text = query_text
        self.reranker = reranker

    def run(self):
        """
        Execute the pure retrieval pipeline in a background thread.

        Pipeline steps:
            1. Build a VectorIndexRetriever with similarity_top_k from config
            2. Retrieve the top-k most similar nodes from the vector store
            3. (Optional) Apply cross-encoder reranking for improved precision
            4. Extract metadata and text from each scored node
            5. Emit the structured results via the finished signal

        The entire pipeline runs without any LLM calls, making it
        orders of magnitude faster than the full RAG query pipeline.
        """
        try:
            # Step 1: Build retriever from the vector index.
            # similarity_top_k controls how many candidate chunks are pulled
            # from ChromaDB before optional reranking narrows them down.
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=cfg.similarity_top_k.value,
            )

            # Step 2: Retrieve semantically similar nodes.
            # This performs embedding-based similarity search in ChromaDB,
            # comparing the query embedding against stored document embeddings.
            scored_nodes = retriever.retrieve(self.query_text)

            # Step 3: Apply reranker if available.
            # The reranker uses a cross-encoder (e.g. BGE-reranker-large) to
            # re-score the candidate nodes against the actual query text.
            # Cross-encoder scoring is far more accurate than embedding cosine
            # similarity alone, but requires pairwise inference per candidate.
            if self.reranker and scored_nodes:
                query_bundle = QueryBundle(query_str=self.query_text)
                scored_nodes = self.reranker.postprocess_nodes(
                    scored_nodes, query_bundle=query_bundle
                )

            # Step 4: Build structured result list from raw nodes.
            # Each result dict contains everything the UI needs to render
            # a result card without further processing.
            results = []
            for node_with_score in scored_nodes:
                node = node_with_score.node
                metadata = node.metadata or {}

                results.append({
                    "title": (
                        metadata.get("file_name")
                        or metadata.get("source")
                        or "Untitled"
                    ),
                    "file_path": metadata.get("file_path"),
                    "score": (
                        node_with_score.score
                        if node_with_score.score is not None
                        else 0.0
                    ),
                    "text": node.get_content(),
                    "metadata": metadata,
                })

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))
