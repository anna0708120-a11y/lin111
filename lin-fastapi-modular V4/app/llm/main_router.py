"""主聊天 provider routing；Memory Detector 不经过这里。"""
from app import config
from app.llm.openai_compatible import OpenAICompatibleProvider


def _provider_config(provider_name, model_override=None):
    name = (provider_name or config.DEFAULT_PROVIDER).lower()
    model = model_override or config.PROVIDER_MODELS.get(name) or config.DEFAULT_MODEL
    return name, model


def get_main_provider(*, provider=None, model=None):
    name, resolved_model = _provider_config(provider, model)
    if name not in config.MAIN_PROVIDERS:
        raise ValueError(f"Unknown main LLM provider: {name}")
    return OpenAICompatibleProvider(
        name=name,
        api_key=config.MAIN_LLM_API_KEY,
        base_url=config.MAIN_LLM_BASE_URL,
        model=resolved_model,
        reasoning_effort=config.MAIN_LLM_REASONING_EFFORT,
        timeout=config.MAIN_LLM_TIMEOUT,
    )


def get_main_model_config(*, provider=None, model=None):
    name, resolved_model = _provider_config(provider, model)
    provider_cfg = config.MAIN_PROVIDERS.get(name)
    if provider_cfg is None:
        raise ValueError(f"Unknown main LLM provider: {name}")
    return {
        "provider": name,
        "model": resolved_model,
        "capabilities": dict(provider_cfg["capabilities"]),
        "base_url": config.MAIN_LLM_BASE_URL,
        "endpoint": f"{config.MAIN_LLM_BASE_URL.rstrip('/')}/chat/completions",
    }


def list_main_models():
    return [
        {
            "id": provider,
            "provider": provider,
            "model": config.PROVIDER_MODELS[provider],
            "available": bool(config.MAIN_LLM_API_KEY),
            "capabilities": dict(config.MAIN_PROVIDERS[provider]["capabilities"]),
        }
        for provider in config.MAIN_PROVIDERS
    ]


def chat(system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True, provider=None, model=None):
    try:
        return get_main_provider(provider=provider, model=model).chat(
            system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            thinking=thinking,
        )
    except Exception as exc:
        print(f"[llm.router] chat routing failed: {exc}")
        return None, None


def stream_chat(system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True, provider=None, model=None):
    try:
        yield from get_main_provider(provider=provider, model=model).stream_chat(
            system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            thinking=thinking,
        )
    except Exception as exc:
        print(f"[llm.router] stream routing failed: {exc}")
        yield ("error", str(exc))
