import os
import chromadb
from llama_index.core import Settings, StorageContext, VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import (
    SummaryExtractor, QuestionsAnsweredExtractor, TitleExtractor, KeywordExtractor
)
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.embeddings.huggingface import HuggingFaceEmbedding



def log(msg: str):
    print(f"[test] {msg}", flush=True)

def setup_storage_context(persist_dir="./storageContext", vector_store=None):
    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        # Load an existing index
        print("[test] Found existing storage, loading...")
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir,
            vector_store=vector_store
        )
        return storage_context, True
    else:
        # Create a new storage context for first-time indexing
        print("[test] No storage found, creating new...")
        os.makedirs(persist_dir, exist_ok=True)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        return storage_context, False

def load_or_create_index(vector_store, storage_context, data_path="./data"):
     # Normalize and validate data paths
    if isinstance(data_path, str):
        data_paths = [data_path]
    else:
        data_paths = data_path

    valid_paths = [p for p in data_paths if os.path.exists(p)]
    if not valid_paths:
        log("[Warning] No valid data folders found. Using ./data as fallback.")
        valid_paths = ["./data"]

    # splitter
    text_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=50, include_metadata=True)

    # define our extractors
    extractors = [
        TitleExtractor(nodes=5),
        QuestionsAnsweredExtractor(questions=3),
        SummaryExtractor(summaries=["self"]),
        KeywordExtractor(keywords=10),
    ]

    # cache folder
    cache = IngestionCache(dir="./cache")

    # check cpu core so we can do parallel processing which hopefully
    # speed up the parsing time
    workers = min(4, os.cpu_count() // 2)

    # Count current collection
    get_collection = vector_store._collection.count()

    if get_collection == 0:
        log(f"Index empty. Rebuilding from {valid_paths} (this may take a while)...")

        documents = []
        for path in valid_paths:
            log(f"Loading documents from: {path}")
            reader = SimpleDirectoryReader(path,recursive=True)
            docs = reader.load_data(show_progress=True)
            log(f"Loaded {len(docs)} documents from {path}")
            documents.extend(docs)

        log(f"Total {len(documents)} documents loaded from all paths.")

        ############### METHOD 1 ############
        # Ingestion pipeline ######
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=512, chunk_overlap=50, include_metadata=True),
                TitleExtractor(nodes=5),
                # SummaryExtractor(summaries=["self"]),
                # KeywordExtractor(keywords=10),
                # QuestionsAnsweredExtractor(questions=3),
            ]
        )
        nodes = pipeline.run(documents=documents, show_progress=True)



        ############### METHOD 2 ############
        # parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20, include_metadata=True)
        # nodes = parser.get_nodes_from_documents(documents, show_progress=True)

        log("Running ingestion pipeline...")
        nodes = pipeline.run(documents=documents, show_progress=True)
        pipeline.cache.persist("./cache") # save hashes for next indexing
        log(f"Pipeline produced {len(nodes)} nodes")

        if nodes:
            log(f"Sample metadata from first node: {nodes[0].metadata}")
        
        log("Starting VectoreStoreIndex")
        index = VectorStoreIndex(nodes, storage_context=storage_context, show_progress=True)
        storage_context.persist(persist_dir="./storageContext")
        log("Index successfully built")

        return index
    else:
        log(f"Found {get_collection} in collection. Loading index...")
        return VectorStoreIndex.from_vector_store(vector_store)
    
def main():
    # Settings.llm = Ollama(model="llama3.1:8b", request_timeout=600)
    # Settings.embed_model = OllamaEmbedding(model_name="qwen3-embedding:0.6b")
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
        verbose=True
        )
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="./models/qwen3-embedding-0.6b", 
        # model_name = "Qwen/Qwen3-Embedding-0.6B",
        device="cpu"
        )
    chroma_client = chromadb.PersistentClient(path="./chroma_db") 
    chroma_collection = chroma_client.get_or_create_collection("index")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    # storage_context = StorageContext.from_defaults(vector_store=vector_store)
    storage_context, existing = setup_storage_context("./storageContext", vector_store)
    data_path = "./data/1854"
    index = load_or_create_index(vector_store, storage_context, data_path=data_path)
    print("YESSSSSSSSSSSSSSSSSSSSSSSSSSSSSS")

    # query_engine = index.as_query_engine(similarity_top_k=3)
    # resp = query_engine.query("What happened in 1841?")
    # print("\n=== Sample Query Result ===")
    # print(resp)

main()