from interfaces.llm_interface import set_llm
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from interfaces.index_interface import load_or_create_index
import chromadb

# Set up LLM (ollama, llama2:7b)
Settings.llm = set_llm(source="ollama", model="llama2:7b")

# Define our embedding model
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text:latest")

# Set up vector database
chroma_client = chromadb.PersistentClient(path="./chroma_db") # For Prod
chroma_collection = chroma_client.get_or_create_collection("index")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = load_or_create_index(vector_store, storage_context, data_path="./data")

# Make the index searchable
query_engine = index.as_query_engine()

# 6. We ask question
resp = query_engine.query("What was her majesty please about?")

# 7. We print answer
print(resp)
