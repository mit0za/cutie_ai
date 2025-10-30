import os
from typing import Union, List
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from PySide6.QtCore import QMetaObject, Qt
from utils.metadata_extractor import MetaDataExtractor

# TODO[Engine]: Re-enable multiprocessing once GUI-safe process spawning is implemented.
# Issue: PySide6 event loop + multiprocessing.spawn causes deadlock on Windows.
# Suggested fix: Move ingestion to standalone process via multiprocessing.Process or subprocess.Popen().


def load_or_create_index(vector_store, storage_context, data_path: Union[str, List[str]] = "./data", callback=None):
    """
    Load an index from the vector store if it has data else build a new index.
    Supports multiple data paths.
    """

    def log(msg: str):
        print(msg)
        if callback:
            try:
                if hasattr(callback, "__self__") and hasattr(callback.__self__, "metaObject"):
                    QMetaObject.invokeMethod( 
                        callback.__self__,
                        callback.__name__ if hasattr(callback, "__name__") else "emit",
                        Qt.QueuedConnection,
                        args=(msg,)
                    )
                else:
                    callback(msg)
            except Exception as e:
                print(f"[Callback Error] {e}")

    # Normalize and validate data paths
    if isinstance(data_path, str):
        data_paths = [data_path]
    else:
        data_paths = data_path

    valid_paths = [p for p in data_paths if os.path.exists(p)]
    if not valid_paths:
        log("[Warning] No valid data folders found. Using ./data as fallback.")
        valid_paths = ["./data"]

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

        # Ingestion pipeline
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=512, chunk_overlap=50, include_metadata=True),
                MetaDataExtractor()
            ]
        )

        log("Running ingestion pipeline...")
        nodes = pipeline.run(documents=documents, show_progress=True)
        pipeline.cache.persist("./cache") # save hashes for next indexing
        log(f"Pipeline produced {len(nodes)} nodes")

        if nodes:
            log(f"Sample metadata from first node: {nodes[0].metadata.get("excerpt_keywords", []) [:10]}")
        
        log("Starting VectoreStoreIndex")
        index = VectorStoreIndex(nodes, storage_context=storage_context, show_progress=True)
        storage_context.persist(persist_dir="./storageContext")
        log("Index successfully built")
        return index
    else:
        log(f"Found {get_collection} in collection. Loading index...")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            show_progress=True
        )
        log(f"BOOM LET'S GO!!!")
        return index
        
