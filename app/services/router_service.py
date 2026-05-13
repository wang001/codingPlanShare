import ipaddress
import logging
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.services.key_service import KeyService
from app.utils.cache import cache
from app.config.settings import settings

logger = logging.getLogger(__name__)

# ============================================================
# 厂商白名单：provider 名称 → base_url
#
# 安全策略：默认使用代码内置白名单；也允许通过 config.yaml 的
# provider_catalog.providers 做受限扩展/覆盖。配置 URL 必须是 https
# 且不能指向 localhost、内网 IP、link-local、metadata 等地址。
#
# 命名规则：
#   - 纯按量付费通道：直接用厂商名，如 "zhipu"、"kimi"
#   - Coding Plan 专属通道：加 "_coding" 后缀，如 "alibaba_coding"
#     Coding Plan 通道通常有独立的 base_url、专属 API Key 格式，
#     且费用走套餐而非按 token 扣费，必须与标准通道严格隔离。
#
# 为什么不用同一个 provider 名 + 不同 base_url？
#   → 见文件底部「设计说明」注释。
# ============================================================
BUILTIN_PROVIDER_BASE_URLS: Dict[str, str] = {
    # ── 按量付费通道（标准 OpenAI 兼容） ────────────────────────────────
    "modelscope":    "https://api-inference.modelscope.cn/v1",
    "openai":        "https://api.openai.com/v1",
    "openrouter":    "https://openrouter.ai/api/v1",
    "huggingface":   "https://router.huggingface.co/v1",
    "aihubmix":      "https://aihubmix.com/v1",
    "zhipu":         "https://open.bigmodel.cn/api/paas/v4",
    "minimax":       "https://api.minimaxi.com/v1",          # 国内站
    "minimax_global":"https://api.minimax.io/v1",            # 国际站
    "alibaba":       "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "dashscope":     "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "tencent":       "https://api.hunyuan.cloud.tencent.com/v1",
    "baidu":         "https://qianfan.baidubce.com/v2",
    "qianfan":       "https://qianfan.baidubce.com/v2",
    "deepseek":      "https://api.deepseek.com/v1",
    "siliconflow":   "https://api.siliconflow.cn/v1",
    "kimi":          "https://api.moonshot.cn/v1",           # Kimi 仅按量，无独立 coding plan
    "moonshot":      "https://api.moonshot.ai/v1",
    "gemini":        "https://generativelanguage.googleapis.com/v1beta/openai",
    "mistral":       "https://api.mistral.ai/v1",
    "volcengine":    "https://ark.cn-beijing.volces.com/api/v3",
    "byteplus":      "https://ark.ap-southeast.bytepluses.com/api/v3",
    "stepfun":       "https://api.stepfun.com/v1",
    "xiaomi_mimo":   "https://api.xiaomimimo.com/v1",
    "longcat":       "https://api.longcat.chat/openai/v1",
    "groq":          "https://api.groq.com/openai/v1",

    # ── Anthropic 协议通道 ─────────────────────────────────────────────
    "anthropic":          "https://api.anthropic.com/v1",
    "minimax_anthropic":  "https://api.minimax.io/anthropic",

    # ── Coding Plan 专属通道 ─────────────────────────────────────────
    # 各家 Coding Plan 有独立的 base_url + 专属 API Key（格式不同），
    # 必须单独注册，不能与按量通道混用，否则套餐额度不会被抵扣。
    #
    # 阿里云百炼 Coding Plan（sk-sp-xxxxx 开头）
    #   OpenAI 兼容：https://coding.dashscope.aliyuncs.com/v1
    "alibaba_coding":  "https://coding.dashscope.aliyuncs.com/v1",
    #
    # 智谱 GLM Coding Plan
    #   OpenAI 兼容通道（资源包调用）：https://open.bigmodel.cn/api/paas/v4
    #   注：GLM Coding Plan 的 OpenAI 兼容通道与按量付费共用同一 base_url，
    #       但 API Key 不同（Coding Plan 专属 key 才能走套餐额度）。
    #       单独注册 zhipu_coding 是为了在密钥管理层面明确区分，避免混用。
    "zhipu_coding":    "https://open.bigmodel.cn/api/paas/v4",
    #
    # MiniMax Coding Plan（国内站）
    #   MiniMax M2.7 OpenAI 兼容：https://api.minimaxi.com/v1
    #   同上，base_url 与按量相同，key 不同，单独注册用于区分。
    "minimax_coding":  "https://api.minimaxi.com/v1",
    "volcengine_coding_plan": "https://ark.cn-beijing.volces.com/api/coding/v3",
    "byteplus_coding_plan":   "https://ark.ap-southeast.bytepluses.com/api/coding/v3",

    # mock provider：仅用于开发和测试，不发起真实网络请求
    "mock":            "http://mock.internal/v1",
}

