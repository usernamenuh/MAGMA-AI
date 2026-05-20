import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use GPU 0 only

from llama_cpp import Llama
import time
start_time = time.time()

llm = Llama(
    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    n_gpu_layers=50,  
    n_ctx=4096,
    verbose=True
)

prompt = """[INST] <<SYS>>
Name the planets in the solar system?
<</SYS>> [/INST]
"""
end_time = time.time()
elapsed_time = end_time - start_time
print(f"elapsed time setup: {elapsed_time:.4f} seconds")

output = llm(prompt, max_tokens=350, echo=True)
response = output['choices'][0]['text'].split('[/INST]')[-1].strip()
print(response)
end_time_process = time.time()
elapsed_time_process = end_time_process - end_time
print(f"elapsed time process: {elapsed_time:.4f} seconds")