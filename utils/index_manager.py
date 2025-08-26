from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from utils.metadata_extractor import create_metadata_fn


def load_or_create_index(vector_store, storage_context, data_path="./data"):
    """
    Load an index from the vector store if it has data else build a new index.
    Now includes metadata extraction from filenames.
    """
    # Get how many collections in the db
    get_collection = vector_store._collection.count()
    
    if get_collection == 0:
        print(f"[Rebuild] Index empty. Rebuilding from {data_path} (this may take a while)...")
        
        # Load raw docs with metadata extraction
        documents = SimpleDirectoryReader(
            data_path, 
            recursive=True,
            file_metadata=create_metadata_fn()    
        ).load_data(show_progress=True)
        
        print(f"[Rebuild] Loaded {len(documents)} documents from {data_path}")
        
        # Parse into nodes with custom chunking
        parser = SentenceSplitter(
            chunk_size=1024, 
            chunk_overlap=20, 
            include_metadata=True  # Ensure metadata is included in nodes
        )
        
        nodes = parser.get_nodes_from_documents(documents, show_progress=True)
        print(f"[Rebuild] Parsed into {len(nodes)} nodes")
        
        # Display sample metadata for verification (optional)
        if nodes and len(nodes) > 0:
            sample_metadata = nodes[0].metadata
            print(f"[Rebuild] Sample metadata from first node: {sample_metadata}")
        
        return VectorStoreIndex.from_documents(
            nodes, 
            storage_context=storage_context, 
            show_progress=True
        )
    else:
        print(f"[Load] Found {get_collection} in collection. Loading index...")
        return VectorStoreIndex.from_vector_store(vector_store)
