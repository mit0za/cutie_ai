from interfaces.llm_interface import set_llm
from llama_index.core import Settings, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from interfaces.index_interface import load_or_create_index
from llama_index.core.query_engine import CitationQueryEngine
import chromadb

# Set up LLM (ollama, llama2:7b)
Settings.llm = set_llm(source="ollama", model="llama3.1:8b")

# Define our embedding model
# Settings.embed_model = OllamaEmbedding(model_name="dengcao/Qwen3-Embedding-0.6B:F16")
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text:latest")

# Set up vector database
chroma_client = chromadb.PersistentClient(path="./chroma_db") 
chroma_collection = chroma_client.get_or_create_collection("index")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = load_or_create_index(vector_store, storage_context, data_path="./data")

# Make the index searchable
# query_engine = index.as_query_engine(
    # streaming=True,
    # verbose=True,
    # response_mode="tree_summarize",
    # similarity_top_k = 10
    # node_postprocessors=[rerank]
# )

query_engine = CitationQueryEngine.from_args(index, similarity_top_k=3, citation_chunk_size=512, streaming=True)
# resp = index.as_retriever(similarity_top_k=20)
# # node = resp.retrieve("What was Her Majesty pleased about?")
# node = resp.retrieve("The new observatory that was built in Adelaide Univerity grounds. It is 13ft high with an additional 15ft for the dome. How much was it expected to cost?")
# for i, node in enumerate(node):
#     print(f"\n--- Chunk #{i+1} ---\n{node.text[:500]}")
# print(node)

resp = query_engine.query("What do you think about FRIEND tv-shows")
print(resp)
print(resp.source_nodes[0].node.get_text())
print(resp.source_nodes[1].node.get_text())
print(resp.source_nodes[2].node.get_text())
