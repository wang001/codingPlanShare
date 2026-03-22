import requests

# 测试流式响应接口
url = "http://localhost:3000/api/v1/chat/completions/stream"
headers = {
    "Content-Type": "application/json",
    "api-key": "pD_hSDriLUrpLLx_5BbimXUaRG1WwVutjQxP7TYi048"
}
data = {
    "model": "modelscope/MiniMax-M2.5",
    "messages": [
        {
            "role": "user",
            "content": "Hello, how are you?"
        }
    ]
}

print("Testing streaming response...")

# 流式获取响应
response = requests.post(url, headers=headers, json=data, stream=True)
print("Status Code:", response.status_code)
print("Response Content:")

for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
    if chunk:
        print(chunk, end="")

print("\nStreaming test completed.")
