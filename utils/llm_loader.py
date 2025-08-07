from llama_index.llms.ollama import Ollama

# 0. Define our model
def llm_model():
    llm = Ollama(
        model="llama2:7b", # replace the model with whatever llama model u want
    )
    return llm