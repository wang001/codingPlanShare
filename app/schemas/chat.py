from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    role: str = Field(
        ...,
        description="消息角色：user（用户）/ assistant（助手）/ system（系统提示词）",
        example="user",
    )
    content: str = Field(..., description="消息内容", example="你好，请介绍一下你自己。")


class ChatCompletionRequest(BaseModel):
    model: str = Field(
        ...,
        description=(
            "模型名称，格式为 `provider/真实模型名`。"
            "第一段为 provider（须在系统白名单内），其余部分为传给厂商的真实模型名。"
            "例：modelscope/moonshotai/Kimi-K2.5、zhipu/glm-4、mock/test-model"
        ),
        example="modelscope/moonshotai/Kimi-K2.5",
    )
    messages: List[Message] = Field(..., description="消息列表，按对话顺序排列")
    temperature: Optional[float] = Field(default=0.7, description="采样温度（0~2），值越高输出越随机", example=0.7)
    max_tokens: Optional[int] = Field(default=1000, description="最大生成 token 数", example=1000)
    top_p: Optional[float] = Field(default=1.0, description="nucleus sampling 概率阈值（0~1）", example=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, description="频率惩罚（-2~2），减少重复词语", example=0.0)
    presence_penalty: Optional[float] = Field(default=0.0, description="存在惩罚（-2~2），鼓励提及新话题", example=0.0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "model": "modelscope/moonshotai/Kimi-K2.5",
                "messages": [
                    {"role": "system", "content": "你是一个有帮助的助手。"},
                    {"role": "user", "content": "你好！"},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            }
        }
    }


class Choice(BaseModel):
    index: int = Field(..., description="结果序号，从 0 开始")
    message: Message = Field(..., description="模型生成的消息，role 固定为 assistant")
    finish_reason: str = Field(..., description="停止原因：stop（正常结束）/ length（达到 max_tokens）/ content_filter（内容过滤）")


class Usage(BaseModel):
    prompt_tokens: int = Field(..., description="输入消息消耗的 token 数")
    completion_tokens: int = Field(..., description="模型生成内容消耗的 token 数")
    total_tokens: int = Field(..., description="总 token 数（prompt_tokens + completion_tokens）")


class EmbeddingsRequest(BaseModel):
    model: str = Field(
        ...,
        description="模型名称，格式为 `provider/真实模型名`",
        example="modelscope/text-embedding-v3",
    )
    input: str = Field(..., description="需要向量化的文本")


class ChatCompletionResponse(BaseModel):
    id: str = Field(..., description="本次响应的唯一 ID")
    object: str = Field(default="chat.completion", description="响应类型，固定值 chat.completion")
    created: int = Field(..., description="创建时间戳（Unix 秒）")
    model: str = Field(..., description="实际使用的模型名称")
    choices: List[Choice] = Field(..., description="生成结果列表（通常只有 1 个）")
    usage: Usage = Field(..., description="本次请求的 token 用量统计")
