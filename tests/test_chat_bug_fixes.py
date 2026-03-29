"""
针对积分扣减三处 Bug 的回归测试
=====================================

Bug1 - 重试成功后积分多扣：
    首次请求失败 → rollback → 重试前重新 pre_deduct → 重试成功 → confirm
    预期：整个过程只扣一次积分

Bug2 - VendorResponseError 写两条矛盾 call_log：
    _confirm_and_log 现在接受 success 参数，由调用方决定日志状态
    预期：VendorResponseError 路径只写一条 call_log，且 status=0

Bug3 - 流式接口 used_count 加两次：
    删除了 chat_completions_stream 函数体中提前调用的 update_key_usage
    预期：流式成功后 update_key_usage 只被调用 1 次

测试策略：
    - 不启动 HTTP 服务器，直接调用路由函数
    - 使用 unittest.mock patch 注入失败行为
    - 用 asyncio.run 驱动协程（不依赖 pytest-asyncio）
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.call_log import CallLog
from app.services.points_service import PointsService, _backend, _SQLiteBackend
from app.providers.modelscope import VendorResponseError


# ─── 公共辅助 ────────────────────────────────────────────────────────────────

def make_user(db: Session, balance: int = 100) -> User:
    user = User(
        username="chattest",
        email="chattest@example.com",
        password_hash="x",
        balance=balance,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # 清除 SQLiteBackend 内存缓存，确保从 DB 重新加载
    if isinstance(_backend, _SQLiteBackend):
        _backend._balances.pop(user.id, None)
    return user


def make_platform_key(db: Session, user_id: int) -> ApiKey:
    key = ApiKey(
        user_id=user_id,
        key_type=1,
        encrypted_key="test-platform-key-abc123",
        name="test key",
        status=0,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def make_vendor_key(db: Session, user_id: int) -> ApiKey:
    key = ApiKey(
        user_id=user_id,
        key_type=2,
        provider="mock",
        encrypted_key="mock",
        name="mock vendor key",
        status=0,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


MOCK_ROUTE_RESULT = {
    "provider":     "mock",
    "key_id":       999,
    "key_owner_id": 999,   # 与调用者不同的虚构 id，避免自托管判断干扰
    "key":          "mock",
    "request": {
        "model":       "test",
        "messages":    [{"role": "user", "content": "hi"}],
        "temperature": 0.7,
        "max_tokens":  100,
    },
}

MOCK_CHAT_RESPONSE = {
    "id": "mock-id-001",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "mock/test",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


def flush(db):
    """强制 SQLiteBackend flush，确保查询结果包含 pending 记录"""
    if isinstance(_backend, _SQLiteBackend):
        _backend.flush_to_db()


# ─── Bug1：重试成功后积分只扣一次 ────────────────────────────────────────────

def test_bug1_retry_success_deducts_only_once(db: Session):
    """
    场景：第一次厂商调用抛普通 Exception，重试成功。
    预期：用户只被扣 10 分，不会扣 20 分。
    """
    user = make_user(db, balance=100)
    platform_key = make_platform_key(db, user.id)

    call_count = 0

    async def fake_chat(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("模拟首次超时")
        return MOCK_CHAT_RESPONSE

    mock_provider = MagicMock()
    mock_provider.chat_completion = fake_chat

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=MOCK_ROUTE_RESULT), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"), \
             patch("app.api.chat.KeyService.mark_key_rate_limited"), \
             patch("app.api.chat.KeyService.mark_key_invalid"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            return await chat_completions(req, platform_key="test-platform-key-abc123", db=db)

    asyncio.run(run())

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 90, (
        f"[Bug1] 余额应为 90（只扣一次），实际为 {final_balance}。"
        f"（call_count={call_count}，若扣两次余额会是 80）"
    )
    assert call_count == 2, f"应调用厂商 2 次（1失败+1重试），实际 {call_count} 次"


def test_bug1_all_retry_fail_full_rollback(db: Session):
    """
    场景：首次 + 所有重试全部失败。
    预期：积分完整回滚，余额不变（100）。
    """
    user = make_user(db, balance=100)
    platform_key = make_platform_key(db, user.id)

    async def always_fail(**kwargs):
        raise Exception("持续失败")

    mock_provider = MagicMock()
    mock_provider.chat_completion = always_fail

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=MOCK_ROUTE_RESULT), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"), \
             patch("app.api.chat.KeyService.mark_key_rate_limited"), \
             patch("app.api.chat.KeyService.mark_key_invalid"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            from fastapi import HTTPException
            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            with pytest.raises(HTTPException) as exc:
                await chat_completions(req, platform_key="test-platform-key-abc123", db=db)
            assert exc.value.status_code == 500

    asyncio.run(run())

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 100, (
        f"[Bug1] 全部重试失败时余额应回滚到 100，实际为 {final_balance}"
    )


# ─── Bug2：VendorResponseError 只写一条失败日志 ──────────────────────────────

def test_bug2_vendor_response_error_single_log(db: Session):
    """
    场景：厂商返回 HTTP 200 但响应体解析失败（VendorResponseError）。
    预期：
      - call_logs 只有 1 条记录（不重复写入）
      - 该记录 status=0（失败）
      - 积分照常扣减（厂商已消耗算力）
    """
    user = make_user(db, balance=100)
    platform_key = make_platform_key(db, user.id)

    async def raise_parse_error(**kwargs):
        raise VendorResponseError("响应体格式不符合预期")

    mock_provider = MagicMock()
    mock_provider.chat_completion = raise_parse_error

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=MOCK_ROUTE_RESULT), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            from fastapi import HTTPException
            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            with pytest.raises(HTTPException) as exc:
                await chat_completions(req, platform_key="test-platform-key-abc123", db=db)
            assert exc.value.status_code == 502

    asyncio.run(run())
    flush(db)

    logs = db.query(CallLog).filter(CallLog.user_id == user.id).all()
    assert len(logs) == 1, (
        f"[Bug2] 期望 1 条 call_log，实际 {len(logs)} 条。"
        f"（Bug 触发时会写 2 条，一条 status=1，一条 status=0）"
    )
    assert logs[0].status == 0, (
        f"[Bug2] call_log.status 应为 0（失败），实际为 {logs[0].status}"
    )

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 90, (
        f"[Bug2] VendorResponseError 应扣积分（厂商已消耗），余额应为 90，实际为 {final_balance}"
    )


# ─── Bug3：流式接口 used_count 只加一次 ─────────────────────────────────────

def test_bug3_stream_update_key_usage_called_once(db: Session):
    """
    场景：调用流式接口且成功完成。
    预期：KeyService.update_key_usage 只被调用 1 次（修复前会调用 2 次）。
    """
    user = make_user(db, balance=100)
    platform_key = make_platform_key(db, user.id)
    vendor_key = make_vendor_key(db, user.id)

    route_result = {**MOCK_ROUTE_RESULT, "key_id": vendor_key.id}

    update_call_count = 0

    def counting_update(db_session, key_id):
        nonlocal update_call_count
        update_call_count += 1

    async def fake_stream(**kwargs):
        yield b"data: chunk1\n\n"
        yield b"data: [DONE]\n\n"

    mock_provider = MagicMock()
    mock_provider.chat_completion_stream = fake_stream

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=route_result), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage", side_effect=counting_update):
            from app.api.chat import chat_completions_stream
            from app.schemas.chat import ChatCompletionRequest
            from fastapi.responses import StreamingResponse

            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            resp = await chat_completions_stream(req, platform_key="test-platform-key-abc123", db=db)

            assert isinstance(resp, StreamingResponse)
            # 消费生成器，驱动 generate() 执行到底
            async for _ in resp.body_iterator:
                pass

    asyncio.run(run())

    assert update_call_count == 1, (
        f"[Bug3] update_key_usage 应被调用 1 次，实际调用 {update_call_count} 次。"
        f"（Bug 触发时会调用 2 次：函数体 1 次 + _confirm_and_log 1 次）"
    )

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 90, (
        f"[Bug3] 流式成功应扣 10 积分，余额应为 90，实际为 {final_balance}"
    )


# ─── 正常路径回归：修复不破坏正常调用 ────────────────────────────────────────

def test_normal_success_single_log_deducts_once(db: Session):
    """
    正常成功路径：call_log 1 条 status=1，积分扣 10。
    """
    user = make_user(db, balance=100)
    platform_key = make_platform_key(db, user.id)

    async def ok(**kwargs):
        return MOCK_CHAT_RESPONSE

    mock_provider = MagicMock()
    mock_provider.chat_completion = ok

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=MOCK_ROUTE_RESULT), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider), \
             patch("app.api.chat.KeyService.update_key_usage"):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            return await chat_completions(req, platform_key="test-platform-key-abc123", db=db)

    asyncio.run(run())
    flush(db)

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 90, f"正常调用应扣 10 分，余额应为 90，实际为 {final_balance}"

    logs = db.query(CallLog).filter(CallLog.user_id == user.id).all()
    assert len(logs) == 1, f"正常路径期望 1 条 call_log，实际 {len(logs)} 条"
    assert logs[0].status == 1, f"正常路径 call_log.status 应为 1，实际为 {logs[0].status}"


def test_insufficient_balance_rejected(db: Session):
    """积分不足时返回 400，余额不变。"""
    user = make_user(db, balance=5)
    platform_key = make_platform_key(db, user.id)

    async def run():
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key):
            from app.api.chat import chat_completions
            from app.schemas.chat import ChatCompletionRequest
            from fastapi import HTTPException
            req = ChatCompletionRequest(model="mock/test", messages=[{"role": "user", "content": "hi"}])
            with pytest.raises(HTTPException) as exc:
                await chat_completions(req, platform_key="test-platform-key-abc123", db=db)
            assert exc.value.status_code == 400
            assert "积分余额不足" in exc.value.detail

    asyncio.run(run())

    final_balance = PointsService.get_user_balance(db, user.id)
    assert final_balance == 5, f"积分不足时余额不应变化，实际为 {final_balance}"
