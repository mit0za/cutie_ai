from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
from PySide6.QtCore import QThread, Signal
from ui.config import cfg
from llama_index.core.postprocessor import SentenceTransformerRerank
import chromadb
import os

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
    need_data = Signal(str)
    error = Signal(str)
    critical_error = Signal(str)

    def run(self):
        try:
            ## Add LLM Model ##
            Settings.llm = LlamaCPP(
                model_path="models/Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf",
                temperature=0.5,
                max_new_tokens=256,
                context_window=8192,
                model_kwargs={
                    "n_gpu_layers": -1,
                    "main_gpu": 0,
                    "n_ctx": 8192,
                    "n_batch": 256,
                    "use_mmap": True,
                    "use_mlock": True,
                },
                verbose=False
            )
            self.llm_ready.emit()

            ## Add Embedding Model ##
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="./models/qwen3-embedding-0.6b", 
                device="cuda"
                )
            
            self.progress.emit("Initializing reranker...")
            reranker = SentenceTransformerRerank(
                model="./models/bge-reranker-large",
                top_n=3,
                device="cuda"
            )

            # Set up vector database
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

            if not data_paths and get_collection > 0:
                self.progress.emit(f"Found existing collection with {get_collection} items.")
                index = load_or_create_index(vector_store, storage_context, data_path=data_paths, callback=self.progress.emit)
            else:
                self.progress.emit(f"Building new index from {len(data_paths)} folder(s)")
                index = load_or_create_index(vector_store, storage_context, data_path=data_paths, callback=self.progress.emit)

            self.progress.emit("Initializing query engine...")
            query_engine = CitationQueryEngine.from_args(
                index,
                similarity_top_k=20,
                node_postprocessors=[reranker],
                citation_chunk_size=512,
                streaming=True,
                verbose=True,
                response_mode="compact"
            )
            # self.progress.emit("Engine Initialized successfully")
            self.engine_ready.emit(query_engine)
        except Exception as e:
            self.error.emit(str(e))