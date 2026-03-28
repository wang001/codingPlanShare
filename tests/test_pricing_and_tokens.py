"""
差异计费 + token 追踪 + 托管收益 综合测试
==========================================

覆盖场景：
  1. 模型差异计费 - get_model_price 查找顺序
  2. 非流式调用：差异积分正确扣减 + token 写入 call_log
  3. 托管收益：非自托管时正确发放（按 rate 计算）
  4. 自托管：调用者 == 托管者，不发收益
  5. 全量回滚：调用失败积分完整还原
  6. mock provider 端到端：用真实 mock 走完整链路验证数字

运行方式：
  cd /home/node/.openclaw/workspace/codingPlanShare
  python -m pytest tests/test_pricing_and_tokens.py -v
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.call_log import CallLog
from app.models.point_log import PointLog
from app.services.points_service import PointsService, _backend, _SQLiteBackend
from app.services.router_service import RouterService
from app.providers.modelscope import VendorResponseError


# ─── 辅助函数 ─────────────────────────────────────────────────────────────────

def make_user(db: Session, username: str, balance: int = 200) -> User:
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash="x",
        balance=balance,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # 清除 SQLiteBackend 内存缓存，从 DB 重新加载
    if isinstance(_backend, _SQLiteBackend):
        _backend._balances.pop(user.id, None)
    return user


def make_platform_key(db: Session, user_id: int, key_val: str = "platform-key-001") -> ApiKey:
    key = ApiKey(
        user_id=user_id,
        key_type=1,
        encrypted_key=key_val,
        name="platform key",
        status=0,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def make_vendor_key(db: Session, user_id: int, provider: str = "mock") -> ApiKey:
    key = ApiKey(
        user_id=user_id,
        key_type=2,
        provider=provider,
        encrypted_key="mock",
        name="vendor key",
        status=0,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def flush(db: Session):
    """强制 SQLiteBackend flush，让 pending 记录写入 DB"""
    if isinstance(_backend, _SQLiteBackend):
        _backend.flush_to_db()


def mock_response(model: str = "mock/test", pt: int = 10, ct: int = 5) -> dict:
    return {
        "id": "chatcmpl-mock-001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    }


def make_route_result(key_id: int, key_owner_id: int, model: str = "mock/test") -> dict:
    return {
        "provider":     "mock",
        "key_id":       key_id,
        "key_owner_id": key_owner_id,
        "key":          "mock",
        "request": {
            "model":       model,
            "messages":    [{"role": "user", "content": "hi"}],
            "temperature": 0.7,
            "max_tokens":  100,
        },
    }


async def call_chat(db, platform_key_val: str, model: str, route_result: dict, response: dict):
    """调用非流式 chat_completions，mock 厂商返回给定 response。"""
    platform_key_obj = db.query(ApiKey).filter(ApiKey.encrypted_key == platform_key_val).first()

    mock_provider = MagicMock()
    mock_provider.chat_completion = AsyncMock(return_value=response)

    with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key_obj), \
         patch("app.api.chat.RouterService.route_request", return_value=route_result), \
         patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
         patch("app.api.chat.KeyService.update_key_usage"):
        from app.api.chat import chat_completions
        from app.schemas.chat import ChatCompletionRequest
        req = ChatCompletionRequest(model=model, messages=[{"role": "user", "content": "hi"}])
        return await chat_completions(req, platform_key=platform_key_val, db=db)


# ─── 1. get_model_price 查找逻辑 ─────────────────────────────────────────────

class TestGetModelPrice:
    def test_exact_model_match(self):
        """精确模型匹配优先级最高"""
        price = RouterService.get_model_price("kimi/kimi-k2.5")
        assert price == 20, f"kimi/kimi-k2.5 应为 20，实际 {price}"

    def test_provider_level_fallback(self):
        """无精确模型配置时，fallback 到 provider 级别"""
        price = RouterService.get_model_price("kimi/kimi-k2-unknown-model")
        assert price == 20, f"kimi provider 兜底应为 20，实际 {price}"

    def test_global_default_fallback(self):
        """既无精确模型也无 provider 配置时，fallback 到 default"""
        price = RouterService.get_model_price("unknownprovider/somemodel")
        assert price == 10, f"全局 default 应为 10，实际 {price}"

    def test_coding_plan_cheaper(self):
        """coding plan 通道定价低于按量通道"""
        price_normal = RouterService.get_model_price("zhipu/glm-4.7")
        price_coding = RouterService.get_model_price("zhipu_coding/glm-4.7")
        assert price_coding < price_normal, (
            f"zhipu_coding 应比 zhipu 便宜：normal={price_normal}, coding={price_coding}"
        )

    def test_glm51_premium(self):
        """GLM-5.1 高阶模型定价更高"""
        price_47 = RouterService.get_model_price("zhipu_coding/glm-4.7")
        price_51 = RouterService.get_model_price("zhipu_coding/glm-5.1")
        assert price_51 > price_47, (
            f"glm-5.1 应比 glm-4.7 贵：47={price_47}, 51={price_51}"
        )

    def test_siliconflow_cheapest(self):
        """siliconflow 是最便宜的 provider 之一"""
        price = RouterService.get_model_price("siliconflow/some-model")
        assert price <= 6, f"siliconflow 应 ≤ 6，实际 {price}"


# ─── 2. 非流式：差异积分 + token 追踪 ───────────────────────────────────────

def test_dynamic_pricing_deducts_correct_points(db: Session):
    """
    场景：调用 kimi/kimi-k2.5（定价 20），用户初始 100 积分。
    预期：扣 20 积分，余额 80。
    """
    caller = make_user(db, "caller_dynamic", balance=100)
    owner  = make_user(db, "owner_dynamic",  balance=0)
    platform_key = make_platform_key(db, caller.id, "dynamic-platform-key")
    vendor_key   = make_vendor_key(db, owner.id, "kimi")

    route = make_route_result(vendor_key.id, owner.id, "kimi/kimi-k2.5")
    resp  = mock_response("kimi/kimi-k2.5", pt=50, ct=30)

    asyncio.run(call_chat(db, "dynamic-platform-key", "kimi/kimi-k2.5", route, resp))
    flush(db)

    balance = PointsService.get_user_balance(db, caller.id)
    assert balance == 80, f"kimi/kimi-k2.5 应扣 20 积分，余额应为 80，实际 {balance}"


def test_token_usage_written_to_call_log(db: Session):
    """
    场景：调用成功，厂商返回 prompt_tokens=10, completion_tokens=5。
    预期：call_log 记录正确的 token 数和 points_deducted。
    """
    caller = make_user(db, "caller_token", balance=200)
    owner  = make_user(db, "owner_token",  balance=0)
    platform_key = make_platform_key(db, caller.id, "token-platform-key")
    vendor_key   = make_vendor_key(db, owner.id)

    model = "mock/test-model"
    route = make_route_result(vendor_key.id, owner.id, model)
    resp  = mock_response(model, pt=10, ct=5)

    asyncio.run(call_chat(db, "token-platform-key", model, route, resp))
    flush(db)

    log = db.query(CallLog).filter(CallLog.user_id == caller.id).first()
    assert log is not None, "应写入 call_log"
    assert log.status == 1,            f"成功调用 status 应为 1，实际 {log.status}"
    assert log.prompt_tokens == 10,    f"prompt_tokens 应为 10，实际 {log.prompt_tokens}"
    assert log.completion_tokens == 5, f"completion_tokens 应为 5，实际 {log.completion_tokens}"
    assert log.total_tokens == 15,     f"total_tokens 应为 15，实际 {log.total_tokens}"
    assert log.points_deducted == 10,  f"points_deducted 应为 10 (mock/test-model)，实际 {log.points_deducted}"


def test_failed_call_no_token_in_log(db: Session):
    """
    场景：调用失败（VendorResponseError）。
    预期：call_log.status=0，token 字段全部为 None。
    """
    caller = make_user(db, "caller_fail_token", balance=200)
    owner  = make_user(db, "owner_fail_token",  balance=0)
    platform_key = make_platform_key(db, caller.id, "fail-token-key")
    vendor_key   = make_vendor_key(db, owner.id)

    route = make_route_result(vendor_key.id, owner.id)

    platform_key_obj = db.query(ApiKey).filter(ApiKey.encrypted_key == "fail-token-key").first()
    mock_provider = MagicMock()

    async def raise_err(**kwargs):
        raise VendorResponseError("解析失败")
    mock_provider.chat_completion = raise_err

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key_obj), \
             patch("app.api.chat.RouterService.route_request", return_value=route), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            from fastapi import HTTPException
            req = ChatCompletionRequest(model="mock/test-model", messages=[{"role": "user", "content": "hi"}])
            with pytest.raises(HTTPException):
                await chat_completions(req, platform_key="fail-token-key", db=db)

    asyncio.run(run())
    flush(db)

    log = db.query(CallLog).filter(CallLog.user_id == caller.id).first()
    assert log.status == 0,           "失败调用 status 应为 0"
    assert log.prompt_tokens is None, "失败时 prompt_tokens 应为 None"
    assert log.total_tokens is None,  "失败时 total_tokens 应为 None"


# ─── 3. 托管收益：非自托管 ───────────────────────────────────────────────────

def test_reward_granted_to_key_owner(db: Session):
    """
    场景：caller 调用 owner 的 key，调用成功。
    预期：
      - caller 按模型定价扣积分
      - owner 获得 floor(points × rate) 积分（rate=0.7 默认）
      - point_logs 中有 type=2 的收益记录
    """
    caller = make_user(db, "caller_reward", balance=200)
    owner  = make_user(db, "owner_reward",  balance=0)
    platform_key = make_platform_key(db, caller.id, "reward-platform-key")
    vendor_key   = make_vendor_key(db, owner.id)

    model = "mock/test-model"   # 定价 10
    route = make_route_result(vendor_key.id, owner.id, model)
    resp  = mock_response(model, pt=10, ct=5)

    asyncio.run(call_chat(db, "reward-platform-key", model, route, resp))
    flush(db)

    caller_balance = PointsService.get_user_balance(db, caller.id)
    owner_balance  = PointsService.get_user_balance(db, owner.id)

    assert caller_balance == 190, f"caller 应扣 10 积分，余额 190，实际 {caller_balance}"
    # rate=0.7，floor(10 × 0.7) = 7
    assert owner_balance == 7, f"owner 应得 7 积分，实际 {owner_balance}"

    # 检查 point_log type=2
    reward_log = db.query(PointLog).filter(
        PointLog.user_id == owner.id,
        PointLog.type == 2
    ).first()
    assert reward_log is not None, "应有 type=2 的托管收益日志"
    assert reward_log.amount == 7, f"收益日志 amount 应为 7，实际 {reward_log.amount}"


# ─── 4. 自托管不发收益 ────────────────────────────────────────────────────────

def test_no_reward_for_self_hosting(db: Session):
    """
    场景：caller 调用自己托管的 key（caller == key_owner）。
    预期：owner 不获得任何收益，point_logs 无 type=2 记录。
    """
    user = make_user(db, "self_host_user", balance=200)
    platform_key = make_platform_key(db, user.id, "self-platform-key")
    vendor_key   = make_vendor_key(db, user.id)   # 自己的 key

    model = "mock/test-model"
    route = make_route_result(vendor_key.id, user.id, model)  # key_owner == caller
    resp  = mock_response(model)

    asyncio.run(call_chat(db, "self-platform-key", model, route, resp))
    flush(db)

    balance = PointsService.get_user_balance(db, user.id)
    assert balance == 190, f"自托管扣 10，余额应 190，实际 {balance}"

    reward_log = db.query(PointLog).filter(
        PointLog.user_id == user.id,
        PointLog.type == 2
    ).first()
    assert reward_log is None, "自托管不应有 type=2 收益记录"


# ─── 5. 失败时积分完整回滚，无收益 ──────────────────────────────────────────

def test_no_reward_on_failure(db: Session):
    """
    场景：厂商 HTTP 500 失败。
    预期：caller 积分完整回滚，owner 不获得收益。
    """
    caller = make_user(db, "caller_no_reward", balance=200)
    owner  = make_user(db, "owner_no_reward",  balance=0)
    platform_key = make_platform_key(db, caller.id, "fail-platform-key")
    vendor_key   = make_vendor_key(db, owner.id)

    route = make_route_result(vendor_key.id, owner.id)
    platform_key_obj = db.query(ApiKey).filter(ApiKey.encrypted_key == "fail-platform-key").first()

    mock_provider = MagicMock()
    async def always_fail(**kwargs):
        import httpx
        raise Exception("厂商 500")
    mock_provider.chat_completion = always_fail

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key_obj), \
             patch("app.api.chat.RouterService.route_request", return_value=route), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"), \
             patch("app.api.chat.KeyService.mark_key_rate_limited"), \
             patch("app.api.chat.KeyService.mark_key_invalid"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            from fastapi import HTTPException
            req = ChatCompletionRequest(model="mock/test-model", messages=[{"role": "user", "content": "hi"}])
            with pytest.raises(HTTPException):
                await chat_completions(req, platform_key="fail-platform-key", db=db)

    asyncio.run(run())
    flush(db)

    caller_balance = PointsService.get_user_balance(db, caller.id)
    owner_balance  = PointsService.get_user_balance(db, owner.id)

    assert caller_balance == 200, f"失败应完整回滚，caller 余额应 200，实际 {caller_balance}"
    assert owner_balance == 0,    f"失败不发收益，owner 余额应 0，实际 {owner_balance}"


# ─── 6. mock provider 端到端：走真实 MockProvider 验证全链路 ─────────────────

def test_end_to_end_with_real_mock_provider(db: Session):
    """
    端到端测试：不 patch provider，直接用真实 MockProvider 走完整链路。
    验证：定价 → 扣分 → token 记录 → 收益发放 全部正确。
    """
    caller = make_user(db, "e2e_caller", balance=200)
    owner  = make_user(db, "e2e_owner",  balance=0)
    platform_key = make_platform_key(db, caller.id, "e2e-platform-key")
    vendor_key   = make_vendor_key(db, owner.id, "mock")

    model = "mock/test-model"   # 定价 10

    platform_key_obj = db.query(ApiKey).filter(ApiKey.encrypted_key == "e2e-platform-key").first()

    # 构造真实 route_result（包含 key_owner_id），只 patch 路由选 key 部分
    real_route = {
        "provider":     "mock",
        "key_id":       vendor_key.id,
        "key_owner_id": owner.id,
        "key":          "mock",
        "request": {
            "model":       "test-model",
            "messages":    [{"role": "user", "content": "hi"}],
            "temperature": 0.7,
            "max_tokens":  100,
        },
    }

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key_obj), \
             patch("app.api.chat.RouterService.route_request", return_value=real_route), \
             patch("app.api.chat.KeyService.update_key_usage"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            req = ChatCompletionRequest(model=model, messages=[{"role": "user", "content": "hi"}])
            return await chat_completions(req, platform_key="e2e-platform-key", db=db)

    result = asyncio.run(run())
    flush(db)

    # 验证响应结构
    assert result.choices[0].message.role == "assistant"
    assert result.usage.total_tokens > 0, "MockProvider 应返回非零 token 用量"

    # 验证积分
    caller_balance = PointsService.get_user_balance(db, caller.id)
    owner_balance  = PointsService.get_user_balance(db, owner.id)
    assert caller_balance == 190, f"caller 应扣 10，余额 190，实际 {caller_balance}"
    assert owner_balance == 7,    f"owner 应得 7（floor(10×0.7)），实际 {owner_balance}"

    # 验证 call_log token 字段
    log = db.query(CallLog).filter(CallLog.user_id == caller.id).first()
    assert log.status == 1
    assert log.prompt_tokens is not None,    "端到端应写入 prompt_tokens"
    assert log.completion_tokens is not None, "端到端应写入 completion_tokens"
    assert log.total_tokens == log.prompt_tokens + log.completion_tokens
    assert log.points_deducted == 10

    print(f"\n[E2E] caller: 200→{caller_balance} | owner: 0→{owner_balance} "
          f"| tokens: {log.prompt_tokens}+{log.completion_tokens}={log.total_tokens}")
