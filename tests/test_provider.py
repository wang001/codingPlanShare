from app.providers.modelscope import ModelScopeProvider

# 创建ModelScopeProvider实例
api_key = "ms-18f62d25-119b-4a61-a7cb-6f6aafc3fb04"
provider = ModelScopeProvider(api_key)

# 测试chat_completion
print("Testing chat_completion...")
try:
    response = provider.chat_completion(
        model="MiniMax/MiniMax-M2.5",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        temperature=0.7,
        max_tokens=1000
    )
    print("Success:", response)
except Exception as e:
    print("Error:", str(e))

# 测试embeddings
print("\nTesting embeddings...")
try:
    response = provider.embeddings(
        model="MiniMax/MiniMax-M2.5",
        input="Hello, how are you?"
    )
    print("Success:", response)
except Exception as e:
    print("Error:", str(e))
