import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.user import User
from app.services.points_service import PointsService, _SQLiteBackend, _backend


def make_user(db: Session, username: str, balance: int = 100) -> User:
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
    if isinstance(_backend, _SQLiteBackend):
        _backend._balances.pop(user.id, None)
    return user


def make_key(db: Session, user_id: int, key_type: int, value: str, provider: str | None = None) -> ApiKey:
    key = ApiKey(
        user_id=user_id,
        key_type=key_type,
        provider=provider,
        encrypted_key=value,
        name="test key",
        status=0,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def flush_points():
    if isinstance(_backend, _SQLiteBackend):
        _backend.flush_to_db()


def test_chat_completions_handler_smoke(db: Session):
    caller = make_user(db, "chat_caller", balance=100)
    owner = make_user(db, "chat_owner", balance=0)
    platform_key = make_key(db, caller.id, 1, "platform-chat-key")
    vendor_key = make_key(db, owner.id, 2, "mock", provider="mock")

    response_payload = {
        "id": "chatcmpl-smoke",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
    }
    mock_provider = MagicMock()
    mock_provider.chat_completion = AsyncMock(return_value=response_payload)

    async def run():
        from app.api.chat import chat_completions
        from app.schemas.chat import ChatCompletionRequest

        route = {
            "provider": "mock",
            "key_id": vendor_key.id,
            "key_owner_id": owner.id,
            "key": "mock",
            "request": {
                "model": "test-model",
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
        }
        with patch("app.api.chat.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.chat.RouterService.route_request", return_value=route), \
             patch("app.api.chat.RouterService.create_provider_instance", return_value=mock_provider):
            request = ChatCompletionRequest(model="mock/test-model", messages=[{"role": "user", "content": "hi"}])
            return await chat_completions(request, platform_key="platform-chat-key", db=db)

    response = asyncio.run(run())
    flush_points()

    assert response.id == "chatcmpl-smoke"
    assert response.choices[0].message.content == "ok"
    assert PointsService.get_user_balance(db, caller.id) == 90
