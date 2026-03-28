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


def _write_call_log(
    db: Session,
    user_id: int,
    key_id: int,
    model: str,
    success: bool,
    error_msg: str = None,
    prompt_tokens: int = None,
    completion_tokens: int = None,
    total_tokens: int = None,
    points_deducted: int = None,
):
    log = CallLog(
        user_id=user_id,
        provider_key_id=key_id,
        model=model,
        status=1 if success else 0,
        error_msg=error_msg,
        ip="127.0.0.1",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        points_deducted=points_deducted,
    )
    db.add(log)
    db.commit()


# [Bug2 Fix] 增加 success 参数，由调用方决定本次调用是否算"成功"。
# 原来内部硬编码 success=True，导致 VendorResponseError 场景下
# 调用方再写一条 success=False 的 log，产生两条矛盾记录。
def _confirm_and_log(
    db: Session,
    user_id: int,
    key_id: int,
    key_owner_id: int,
    model: str,
    provider: str,
    points: int,
    success: bool = True,
    error_msg: Optional[str] = None,
    usage: Optional[dict] = None,
):
    """
    原子化完成成功/失败路径的四步操作：
      1. confirm_deduct（调用者积分落库 / 入队）
      2. update_key_usage（更新密钥使用计数）
      3. write_call_log（写调用日志，success/token 用量由调用方传入）
      4. 发放托管收益（仅 success=True 且非自托管时触发）

    usage 参数：成功时传入厂商响应的 usage 字段，用于记录真实 token 用量。
      格式：{"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
      失败时传 None，call_log 对应字段留空。

    托管收益规则：
      - 仅调用成功时发放（success=True）
      - 调用者与托管者相同时不发放（自托管，避免自买自卖）
      - 收益额 = floor(points * key_reward_rate)，至少 1 积分（rate > 0 时）
    """
    try:
        PointsService.confirm_deduct(db, user_id, points, 1, key_id, model, f"Chat with {provider}")
        KeyService.update_key_usage(db, key_id)
        # [Bug2 Fix] success 由调用方传入，不再硬编码 True
        _write_call_log(
            db, user_id, key_id, model,
            success=success,
            error_msg=error_msg,
            prompt_tokens=usage.get('prompt_tokens') if usage else None,
            completion_tokens=usage.get('completion_tokens') if usage else None,
            total_tokens=usage.get('total_tokens') if usage else None,
            points_deducted=points,
        )
    except Exception as e:
        logger.error(f"confirm_and_log 失败，回滚积分: {e}")
        PointsService.rollback_points(db, user_id, points)
        raise

    # ── 托管收益发放 ─────────────────────────────────────────────────
    # 在扣费落库之后单独执行，失败不影响主流程（只记日志）
    if success:
        _grant_key_owner_reward(db, user_id, key_owner_id, key_id, model, points)


