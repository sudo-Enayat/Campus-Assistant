from llama_cpp import Llama
import os

model_path = "models/gemma-3-4b-it-Q4_K_M.gguf"

if not os.path.exists(model_path):
    print("❌ Model not found! Please download it first.")
    exit(1)

print("🔄 Loading model...")
llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
print("✅ Model loaded! Type 'quit' to exit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() in ['quit', 'exit', 'bye']:
        break
    
    response = llm(user_input, max_tokens=150, temperature=0.7)
    print(f"Gemma: {response['choices'][0]['text'].strip()}\n")
