import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.chat import get_platform_key, _grant_key_owner_reward
from app.db.database import get_db
from app.models.call_log import CallLog
from app.providers.modelscope import VendorResponseError
from app.schemas.chat import ResponsesRequest
from app.services.auth_service import AuthService
from app.services.key_service import KeyService
from app.services.points_service import PointsService
from app.services.router_service import RouterService

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle_vendor_error(db: Session, exc: Exception, key_id: int):
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            KeyService.mark_key_rate_limited(db, key_id)
        elif code in (401, 403):
            KeyService.mark_key_invalid(db, key_id)


def _usage_from_response(response: dict) -> dict:
    usage = response.get("usage") or {}
    prompt_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    completion_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    total_tokens = usage.get("total_tokens")
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _write_call_log(
    db: Session,
    user_id: int,
    key_id: int,
    model: str,
    success: bool,
    error_msg: Optional[str] = None,
    usage: Optional[dict] = None,
    points_deducted: Optional[int] = None,
):
    usage = usage or {}
    log = CallLog(
        user_id=user_id,
        provider_key_id=key_id,
        model=model,
        status=1 if success else 0,
        error_msg=error_msg,
        ip="127.0.0.1",
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
        points_deducted=points_deducted,
    )
    db.add(log)
    db.commit()


@router.post("")
async def create_response(
    request: ResponsesRequest,
    platform_key: str = Depends(get_platform_key),
    db: Session = Depends(get_db),
):
    """OpenAI Responses API 兼容入口。"""
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="暂不支持流式 Responses API，请使用非流式请求",
        )

    key = AuthService.verify_api_key(db, platform_key)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API密钥")

    provider, actual_model = RouterService.get_provider_from_model(request.model)
    if not RouterService.supports_responses(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"provider '{provider}' 暂不支持 OpenAI Responses API",
        )

    user_id = key.user_id
    points_to_deduct = RouterService.get_model_price(request.model)

    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分余额不足")

    route_result = RouterService.route_request(db, request.model, {})
    if not route_result:
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有可用的厂商密钥")

    key_id = route_result["key_id"]
    key_owner_id = route_result["key_owner_id"]
    vendor_key = route_result["key"]
    provider_instance = RouterService.create_provider_instance(provider, vendor_key)
    if not provider_instance or not hasattr(provider_instance, "responses"):
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"provider '{provider}' 未实现 Responses API",
        )

    payload = request.model_dump(exclude_none=True)
    payload["model"] = actual_model
    payload.pop("stream", None)

    try:
        response = await provider_instance.responses(payload)
        usage = _usage_from_response(response)
        PointsService.confirm_deduct(
            db,
            user_id,
            points_to_deduct,
            1,
            key_id,
            request.model,
            f"Responses with {provider}",
        )
        KeyService.update_key_usage(db, key_id)
        _write_call_log(
            db,
            user_id,
            key_id,
            request.model,
            success=True,
            usage=usage,
            points_deducted=points_to_deduct,
        )
        _grant_key_owner_reward(db, user_id, key_owner_id, key_id, request.model, points_to_deduct)
        return response

    except VendorResponseError as e:
        logger.error(f"Responses VendorResponseError: {e}")
        PointsService.confirm_deduct(
            db,
            user_id,
            points_to_deduct,
            1,
            key_id,
            request.model,
            f"Responses with {provider}",
        )
        KeyService.update_key_usage(db, key_id)
        _write_call_log(
            db,
            user_id,
            key_id,
            request.model,
            success=False,
            error_msg=str(e),
            points_deducted=points_to_deduct,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"厂商响应解析失败（已扣积分）: {str(e)}",
        )

    except Exception as e:
        _handle_vendor_error(db, e, key_id)
        _write_call_log(db, user_id, key_id, request.model, success=False, error_msg=str(e))
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"厂商 Responses API 调用失败: {str(e)}",
        )
