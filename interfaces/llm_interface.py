from utils.llm_loader import get_ollama_model

def set_llm(source, model=None, api_key=None):
    """
    Set the LLM globally. This should support any models pull from ollama not just llama

    Params:
        source: "ollama" | "openapi" #Currently not support
        model: "llama2:7b" 
        api_key: api keys for your online models
    """
    match source:
        case "ollama":
            model = get_ollama_model(model)
            return model
        case "openapi":
            print("OpenApi support will come later")
            return None
        case _:
            print("This program only support llama models for now.")
            return None