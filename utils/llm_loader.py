from llama_index.llms.ollama import Ollama

"""
This is where you load your ai model. U can either use api keys or
your own locally hosted ai model.
For this project we will be using llama ai from Meta
"""
def get_ollama_model(model):
    return Ollama(model=model)
