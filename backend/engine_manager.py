import chromadb
import os
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
from PySide6.QtCore import QThread, Signal
from ui.config import cfg
from llama_index.core.postprocessor import SentenceTransformerRerank

def storage_graph(persist_dir="./storageContext", vector_store=None):
    """Check if storageContext exist if not create one"""
    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        # Load existing index
        print("Found existing storage, loading...")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir, vector_store=vector_store)
        return storage_context, True
    else:
        # Create new graph storage
        print("No storage found, creating new...")
        os.makedirs(persist_dir, exist_ok=True)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return storage_context, False

class EngineManager(QThread):
    progress = Signal(str)
    llm_ready = Signal()
    db_ready = Signal()
    engine_ready = Signal(object)
    # Emits (index, reranker) when the vector index is built but before
    # the LLM query engine is created. This allows the pure retrieval
    # pipeline to become available earlier than the full RAG pipeline.
    index_ready = Signal(object, object)
    need_data = Signal(str)
    error = Signal(str)
    critical_error = Signal(str)

    # Granular step-level progress for the Progress Notification Dialog.
    # Args: step_index (int), total_steps (int), message (str)
    step_progress = Signal(int, int, str)
    # Emitted once at the start of run() with the total number of steps.
    pipeline_started = Signal(int)
    # Emitted when the entire pipeline completes without error.
    pipeline_finished = Signal()

    # Total number of discrete steps in the initialization pipeline
    TOTAL_STEPS = 7

    def run(self):
        try:
            # Notify listeners that the pipeline is starting
            self.pipeline_started.emit(self.TOTAL_STEPS)

            ## Step 0: Load LLM Model ##
            self.step_progress.emit(0, self.TOTAL_STEPS, "Loading LLM (Llama 3.1:8B)…")
            Settings.llm = LlamaCPP(
                model_path=cfg.llmModelPath.value,
                temperature=cfg.temperature.value,
                max_new_tokens=cfg.max_new_tokens.value,
                context_window=8192,
                model_kwargs={
                    "n_gpu_layers": -1,
                    "main_gpu": 0,
                    "n_ctx": 8192,
                    "n_batch": 256,
                    "use_mmap": True,
                    "use_mlock": True,
                },
                verbose=cfg.verbose.value,
            )
            self.llm_ready.emit()

            ## Step 1: Load Embedding Model ##
            self.step_progress.emit(1, self.TOTAL_STEPS, "Loading embedding model…")
            Settings.embed_model = HuggingFaceEmbedding(
                model_name=cfg.embedModelPath.value,
                device="cuda",
                trust_remote_code=True,
                show_progress_bar=True
                )

            ## Step 2: Initialize Reranker ##
            self.step_progress.emit(2, self.TOTAL_STEPS, "Initializing reranker…")
            self.progress.emit("Initializing reranker...")
            reranker = SentenceTransformerRerank(
                model=cfg.rerankerModelPath.value,
                top_n=cfg.top_n.value,
                device="cuda"
            )

            ## Step 3: Connect to ChromaDB ##
            self.step_progress.emit(3, self.TOTAL_STEPS, "Connecting to ChromaDB…")
            chroma_client = chromadb.PersistentClient(path="./chroma_db")
            chroma_collection = chroma_client.get_or_create_collection("index")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

            # Check if "./storageContext"
            storage_context, existing = storage_graph("./storageContext", vector_store)
            self.db_ready.emit()

            get_collection = chroma_collection.count()
            data_paths = cfg.dataFolders.value or []

            if not data_paths and get_collection == 0:
                self.critical_error.emit(
                    "No data folders nor index found. Please locate your data folder to start indexing or import your index collection.")
                return

            ## Step 4: Build or load document index ##
            if not data_paths and get_collection > 0:
                self.step_progress.emit(4, self.TOTAL_STEPS, f"Loading existing index ({get_collection} items)…")
                self.progress.emit(f"Found existing collection with {get_collection} items.")
                index = load_or_create_index(vector_store, storage_context, data_path=data_paths, callback=self.progress.emit)
            else:
                self.step_progress.emit(4, self.TOTAL_STEPS, f"Indexing documents from {len(data_paths)} folder(s)…")
                self.progress.emit(f"Building new index from {len(data_paths)} folder(s)")
                index = load_or_create_index(vector_store, storage_context, data_path=data_paths, callback=self.progress.emit)

            ## Step 5: Expose retrieval pipeline ##
            self.step_progress.emit(5, self.TOTAL_STEPS, "Retrieval pipeline ready")
            # Expose the raw index and reranker for the pure retrieval pipeline.
            # This signal fires before the LLM query engine is created, so the
            # Document Search feature becomes usable while the heavier LLM-based
            # CitationQueryEngine is still being initialized.
            self.index_ready.emit(index, reranker)

            ## Step 6: Create CitationQueryEngine ##
            self.step_progress.emit(6, self.TOTAL_STEPS, "Initializing query engine…")
            self.progress.emit("Initializing query engine...")
            query_engine = CitationQueryEngine.from_args(
                index,
                similarity_top_k=cfg.similarity_top_k.value,
                node_postprocessors=[reranker],
                citation_chunk_size=cfg.citation_chunk_size.value,
                streaming=True,
                verbose=True,
                response_mode="compact"
            )

            self.engine_ready.emit(query_engine)

            # Notify that the full pipeline completed successfully
            self.pipeline_finished.emit()
        except Exception as e:
            self.error.emit(str(e))
