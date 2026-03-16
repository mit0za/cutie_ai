import chromadb
import os
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine, RetrieverQueryEngine, RouterQueryEngine
from PySide6.QtCore import QThread, Signal
from ui.config import cfg
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.prompts import PromptTemplate

# Project root (resolve relative to this file)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    retriever_ready = Signal(object)  # Pure semantic retrieval, no LLM
    need_data = Signal(str)
    error = Signal(str)
    critical_error = Signal(str)

    def run(self):
        try:
            ## Add LLM Model ##
            llm_candidates = [
                "Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf",
                "Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
            ]
            llm_path = None
            for name in llm_candidates:
                p = os.path.join(_PROJECT_ROOT, "models", name)
                if os.path.exists(p):
                    llm_path = p
                    break
            if not llm_path:
                self.critical_error.emit(
                    f"LLM 模型文件不存在: {llm_path}\n\n请从 https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF 下载 Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf 并放入 models 文件夹。")
                return
            Settings.llm = LlamaCPP(
<<<<<<< HEAD
                model_path="models/Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf",
                temperature=cfg.temperature.value,
                max_new_tokens=cfg.max_new_tokens.value,
=======
                model_path=llm_path,
                temperature=0.5,
                max_new_tokens=256,
                # max_new_tokens=512,
                # max_new_tokens=1024,
>>>>>>> 6d7d314 (feat: Task 1 & 2 - Pure semantic retrieval + Document Search view)
                context_window=8192,
                model_kwargs={
                    "n_gpu_layers": -1,
                    "main_gpu": 0,
                    "n_ctx": 8192,
                    "n_batch": 256,
                    "use_mmap": True,
                    "use_mlock": True,
                },
                verbose=cfg.verbose.value
            )
            self.llm_ready.emit()

            ## Add Embedding Model ##
            embed_path = os.path.join(_PROJECT_ROOT, "models", "qwen3-embedding-0.6b")
            has_embed_local = os.path.exists(embed_path) and os.path.isfile(os.path.join(embed_path, "config.json"))
            embed_model_name = embed_path if has_embed_local else "Qwen/Qwen3-Embedding-0.6B"
            embed_device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
            Settings.embed_model = HuggingFaceEmbedding(
                model_name=embed_model_name,
                device=embed_device
            )
            
            self.progress.emit("Initializing reranker...")
            rerank_path = os.path.join(_PROJECT_ROOT, "models", "bge-reranker-large")
            has_rerank_local = os.path.exists(rerank_path) and os.path.isfile(os.path.join(rerank_path, "config.json"))
            rerank_model = rerank_path if has_rerank_local else "BAAI/bge-reranker-large"
            rerank_device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
            reranker = SentenceTransformerRerank(
<<<<<<< HEAD
                model="./models/bge-reranker-large",
                top_n=cfg.top_n.value,
                device="cuda"
=======
                model=rerank_model,
                top_n=3, # Precise Query
                # top_n=10, # Broad Query
                device=rerank_device
>>>>>>> 6d7d314 (feat: Task 1 & 2 - Pure semantic retrieval + Document Search view)
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

            # Fallback: use ./data when no folder configured and no existing index
            if not data_paths and get_collection == 0:
                os.makedirs("./data", exist_ok=True)
                data_paths = ["./data"]
                if not os.listdir("./data"):
                    self.critical_error.emit(
                        "No data folders nor index found. Please add documents (PDF, TXT, etc.) to the ./data folder, or use Settings to locate your data folder.")
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
                similarity_top_k=cfg.similarity_top_k.value,
                node_postprocessors=[reranker],
                citation_chunk_size=cfg.citation_chunk_size.value,
                streaming=True,
                verbose=True,
                response_mode="compact"
            )

            self.engine_ready.emit(query_engine)

            # Pure semantic retriever (no LLM) - for Document Search view
            # VectorIndexRetriever does not support node_postprocessors; returns raw nodes
            self.progress.emit("Initializing pure retriever...")
            retriever = index.as_retriever(similarity_top_k=20)
            self.retriever_ready.emit(retriever)
        except Exception as e:
            self.error.emit(str(e))
