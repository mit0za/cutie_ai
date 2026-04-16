import json
from llama_index.core.llama_dataset import (
    LabelledRagDataset,
    CreatedBy,
    CreatedByType,
    LabelledRagDataExample,
)
from llama_index.core import Settings, StorageContext, VectorStoreIndex
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.evaluation import RelevancyEvaluator, FaithfulnessEvaluator
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Define path for llms
LLM_PATH = "models/Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf"
EMBEDED_PATH = "./models/qwen3-embedding-0.6b"

# Set up llms
Settings.llm = LlamaCPP(
    model_path=LLM_PATH,
    temperature=0.1,
    model_kwargs={
        "n_gpu_layers": -1,
        "repeat_penalty": 1.1,
        "n_ctx": 8192},
    verbose=False
)

Settings.embed_model = HuggingFaceEmbedding(
    model_name = EMBEDED_PATH,
    device="cuda"
)

# Set up vectorDB
db = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = db.get_or_create_collection("index")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

storage_context = StorageContext.from_defaults(vector_store=vector_store, persist_dir="./storageContext")
index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

query_engine = index.as_query_engine()

# Load dataset
def load_dataset(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)

    # Put dataset into order
    dataSet = []
    for item in data:
        example = LabelledRagDataExample(
            query=item["query"],
            query_by=CreatedBy(type=CreatedByType.HUMAN),
            reference_answer=item["reference_answer"],
            reference_contexts=item["reference_contexts"],
            reference_by=CreatedBy(type=CreatedByType.HUMAN)
        )
        dataSet.append(example)

    return LabelledRagDataset(examples=dataSet)

rag_dataset = load_dataset("dataset.json")

# Assuming 'query_engine' is the one from your EngineController
faithfulness_evaluator = FaithfulnessEvaluator(llm=Settings.llm)
relevancy_evaluator = RelevancyEvaluator(llm=Settings.llm)

print(f"Loaded {len(rag_dataset.examples)} offline test cases.\n")

for example in rag_dataset.examples:
    print(f"Testing Query: {example.query}")
    
    # Run the actual RAG pipeline
    response = query_engine.query(example.query)
    
    # Evaluate Faithfulness (Did the AI hallucinate?)
    eval_result = faithfulness_evaluator.evaluate_response(response=response)
    
    print(f"Passing: {eval_result.passing}")
    print(f"Feedback: {eval_result.feedback}")
    # print("-" * 30)