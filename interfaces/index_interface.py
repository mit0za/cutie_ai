from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

def load_or_create_index(vector_store, storage_context, data_path="./data"):
    """Load an index from the vector store if it has data else build a new index."""

    # Get how many collection in the db
    get_collection = vector_store._collection.count()
    
    if get_collection == 0:
        print(f"[Rebuild] Index empty. Rebuilding from {data_path} (this may take a while)...")
        documents = SimpleDirectoryReader(data_path, recursive=True,).load_data()
        print(f"[Rebuild] Loaded {len(documents)} documents from {data_path}")
        return VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    else:
        print(f"[Load] Found {get_collection} in collection. Loading index...")
        return VectorStoreIndex.from_vector_store(vector_store)

