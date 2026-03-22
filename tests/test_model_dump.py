from app.schemas.chat import ChatCompletionRequest, Message

# 创建一个测试请求
request = ChatCompletionRequest(
    model="modelscope/MiniMax-M2.5",
    messages=[
        Message(role="user", content="Hello, how are you?")
    ],
    temperature=0.7,
    max_tokens=1000
)

# 测试model_dump()
dump_result = request.model_dump()
print("model_dump() result:")
print(dump_result)
print("\nType of messages:")
print(type(dump_result['messages']))
print("\nType of first message:")
print(type(dump_result['messages'][0]))
print("\nMessage content:")
print(dump_result['messages'][0])