# ============================================================
# 厂商元信息：provider → 描述、key 格式提示、是否为 coding plan
# 用于管理后台展示和创建密钥时的提示信息。
# ============================================================
BUILTIN_PROVIDER_META: Dict[str, Dict[str, Any]] = {
    "modelscope":    {"label": "ModelScope",           "coding_plan": False, "key_hint": "ms-xxxxx"},
    "openai":        {"label": "OpenAI",               "coding_plan": False, "key_hint": "sk-xxxxx", "supports_responses": True},
    "openrouter":    {"label": "OpenRouter",           "coding_plan": False, "key_hint": "sk-or-xxxxx"},
    "huggingface":   {"label": "Hugging Face",         "coding_plan": False, "key_hint": "hf_xxxxx"},
    "aihubmix":      {"label": "AiHubMix",             "coding_plan": False, "key_hint": "任意格式"},
    "zhipu":         {"label": "智谱 GLM（按量）",      "coding_plan": False, "key_hint": "任意格式"},
    "zhipu_coding":  {"label": "智谱 GLM Coding Plan", "coding_plan": True,  "key_hint": "Coding Plan 专属 key"},
    "minimax":       {"label": "MiniMax（按量）",        "coding_plan": False, "key_hint": "任意格式"},
    "minimax_global":{"label": "MiniMax Global",       "coding_plan": False, "key_hint": "任意格式"},
    "minimax_anthropic":{"label": "MiniMax Anthropic", "coding_plan": False, "key_hint": "任意格式"},
    "minimax_coding":{"label": "MiniMax Coding Plan",  "coding_plan": True,  "key_hint": "Coding Plan 专属 key"},
    "alibaba":       {"label": "阿里云百炼（按量）",     "coding_plan": False, "key_hint": "sk-xxxxx"},
    "dashscope":     {"label": "DashScope",            "coding_plan": False, "key_hint": "sk-xxxxx"},
    "alibaba_coding":{"label": "阿里云百炼 Coding Plan","coding_plan": True,  "key_hint": "sk-sp-xxxxx"},
    "tencent":       {"label": "腾讯混元",              "coding_plan": False, "key_hint": "任意格式"},
    "baidu":         {"label": "百度千帆",              "coding_plan": False, "key_hint": "任意格式"},
    "qianfan":       {"label": "Qianfan",              "coding_plan": False, "key_hint": "任意格式"},
    "kimi":          {"label": "Kimi（月之暗面）",      "coding_plan": False, "key_hint": "任意格式"},
    "moonshot":      {"label": "Moonshot",             "coding_plan": False, "key_hint": "任意格式"},
    "deepseek":      {"label": "DeepSeek",             "coding_plan": False, "key_hint": "任意格式"},
    "siliconflow":   {"label": "SiliconFlow",          "coding_plan": False, "key_hint": "任意格式"},
    "gemini":        {"label": "Gemini",               "coding_plan": False, "key_hint": "AIza..."},
    "mistral":       {"label": "Mistral AI",           "coding_plan": False, "key_hint": "任意格式"},
    "volcengine":    {"label": "火山引擎",              "coding_plan": False, "key_hint": "任意格式"},
    "volcengine_coding_plan": {"label": "火山引擎 Coding Plan", "coding_plan": True, "key_hint": "Coding Plan 专属 key"},
    "byteplus":      {"label": "BytePlus",             "coding_plan": False, "key_hint": "任意格式"},
    "byteplus_coding_plan": {"label": "BytePlus Coding Plan", "coding_plan": True, "key_hint": "Coding Plan 专属 key"},
    "stepfun":       {"label": "StepFun",              "coding_plan": False, "key_hint": "任意格式"},
    "xiaomi_mimo":   {"label": "Xiaomi MiMo",          "coding_plan": False, "key_hint": "任意格式"},
    "longcat":       {"label": "LongCat",              "coding_plan": False, "key_hint": "任意格式"},
    "groq":          {"label": "Groq",                 "coding_plan": False, "key_hint": "gsk_..."},
    "anthropic":     {"label": "Anthropic",            "coding_plan": False, "key_hint": "sk-ant-xxxxx"},
    "mock":          {"label": "Mock（测试）",          "coding_plan": False, "key_hint": "mock[:slow|:fail|:fail_rate=N]"},
}

