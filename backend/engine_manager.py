from utils.llm_manager import set_llm
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from utils.index_manager import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
from utils.custom_queryEngine import create_metadata_query_engine, format_response,format_metadata
from PySide6.QtCore import QThread, Signal
import chromadb

class EngineManager(QThread):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)

    def run(self):
        try:
            # Set up LLM (ollama, llama2:7b)
            Settings.llm = set_llm(source="ollama", model="llama3.1:8b")
            # Define our embedding model
            Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text:latest")

            # Set up vector database
            chroma_client = chromadb.PersistentClient(path="./chroma_db") 
            chroma_collection = chroma_client.get_or_create_collection("index")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Load index
            index = load_or_create_index(vector_store, storage_context, data_path="./data", callback=self.progress.emit)

            # query engine
            query_engine = create_metadata_query_engine(
                index,
                similarity_top_k=3,
                citation_chunk_size=512,
                streaming=True,
                verbose=True
            )
            self.finished.emit(query_engine)
        except Exception as e:
            self.error.emit(str(e))