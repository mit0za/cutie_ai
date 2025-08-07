from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

def load_or_create_index(vector_store, storage_context, data_path="./data"):
    """This check if vector exists"""
    try:
        index = VectorStoreIndex.from_vector_store(vector_store)
        return index
    except Exception:
        """This will rebuild new index"""
        documents = SimpleDirectoryReader(data_path).load_data()
        return VectorStoreIndex.from_documents(documents, storage_context=storage_context)
