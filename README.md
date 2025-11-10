# Dependencies

**Python Libraries**
```
pip install -r requirements.txt
```
# LLM
**Llama-3.1:8B GGUF**
```
https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF
```

**Embedding Model**
```
https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
```

**Reranking Model**
```
https://huggingface.co/BAAI/bge-reranker-large
```

# How to set up LLM
1. Create models directory<br>
Create a folder called ```models``` and put the raw model file ```Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf``` inside it.
2. Set up embedding model<br>
Inside the ```models``` directory, create a folder name ```qwen3-embedding-0.6b``` and place the embedding model files there.
3. Set up the reranking model<br>
Inside the ```models``` directory, create a folder named ```bge-reranker-large``` and place the reranking model files there.