BUILTIN_ANTHROPIC_COMPAT_PROVIDERS = {"anthropic", "minimax_anthropic"}

_PROVIDER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_BLOCKED_HOSTS = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "169.254.169.254",
}
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
)


def _normalize_provider_name(provider: str) -> str:
    name = provider.strip().lower()
    if not _PROVIDER_NAME_RE.fullmatch(name):
        raise ValueError(
            f"非法 provider 名称: {provider!r}，仅允许小写字母、数字、下划线和中划线"
        )
    return name


def _validate_public_https_base_url(provider: str, base_url: str) -> str:
    url = str(base_url).strip().rstrip("/")
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError(f"provider '{provider}' 的 base_url 必须使用 https")
    if not parsed.hostname:
        raise ValueError(f"provider '{provider}' 的 base_url 缺少 hostname")
    if parsed.username or parsed.password:
        raise ValueError(f"provider '{provider}' 的 base_url 不允许包含用户名或密码")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError(f"provider '{provider}' 的 base_url 不允许包含 params/query/fragment")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in _BLOCKED_HOSTS or hostname.endswith(_BLOCKED_HOST_SUFFIXES):
        raise ValueError(f"provider '{provider}' 的 base_url 指向受保护主机: {hostname}")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError(f"provider '{provider}' 的 base_url 指向非公网 IP: {hostname}")

    return url


def _load_configured_provider_catalog() -> tuple[Dict[str, str], Dict[str, Dict[str, Any]], set[str]]:
    """
    合并 config.yaml provider_catalog.providers。

    配置格式：
      provider_catalog:
        providers:
          provider_name:
            enabled: true
            base_url: https://example.com/v1
            label: Example
            protocol: openai | anthropic
            coding_plan: false
            key_hint: sk-xxxxx
            supports_responses: false
    """
    base_urls = dict(BUILTIN_PROVIDER_BASE_URLS)
    meta = {provider: dict(value) for provider, value in BUILTIN_PROVIDER_META.items()}
    anthropic_providers = set(BUILTIN_ANTHROPIC_COMPAT_PROVIDERS)

    configured = settings.provider_catalog.get("providers", {})
    if not configured:
        return base_urls, meta, anthropic_providers
    if not isinstance(configured, dict):
        raise ValueError("provider_catalog.providers 必须是对象")

    for raw_provider, raw_cfg in configured.items():
        provider = _normalize_provider_name(str(raw_provider))
        if raw_cfg is None:
            raw_cfg = {}
        if not isinstance(raw_cfg, dict):
            raise ValueError(f"provider_catalog.providers.{provider} 必须是对象")

        enabled = raw_cfg.get("enabled", True)
        if enabled is False:
            base_urls.pop(provider, None)
            meta.pop(provider, None)
            anthropic_providers.discard(provider)
            continue

        if "base_url" not in raw_cfg:
            if provider not in base_urls:
                raise ValueError(f"新增 provider '{provider}' 必须配置 base_url")
        else:
            base_urls[provider] = _validate_public_https_base_url(provider, raw_cfg["base_url"])

        provider_meta = dict(meta.get(provider, {}))
        for key in ("label", "coding_plan", "key_hint", "supports_responses"):
            if key in raw_cfg:
                provider_meta[key] = raw_cfg[key]
        meta[provider] = provider_meta

        protocol = raw_cfg.get("protocol", "anthropic" if provider in anthropic_providers else "openai")
        if protocol not in {"openai", "anthropic"}:
            raise ValueError(f"provider '{provider}' 的 protocol 仅支持 openai / anthropic")
        if protocol == "anthropic":
            anthropic_providers.add(provider)
        else:
            anthropic_providers.discard(provider)

    return base_urls, meta, anthropic_providers


