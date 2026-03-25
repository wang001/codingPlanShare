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
from app.providers.modelscope import VendorResponseError

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


def _confirm_and_log(
    db: Session,
    user_id: int,
    key_id: int,
    model: str,
    provider: str,
    points: int,
):
    """
    原子化完成成功路径的三步操作：
      1. confirm_deduct（积分落库 / 入队）
      2. update_key_usage（更新密钥使用计数）
      3. write_call_log（写调用日志）

    任意一步抛异常时，回滚积分预扣，并将异常向上传播。
    MySQL 模式：confirm_deduct 直接 INSERT，若失败 rollback 有意义。
    SQLite 模式：confirm_deduct 写队列（内存操作不会失败），基本不触发 except。
    """
    try:
        PointsService.confirm_deduct(db, user_id, points, 1, key_id, model, f"Chat with {provider}")
        KeyService.update_key_usage(db, key_id)
        _write_call_log(db, user_id, key_id, model, success=True)
    except Exception as e:
        logger.error(f"confirm_and_log 失败，回滚积分: {e}")
        PointsService.rollback_points(db, user_id, points)
        raise


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
        _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)
        return ChatCompletionResponse(**response)

    except VendorResponseError as e:
        # HTTP 200 但响应体解析失败：厂商已消耗算力，照常扣积分，不重试
        logger.error(f"VendorResponseError: {e}")
        _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)
        _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"厂商响应解析失败（已扣积分）: {str(e)}",
        )

    except Exception as e:
        # HTTP 层面失败（4xx/5xx）或超时：厂商未消耗算力，回滚积分，尝试重试
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
                _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)
                return ChatCompletionResponse(**response)

            except VendorResponseError as retry_ve:
                # 重试时同样遇到解析失败，扣积分后返回错误
                logger.error(f"Retry VendorResponseError: {retry_ve}")
                _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)
                _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(retry_ve))
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"厂商响应解析失败（已扣积分）: {str(retry_ve)}",
                )

            except Exception as retry_e:
                _handle_vendor_error(db, retry_e, key_id)
                _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(retry_e))
                continue

        # 所有重试耗尽，回滚积分
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

            # 流式正常结束，扣积分
            _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)

        except VendorResponseError as e:
            # 流式过程中响应体解析失败：厂商已消耗算力，照常扣积分
            logger.error(f"Stream VendorResponseError: {e}")
            _confirm_and_log(db, user_id, key_id, request.model, provider, points_to_deduct)
            _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            # HTTP 失败或超时：回滚积分
            _handle_vendor_error(db, e, key_id)
            _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
            PointsService.rollback_points(db, user_id, points_to_deduct)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
