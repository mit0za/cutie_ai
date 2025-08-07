from utils.llm_loader import llm_model
from llama_index.core import Settings, SimpleDirectoryReader
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.ollama import OllamaEmbedding

"""
1.We first define our model because if we don't
llamaindex will default to openAi
"""
Settings.llm = llm_model()

# 2. We then define our embedding model
Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text:latest"
)

# 3. We define where our data is so the AI will know where to look
doc = SimpleDirectoryReader("./data").load_data()


"""4. It then take our documents and split them into nodes. I know what you're thinking.
Isn't that just indexing? Well yes, but also no. 
"""
vector_index = VectorStoreIndex.from_documents(doc)

# 5. Make it searchable
query_engine = vector_index.as_query_engine()

# 6. We ask question
resp = query_engine.query("What was her majesty please about?")

# 7. We print answer
print(resp)

## 8.??
## 9. Profit