def _grant_key_owner_reward(
    db: Session,
    caller_user_id: int,
    key_owner_id: int,
    key_id: int,
    model: str,
    points_deducted: int,
):
    """
    向托管密钥的用户发放收益积分。

    触发条件：
      1. config.yaml key_reward.enabled = true
      2. 调用者（caller_user_id）≠ 托管者（key_owner_id）：自托管不发收益
      3. 计算出的收益 reward ≥ 1

    收益计算：reward = floor(points_deducted * key_reward_rate)
    写入 point_logs.type = 2（托管收益），remark 注明来源模型和调用者 id。
    任何异常均只记 error log，不抛出，不影响调用方的响应。
    """
    try:
        from app.config.settings import settings
        reward_cfg = settings.key_reward
        if not reward_cfg.get('enabled', False):
            return
        if caller_user_id == key_owner_id:
            # 自托管：调用者即密钥所有人，无需发收益
            return

        rate = float(reward_cfg.get('key_reward_rate', 0.7))
        reward = int(points_deducted * rate)
        if reward < 1:
            return

        PointsService.add_points(
            db,
            user_id=key_owner_id,
            amount=reward,
            log_type=2,
            related_key_id=key_id,
            model=model,
            remark=f"托管收益：model={model}，调用者uid={caller_user_id}，扣{points_deducted}积分→收益{reward}积分",
        )
        logger.info(
            f"[Reward] key_owner={key_owner_id} +{reward}积分 "
            f"(caller={caller_user_id}, key_id={key_id}, model={model})"
        )
    except Exception as e:
        logger.error(f"[Reward] 发放托管收益失败，不影响主流程: {e}")


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
    points_to_deduct = RouterService.get_model_price(request.model)

    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

    model_dump_result = request.model_dump()
    route_result = RouterService.route_request(db, request.model, model_dump_result)
    if not route_result:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有可用的厂商密钥")

    provider      = route_result['provider']
    key_id        = route_result['key_id']
    key_owner_id  = route_result['key_owner_id']
    vendor_key    = route_result['key']

    logger.info(f"Routing to provider={provider} key_id={key_id} key_owner={key_owner_id} model={request.model}")

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
        # 正常成功：触发托管收益发放，记录真实 token 用量
        _confirm_and_log(
            db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct,
            usage=response.get('usage'),
        )
        return ChatCompletionResponse(**response)

    except VendorResponseError as e:
        # HTTP 200 但响应体解析失败：厂商已消耗算力，照常扣积分，不重试，不发收益。
        # [Bug2 Fix] 传入 success=False、error_msg，由 _confirm_and_log 统一写日志。
        logger.error(f"VendorResponseError: {e}")
        _confirm_and_log(
            db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct,
            success=False, error_msg=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"厂商响应解析失败（已扣积分）: {str(e)}",
        )

    except Exception as e:
        # HTTP 层面失败（4xx/5xx）或超时：厂商未消耗算力，先回滚，再尝试重试。
        # [Bug1 Fix] 立即回滚 pre_deduct，重试前重新 pre_deduct，避免多扣。
        _handle_vendor_error(db, e, key_id)
        _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
        PointsService.rollback_points(db, user_id, points_to_deduct)  # [Bug1 Fix] 先回滚

        from app.config.settings import settings
        max_retry = settings.key_management.get('max_retry', 1)

        for attempt in range(max_retry):
            logger.warning(f"Retrying chat, attempt {attempt + 1}")

            # [Bug1 Fix] 每次重试前重新 pre_deduct，余额不足则终止重试
            if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

            route_result = RouterService.route_request(db, request.model, model_dump_result)
            if not route_result:
                PointsService.rollback_points(db, user_id, points_to_deduct)  # [Bug1 Fix] 路由失败回滚
                break

            provider      = route_result['provider']
            key_id        = route_result['key_id']
            key_owner_id  = route_result['key_owner_id']
            vendor_key    = route_result['key']

            provider_instance = RouterService.create_provider_instance(provider, vendor_key)
            if not provider_instance:
                PointsService.rollback_points(db, user_id, points_to_deduct)  # [Bug1 Fix] 实例化失败回滚
                continue

            try:
                response = await provider_instance.chat_completion(
                    model=route_result['request']['model'],
                    messages=route_result['request']['messages'],
                    temperature=route_result['request']['temperature'],
                    max_tokens=route_result['request']['max_tokens'],
                )
                # 重试成功：此时 pre_deduct 已重新扣过，confirm 正常落库，触发收益
                _confirm_and_log(
                    db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct,
                    usage=response.get('usage'),
                )
                return ChatCompletionResponse(**response)

            except VendorResponseError as retry_ve:
                # 重试时遇到解析失败：厂商已消耗算力，扣积分后返回错误，不发收益。
                # [Bug2 Fix] 同样用 success=False 传入，不再额外写 _write_call_log。
                logger.error(f"Retry VendorResponseError: {retry_ve}")
                _confirm_and_log(
                    db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct,
                    success=False, error_msg=str(retry_ve),
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"厂商响应解析失败（已扣积分）: {str(retry_ve)}",
                )

            except Exception as retry_e:
                # 重试也失败：回滚本次 pre_deduct，继续下一次
                # [Bug1 Fix] 每次重试失败都回滚，确保下轮重新 pre_deduct 是干净的
                _handle_vendor_error(db, retry_e, key_id)
                _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(retry_e))
                PointsService.rollback_points(db, user_id, points_to_deduct)  # [Bug1 Fix]
                continue

        # 所有重试耗尽，积分已在最后一次 except 中回滚，直接报错
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
    points_to_deduct = RouterService.get_model_price(request.model)

    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

    route_result = RouterService.route_request(db, request.model, request.model_dump())
    if not route_result:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有可用的厂商密钥")

    provider      = route_result['provider']
    key_id        = route_result['key_id']
    key_owner_id  = route_result['key_owner_id']
    vendor_key    = route_result['key']

    provider_instance = RouterService.create_provider_instance(provider, vendor_key)
    if not provider_instance:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"不支持的厂商: {provider}")

    # [Bug3 Fix] 删除此处提前调用的 KeyService.update_key_usage(db, key_id)。
    # 原来在 generate() 启动前就调用一次，generate() 内 _confirm_and_log 又调一次，
    # 导致 used_count 每次流式请求被加两次。
    # update_key_usage 统一由 generate() 内部的 _confirm_and_log 负责。

    async def generate():
        try:
            async for chunk in provider_instance.chat_completion_stream(
                model=route_result['request']['model'],
                messages=route_result['request']['messages'],
                temperature=route_result['request']['temperature'],
                max_tokens=route_result['request']['max_tokens'],
            ):
                yield chunk

            # 流式正常结束：触发托管收益发放
            # 注：流式响应无法从 SSE chunks 中结构化提取 usage，暂记 None
            _confirm_and_log(db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct)

        except VendorResponseError as e:
            # 流式过程中响应体解析失败：厂商已消耗算力，照常扣积分，不发收益。
            # [Bug2 Fix] 传入 success=False，不再额外写 _write_call_log。
            logger.error(f"Stream VendorResponseError: {e}")
            _confirm_and_log(
                db, user_id, key_id, key_owner_id, request.model, provider, points_to_deduct,
                success=False, error_msg=str(e),
            )
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            # HTTP 失败或超时：回滚积分，不发收益
            _handle_vendor_error(db, e, key_id)
            _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
            PointsService.rollback_points(db, user_id, points_to_deduct)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
