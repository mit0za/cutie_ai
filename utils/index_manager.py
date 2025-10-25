from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from utils.metadata_extractor import create_metadata_fn
from PySide6.QtCore import QMetaObject, Qt


def load_or_create_index(vector_store, storage_context, data_path="./data", callback=None):
    """
    Load an index from the vector store if it has data else build a new index.
    Now includes metadata extraction from filenames.
    """

    # Basically this send the our string to main thread. Don't ask me how
    def log(msg: str):
        print(msg)
        if callback:
            try:
                # If it's a Qt Signal (has .emit), invoke on main thread
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


    # Get how many collections in the db
    get_collection = vector_store._collection.count()
    
    if get_collection == 0:
        log(f"[Rebuild] Index empty. Rebuilding from {data_path} (this may take a while)...")
        
        # Load raw docs with metadata extraction
        documents = SimpleDirectoryReader(
            data_path, 
            recursive=True,
            file_metadata=create_metadata_fn()    
        ).load_data(show_progress=True)
        
        log(f"[Rebuild] Loaded {len(documents)} documents from {data_path}")
        
        # Parse into nodes with custom chunking
        parser = SentenceSplitter(
            chunk_size=1024, 
            chunk_overlap=20, 
            include_metadata=True  # Ensure metadata is included in nodes
        )
        
        nodes = parser.get_nodes_from_documents(documents, show_progress=True)
        log(f"[Rebuild] Parsed into {len(nodes)} nodes")
        
        # Display sample metadata for verification (optional)
        if nodes and len(nodes) > 0:
            sample_metadata = nodes[0].metadata
            log(f"[Rebuild] Sample metadata from first node: {sample_metadata}")
        
        return VectorStoreIndex.from_documents(
            nodes, 
            storage_context=storage_context, 
            show_progress=True
        )
    else:
        log(f"[Load] Found {get_collection} in collection. Loading index...")
        return VectorStoreIndex.from_vector_store(vector_store)