try:
    PROVIDER_BASE_URLS, PROVIDER_META, ANTHROPIC_COMPAT_PROVIDERS = _load_configured_provider_catalog()
except ValueError as e:
    logger.error("provider_catalog 配置非法，服务启动终止: %s", e)
    raise


class RouterService:
    @staticmethod
    def get_provider_from_model(model: str) -> tuple:
        """
        从模型名称解析厂商 provider 和实际模型名称。

        格式：`provider/model`，例如：
          - "kimi/kimi-k2.5"          → ("kimi", "kimi-k2.5")
          - "alibaba_coding/qwen3.5-plus" → ("alibaba_coding", "qwen3.5-plus")
          - "zhipu_coding/glm-4.7"    → ("zhipu_coding", "glm-4.7")
          - "minimax_coding/MiniMax-M2.7" → ("minimax_coding", "MiniMax-M2.7")

        不带前缀时默认 modelscope。
        """
        if '/' in model:
            provider, actual_model = model.split('/', 1)
            return provider.lower(), actual_model
        return 'modelscope', model

    @staticmethod
    def select_provider_key(db: Session, provider: str, exclude_key_id: Optional[int] = None) -> Optional[ApiKey]:
        """
        选择可用的厂商密钥。
        - 通过 KeyService.get_available_provider_keys 获取（含懒恢复逻辑）
        - 排除指定的 key（用于重试时跳过刚失败的 key）
        - 从可用列表中随机选一个（避免单 key 热点）
        """
        import random
        available_keys = KeyService.get_available_provider_keys(db, provider)

        if exclude_key_id:
            available_keys = [k for k in available_keys if k.id != exclude_key_id]

        if not available_keys:
            return None

        return random.choice(available_keys)

    @staticmethod
    def route_request(db: Session, model: str, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """路由请求到合适的厂商"""
        provider, actual_model = RouterService.get_provider_from_model(model)

        max_retry = settings.key_management.get('max_retry', 1)

        excluded_key_ids = []
        for attempt in range(max_retry + 1):
            provider_key = RouterService.select_provider_key(
                db, provider,
                exclude_key_id=excluded_key_ids[-1] if excluded_key_ids else None
            )
            if not provider_key:
                return None

            if provider_key.key_type == 2:
                try:
                    decrypted_key = KeyService.decrypt_provider_key(provider_key.encrypted_key)
                except Exception:
                    excluded_key_ids.append(provider_key.id)
                    continue
            else:
                decrypted_key = provider_key.encrypted_key

            provider_request = RouterService.adapt_request(provider, actual_model, request_data, decrypted_key)

            return {
                'provider':      provider,
                'key_id':        provider_key.id,
                'key_owner_id':  provider_key.user_id,  # 托管该厂商密钥的用户 id，用于发放收益
                'key':           decrypted_key,
                'request':       provider_request,
            }

        return None

    @staticmethod
    def adapt_request(provider: str, model: str, request_data: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """适配请求参数到厂商 API 格式（统一 OpenAI 兼容格式，base_url 从白名单取）"""
        return {
            'base_url': PROVIDER_BASE_URLS.get(provider.lower(), ""),
            'model': model,
            'messages': request_data.get('messages', []),
            'temperature': request_data.get('temperature', 0.7),
            'max_tokens': request_data.get('max_tokens', 1000),
            'api_key': api_key,
        }

    @staticmethod
    def is_provider_allowed(provider: str) -> bool:
        """检查 provider 是否在白名单中（安全校验，防止 SSRF）"""
        return provider.lower() in PROVIDER_BASE_URLS

    @staticmethod
    def create_provider_instance(provider: str, api_key: str) -> Optional[Any]:
        """
        创建厂商适配器实例。
        - mock：使用 MockProvider，不发起真实网络请求
        - 其他：使用 ModelScopeProvider（统一 OpenAI 兼容格式）
        """
        provider = provider.lower()
        base_url = PROVIDER_BASE_URLS.get(provider)
        if base_url is None:
            return None  # provider 不在白名单，拒绝

        if provider == "mock":
            from app.providers.mock import MockProvider
            return MockProvider(api_key=api_key)

        if provider in ANTHROPIC_COMPAT_PROVIDERS:
            from app.providers.anthropic import AnthropicProvider
            return AnthropicProvider(api_key=api_key, base_url=base_url)

        from app.providers.modelscope import ModelScopeProvider
        return ModelScopeProvider(api_key=api_key, base_url=base_url)

    @staticmethod
    def normalize_response(provider: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化厂商响应为统一的 OpenAI Chat Completions 格式。
        当前所有厂商均已兼容 OpenAI 格式，直接透传。
        若未来某厂商响应字段有差异，在对应分支里做适配。
        """
        # 所有支持厂商（含 coding plan 通道）均返回标准 OpenAI 格式，直接透传
        return response

    @staticmethod
    def get_model_price(model: str) -> int:
        """
        查询本次调用应扣的积分数。

        查找顺序（优先级从高到低）：
          1. config.yaml model_pricing.models.<provider/model>  — 精确模型匹配
          2. config.yaml model_pricing.providers.<provider>     — provider 级别兜底
          3. config.yaml model_pricing.default                  — 全局兜底（默认 10）

        参数 model 为调用方传入的完整模型字符串，如 "zhipu_coding/glm-5.1"。
        """
        pricing = settings.model_pricing
        default_price = int(pricing.get('default', 10))

        # 1. 精确模型匹配
        models_map: Dict[str, Any] = pricing.get('models', {})
        if model in models_map:
            return int(models_map[model])

        # 2. provider 级别
        provider, _ = RouterService.get_provider_from_model(model)
        providers_map: Dict[str, Any] = pricing.get('providers', {})
        if provider in providers_map:
            return int(providers_map[provider])

        # 3. 全局兜底
        return default_price

    @staticmethod
    def list_providers() -> List[Dict[str, Any]]:
        """返回所有已注册 provider 的元信息列表，供管理后台展示。"""
        result = []
        for provider, base_url in PROVIDER_BASE_URLS.items():
            meta = PROVIDER_META.get(provider, {})
            result.append({
                "provider": provider,
                "label": meta.get("label", provider),
                "base_url": base_url,
                "coding_plan": meta.get("coding_plan", False),
                "key_hint": meta.get("key_hint", ""),
                "supports_responses": meta.get("supports_responses", False),
                "price": RouterService.get_model_price(provider + "/"),
            })
        return result

    @staticmethod
    def supports_responses(provider: str) -> bool:
        """检查 provider 是否支持 OpenAI Responses API。"""
        meta = PROVIDER_META.get(provider.lower(), {})
        return bool(meta.get("supports_responses", False))


# ============================================================
# 设计说明：为什么同厂商不同计费通道要用不同 provider 名？
#
# 背景：阿里云、智谱、MiniMax 等厂商同时提供两种 API 接入方式：
#   A. 按量付费：普通 API Key（如 sk-xxxxx），按 token 计费
#   B. Coding Plan：专属 API Key（如 sk-sp-xxxxx）+ 专属 base_url，走套餐额度
#
# 问题：如果用同一个 provider 名（如 "alibaba"），只靠 key 格式区分通道，
#       会带来以下风险：
#   1. 路由不可控：系统随机选 key 时，按量 key 和 coding plan key 会互抢路由，
#      套餐额度不会被正确抵扣，甚至产生额外扣费。
#   2. 用量统计混乱：两种计费模式的调用数据混在一起，无法分别统计。
#   3. 限流策略冲突：按量通道和 coding plan 通道的限流规则不同，共享密钥池会
#      导致错误的 key 被错误地标记为「超限」或「无效」。
#   4. 安全隐患：coding plan key 泄露后，攻击者可通过按量通道发起无限请求。
#
# 解决方案：用 provider 名称本身区分通道：
#   - "alibaba"        → 按量付费，base_url = dashscope.aliyuncs.com/...
#   - "alibaba_coding" → Coding Plan，base_url = coding.dashscope.aliyuncs.com/v1
#
# 用户在模型调用时通过前缀明确指定：
#   - "alibaba/qwen3-max"           → 按量付费
#   - "alibaba_coding/qwen3.5-plus" → 走 coding plan 套餐
#
# 这样路由层完全隔离，密钥池不会混用，计费和统计都是干净的。
# ============================================================
