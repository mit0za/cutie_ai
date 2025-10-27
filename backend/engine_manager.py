from llama_index.llms.ollama import Ollama
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
from PySide6.QtCore import QThread, Signal
from ui.config import cfg
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
            # Add llama ll model via Ollama to llamaindex.settings
            Settings.llm = Ollama(source="ollama", model="llama3.1:8b", request_timeout=600.0)
            # Add Qwen3 embeded model via Ollama to llamaindex.setting
            Settings.embed_model = OllamaEmbedding(model_name="dengcao/Qwen3-Embedding-0.6B:F16", embed_batch_size=64) # Change to lower batch size for prod
            self.llm_ready.emit()

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
            query_engine = CitationQueryEngine(
                index,
                similarity_top_k=10,
                citation_chunk_size=512,
                streaming=True,
                verbose=True
            )
            # self.progress.emit("Engine Initialized successfully")
            self.engine_ready.emit(query_engine)
        except Exception as e:
            self.error.emit(str(e))