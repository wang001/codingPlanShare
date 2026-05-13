import asyncio
from unittest.mock import MagicMock, patch

from fastapi.responses import StreamingResponse
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


def test_chat_completions_stream_handler_smoke(db: Session):
    caller = make_user(db, "stream_caller", balance=100)
    owner = make_user(db, "stream_owner", balance=0)
    platform_key = make_key(db, caller.id, 1, "platform-stream-key")
    vendor_key = make_key(db, owner.id, 2, "mock", provider="mock")

    async def fake_stream(**kwargs):
        yield 'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'
        yield "data: [DONE]\n\n"

    mock_provider = MagicMock()
    mock_provider.chat_completion_stream = fake_stream

    async def run():
        from app.api.chat import chat_completions_stream
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
            response = await chat_completions_stream(request, platform_key="platform-stream-key", db=db)
            assert isinstance(response, StreamingResponse)
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            return "".join(chunks)

    body = asyncio.run(run())
    flush_points()

    assert '"content":"ok"' in body
    assert "data: [DONE]" in body
    assert PointsService.get_user_balance(db, caller.id) == 90
