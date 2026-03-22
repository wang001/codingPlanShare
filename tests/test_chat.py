import requests
import json

# 测试chat/completions接口
url = "http://localhost:3000/api/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "api-key": "pD_hSDriLUrpLLx_5BbimXUaRG1WwVutjQxP7TYi048"
}
data = {
    "model": "modelscope/MiniMax/MiniMax-M2.5",
    "messages": [
        {
            "role": "user",
            "content": "Hello, how are you?"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print("Status Code:", response.status_code)
print("Response Text:", response.text)
try:
    print("Response JSON:", response.json())
except Exception as e:
    print("JSON Decode Error:", e)
