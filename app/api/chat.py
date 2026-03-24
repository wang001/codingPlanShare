import time
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.auth_service import AuthService
from app.services.points_service import PointsService
from app.services.router_service import RouterService
from app.services.key_service import KeyService
from app.models.call_log import CallLog

logger = logging.getLogger(__name__)

router = APIRouter()


def get_platform_key(
    api_key: Optional[str] = Header(None, alias="api-key"),
    authorization: Optional[str] = Header(None),
) -> str:
    """
    从 Header 提取平台调用密钥。
    支持：api-key: <key>  或  Authorization: Bearer <key>
    """
    if api_key:
        return api_key
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少认证 Header（api-key 或 Authorization: Bearer <key>）",
    )


def _handle_vendor_error(db: Session, exc: Exception, key_id: int):
    """
    识别厂商异常并标记密钥状态：
    - 429 → mark_key_rate_limited（冷却 1h，可自动恢复）
    - 401/403 → mark_key_invalid（需人工更换）
    """
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            KeyService.mark_key_rate_limited(db, key_id)
        elif code in (401, 403):
            KeyService.mark_key_invalid(db, key_id)


def _write_call_log(db: Session, user_id: int, key_id: int, model: str,
                    success: bool, error_msg: str = None):
    log = CallLog(
        user_id=user_id,
        provider_key_id=key_id,
        model=model,
        status=1 if success else 0,
        error_msg=error_msg,
        ip="127.0.0.1",
    )
    db.add(log)
    db.commit()


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    summary="聊天完成（Chat Completions）",
    description=(
        "OpenAI Chat Completions 兼容接口，通过平台路由到各厂商 LLM。\n\n"
        "**认证**：`api-key: <平台密钥>` 或 `Authorization: Bearer <平台密钥>`。\n\n"
        "**模型格式**：`provider/真实模型名`，例如 `mock/test-model`、`modelscope/moonshotai/Kimi-K2.5`。\n\n"
        "**计费**：每次成功调用扣减 10 积分，失败自动回滚。"
    ),
)
async def chat_completions(
    request: ChatCompletionRequest,
    platform_key: str = Depends(get_platform_key),
    db: Session = Depends(get_db),
):
    # 验证平台密钥
    key = AuthService.verify_api_key(db, platform_key)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API密钥")

    user_id = key.user_id
    points_to_deduct = 10

    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

    model_dump_result = request.model_dump()
    route_result = RouterService.route_request(db, request.model, model_dump_result)
    if not route_result:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有可用的厂商密钥")

    provider   = route_result['provider']
    key_id     = route_result['key_id']
    vendor_key = route_result['key']

    logger.info(f"Routing to provider={provider} key_id={key_id} model={request.model}")

    provider_instance = RouterService.create_provider_instance(provider, vendor_key)
    if not provider_instance:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"不支持的厂商: {provider}")

    try:
        response = await provider_instance.chat_completion(
            model=route_result['request']['model'],
            messages=route_result['request']['messages'],
            temperature=route_result['request']['temperature'],
            max_tokens=route_result['request']['max_tokens'],
        )
        KeyService.update_key_usage(db, key_id)
        PointsService.confirm_deduct(db, user_id, points_to_deduct, 1, key_id, request.model, f"Chat with {provider}")
        _write_call_log(db, user_id, key_id, request.model, success=True)
        return ChatCompletionResponse(**response)

    except Exception as e:
        _handle_vendor_error(db, e, key_id)
        _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))

        # 重试（最多 1 次）
        from app.config.settings import settings
        max_retry = settings.key_management.get('max_retry', 1)

        for attempt in range(max_retry):
            logger.warning(f"Retrying chat, attempt {attempt + 1}")
            route_result = RouterService.route_request(db, request.model, model_dump_result)
            if not route_result:
                break

            provider   = route_result['provider']
            key_id     = route_result['key_id']
            vendor_key = route_result['key']

            provider_instance = RouterService.create_provider_instance(provider, vendor_key)
            if not provider_instance:
                continue

            try:
                response = await provider_instance.chat_completion(
                    model=route_result['request']['model'],
                    messages=route_result['request']['messages'],
                    temperature=route_result['request']['temperature'],
                    max_tokens=route_result['request']['max_tokens'],
                )
                KeyService.update_key_usage(db, key_id)
                PointsService.confirm_deduct(db, user_id, points_to_deduct, 1, key_id, request.model, f"Chat with {provider}")
                _write_call_log(db, user_id, key_id, request.model, success=True)
                return ChatCompletionResponse(**response)

            except Exception as retry_e:
                _handle_vendor_error(db, retry_e, key_id)
                _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(retry_e))
                continue

        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"厂商API调用失败: {str(e)}",
        )


@router.post("/completions/stream")
async def chat_completions_stream(
    request: ChatCompletionRequest,
    platform_key: str = Depends(get_platform_key),
    db: Session = Depends(get_db),
):
    """聊天完成（流式 SSE）"""
    key = AuthService.verify_api_key(db, platform_key)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API密钥")

    user_id = key.user_id
    points_to_deduct = 10

    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

    route_result = RouterService.route_request(db, request.model, request.model_dump())
    if not route_result:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有可用的厂商密钥")

    provider   = route_result['provider']
    key_id     = route_result['key_id']
    vendor_key = route_result['key']

    provider_instance = RouterService.create_provider_instance(provider, vendor_key)
    if not provider_instance:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"不支持的厂商: {provider}")

    KeyService.update_key_usage(db, key_id)

    async def generate():
        try:
            async for chunk in provider_instance.chat_completion_stream(
                model=route_result['request']['model'],
                messages=route_result['request']['messages'],
                temperature=route_result['request']['temperature'],
                max_tokens=route_result['request']['max_tokens'],
            ):
                yield chunk

            PointsService.confirm_deduct(db, user_id, points_to_deduct, 1, key_id, request.model, f"Stream with {provider}")
            _write_call_log(db, user_id, key_id, request.model, success=True)

        except Exception as e:
            _handle_vendor_error(db, e, key_id)
            _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
            PointsService.rollback_points(db, user_id, points_to_deduct)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
