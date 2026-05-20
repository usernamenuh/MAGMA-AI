from models import EmbeddingRequest, EmbeddingResponse, EmbeddingData
from utils import get_model, count_tokens

def handle_embeddings(request: EmbeddingRequest):
    llm_model = get_model()
    
    if isinstance(request.input, str):
        texts = [request.input]
    elif isinstance(request.input, list) and all(isinstance(x, str) for x in request.input):
        texts = request.input
    else:
        raise ValueError("Invalid input format")
    
    embeddings_data = []
    total_tokens = 0
    
    for i, text in enumerate(texts):
        embedding = llm_model.embed(text)
        embeddings_data.append(EmbeddingData(object="embedding", index=i, embedding=embedding))
        total_tokens += count_tokens(text)
    
    return EmbeddingResponse(
        object="list",
        data=embeddings_data,
        model=request.model,
        usage={"prompt_tokens": total_tokens, "total_tokens": total_tokens}
    )
