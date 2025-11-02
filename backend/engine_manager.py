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
from llama_index.core.tools import QueryEngineTool

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
                max_new_tokens=512,
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

            self.progress.emit("Initializing reranker...")
            reranker = SentenceTransformerRerank(
                model="./models/bge-reranker-large",
                top_n=3,
                device="cuda"
            )

            # For precise query we want narrow down the search
            precise_query_engine = CitationQueryEngine.from_args(
                index,
                similarity_top_k=10,
                citation_chunk_size=256,
                streaming=True,
                verbose=True,
                response_mode="compact"
            )
            #self.engine_ready.emit(precise_query_engine)

            precise_tool = QueryEngineTool.from_defaults(
                query_engine=precise_query_engine,
                description=(
                    "Best suited for short, factual, or well-defined questions where the answer "
                    "exists as a specific statement in the text. Use this for precise queries such as "
                    "'who founded...', 'what year...', 'when did...', 'where is...', or 'how many...'. "
                    "Focus on accuracy and concise citation."
                ),
            )

            # For broad query we want to get as many relevant documents as possible
            # then use reranker to filter them out
            broad_query_engine = CitationQueryEngine.from_args(
                index,
                similarity_top_k=20,
                node_postprocessors=[reranker],
                citation_chunk_size=512,
                streaming=True,
                verbose=True,
                response_mode="compact"
            )

            broad_tool = QueryEngineTool.from_defaults(
                query_engine=broad_query_engine,
                description=(
                    "Use this for open-ended, descriptive, or multi-fact questions that require "
                    "summarization or reasoning across multiple documents. Ideal for 'why', "
                    "'how', or 'describe' questions, or when the topic spans many sources "
                    "or includes evolving information such as costs, opinions, or timelines."
                )
            )

            # Agent workflow
            self.progress.emit("Initializing router query engine...")
            query_engine = RouterQueryEngine.from_defaults(
                query_engine_tools=[
                    precise_tool,
                    broad_tool
                ],
                llm=Settings.llm
            )
            self.engine_ready.emit(query_engine)
        except Exception as e:
            self.error.emit(str(e))