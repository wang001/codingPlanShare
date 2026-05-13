import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.call_log import CallLog
from app.models.user import User
from app.providers.anthropic import AnthropicProvider
from app.services.points_service import PointsService, _SQLiteBackend, _backend
from app.services.router_service import RouterService


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


def test_provider_catalog_includes_nanobot_remote_openai_compatible_providers():
    providers = {item["provider"]: item for item in RouterService.list_providers()}

    for provider in [
        "openai",
        "openrouter",
        "huggingface",
        "aihubmix",
        "gemini",
        "mistral",
        "volcengine",
        "byteplus",
        "stepfun",
        "xiaomi_mimo",
        "longcat",
        "groq",
        "anthropic",
    ]:
        assert provider in providers
        assert RouterService.is_provider_allowed(provider)

    assert providers["openai"]["supports_responses"] is True
    assert providers["openrouter"]["supports_responses"] is False


def test_create_provider_instance_uses_anthropic_adapter():
    provider = RouterService.create_provider_instance("anthropic", "sk-ant-test")
    assert isinstance(provider, AnthropicProvider)


def test_configured_provider_catalog_can_extend_builtin_providers(monkeypatch):
    import app.services.router_service as router_service

    monkeypatch.setattr(
        router_service.settings,
        "provider_catalog",
        {
            "providers": {
                "custom_gateway": {
                    "base_url": "https://api.example.com/v1",
                    "label": "Custom Gateway",
                    "protocol": "openai",
                    "key_hint": "sk-custom",
                    "supports_responses": True,
                },
                "custom_anthropic": {
                    "base_url": "https://anthropic.example.com/v1",
                    "label": "Custom Anthropic",
                    "protocol": "anthropic",
                },
            }
        },
    )

    base_urls, meta, anthropic_providers = router_service._load_configured_provider_catalog()

    assert base_urls["custom_gateway"] == "https://api.example.com/v1"
    assert meta["custom_gateway"]["label"] == "Custom Gateway"
    assert meta["custom_gateway"]["supports_responses"] is True
    assert base_urls["custom_anthropic"] == "https://anthropic.example.com/v1"
    assert "custom_anthropic" in anthropic_providers


def test_configured_provider_catalog_can_disable_builtin_provider(monkeypatch):
    import app.services.router_service as router_service

    monkeypatch.setattr(
        router_service.settings,
        "provider_catalog",
        {"providers": {"groq": {"enabled": False}}},
    )

    base_urls, meta, anthropic_providers = router_service._load_configured_provider_catalog()

    assert "groq" not in base_urls
    assert "groq" not in meta
    assert "groq" not in anthropic_providers


@pytest.mark.parametrize(
    "base_url",
    [
        "http://api.example.com/v1",
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://10.0.0.1/v1",
        "https://169.254.169.254/latest",
        "https://api.example.com/v1?target=http://127.0.0.1",
    ],
)
def test_configured_provider_catalog_rejects_unsafe_base_urls(monkeypatch, base_url):
    import app.services.router_service as router_service

    monkeypatch.setattr(
        router_service.settings,
        "provider_catalog",
        {"providers": {"unsafe_provider": {"base_url": base_url}}},
    )

    with pytest.raises(ValueError):
        router_service._load_configured_provider_catalog()


def test_openai_responses_endpoint_charges_and_logs_usage(db: Session):
    caller = make_user(db, "responses_caller", balance=100)
    owner = make_user(db, "responses_owner", balance=0)
    platform_key = make_key(db, caller.id, 1, "platform-responses-key")
    vendor_key = make_key(db, owner.id, 2, "sk-test", provider="openai")

    mock_provider = MagicMock()
    mock_provider.responses = AsyncMock(
        return_value={
            "id": "resp_test",
            "object": "response",
            "model": "gpt-4.1",
            "output": [],
            "usage": {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        }
    )

    async def run():
        from app.api.responses import create_response
        from app.schemas.chat import ResponsesRequest

        route = {
            "provider": "openai",
            "key_id": vendor_key.id,
            "key_owner_id": owner.id,
            "key": "sk-test",
            "request": {"model": "gpt-4.1"},
        }
        with patch("app.api.responses.AuthService.verify_api_key", return_value=platform_key), \
             patch("app.api.responses.RouterService.route_request", return_value=route), \
             patch("app.api.responses.RouterService.create_provider_instance", return_value=mock_provider):
            request = ResponsesRequest(model="openai/gpt-4.1", input="hi")
            return await create_response(request, platform_key="platform-responses-key", db=db)

    response = asyncio.run(run())
    flush_points()

    assert response["id"] == "resp_test"
    assert PointsService.get_user_balance(db, caller.id) == 85

    log = db.query(CallLog).filter(CallLog.user_id == caller.id).first()
    assert log is not None
    assert log.status == 1
    assert log.prompt_tokens == 7
    assert log.completion_tokens == 3
    assert log.total_tokens == 10
    assert log.points_deducted == 15


def test_responses_endpoint_rejects_non_responses_provider(db: Session):
    caller = make_user(db, "responses_reject", balance=100)
    platform_key = make_key(db, caller.id, 1, "platform-reject-key")

    async def run():
        from app.api.responses import create_response
        from app.schemas.chat import ResponsesRequest

        with patch("app.api.responses.AuthService.verify_api_key", return_value=platform_key):
            request = ResponsesRequest(model="openrouter/openai/gpt-4.1", input="hi")
            return await create_response(request, platform_key="platform-reject-key", db=db)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 400
    assert "Responses API" in exc_info.value.detail
