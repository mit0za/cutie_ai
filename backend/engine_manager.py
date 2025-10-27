from llama_index.llms.ollama import Ollama
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
from PySide6.QtCore import QThread, Signal
from ui.config import cfg
import chromadb

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
            # self.progress.emit("Setting up LLM (Llama 3.1:8B)")
            # Set up LLM (ollama, llama2:7b)
            Settings.llm = Ollama(source="ollama", model="llama3.1:8b")
            # Define our embedding model
            Settings.embed_model = OllamaEmbedding(model_name="dengcao/Qwen3-Embedding-0.6B:F16")
            # self.progress.emit("LLM and Embedding model ready.")
            self.llm_ready.emit()

            # Set up vector database
            chroma_client = chromadb.PersistentClient(path="./chroma_db") 
            chroma_collection = chroma_client.get_or_create_collection("index")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            # self.progress.emit("Database connected successfully.")
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
            # Load index
            # data_path = cfg.dataFolders.value or ["./data"]
            # self.progress.emit(f"Loading {len(data_path)} folders(s): {", ". join(data_path)}")
            # index = load_or_create_index(vector_store, storage_context, data_path=data_path, callback=self.progress.emit)
        except Exception as e:
            self.error.emit(str(e))