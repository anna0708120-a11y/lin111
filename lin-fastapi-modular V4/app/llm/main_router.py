"""主聊天 provider routing；Memory Detector 不经过这里。"""
from app import config
from app.llm.openai_compatible import OpenAICompatibleProvider


def _provider_config(provider_name, model_override=None):
    name = (provider_name or config.DEFAULT_PROVIDER).lower()
    model = model_override or config.PROVIDER_MODELS.get(name) or config.DEFAULT_MODEL
    catalog_provider = config.MODEL_CATALOG.get(model)
    if catalog_provider and provider_name is None:
        name = catalog_provider
    if catalog_provider and catalog_provider != name:
        raise ValueError(f"Model {model} belongs to provider {catalog_provider}, not {name}")
    if model not in config.MODEL_CATALOG:
        raise ValueError(f"Unknown main LLM model: {model}")
    return name, model


def get_main_provider(*, provider=None, model=None):
    name, resolved_model = _provider_config(provider, model)
    if name not in config.MAIN_PROVIDERS:
        raise ValueError(f"Unknown main LLM provider: {name}")
    provider_settings = {
        "deepseek": {
            "api_key": config.DEEPSEEK_API_KEY,
            "base_url": config.DEEPSEEK_BASE_URL,
        },
        "gpt": {
            "api_key": config.MAIN_LLM_API_KEY,
            "base_url": config.MAIN_LLM_BASE_URL,
        },
        "claude": {
            "api_key": config.MAIN_LLM_API_KEY,
            "base_url": config.MAIN_LLM_BASE_URL,
        },
    }[name]
    return OpenAICompatibleProvider(
        name=name,
        api_key=provider_settings["api_key"],
        base_url=provider_settings["base_url"],
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
        "base_url": config.DEEPSEEK_BASE_URL if name == "deepseek" else config.MAIN_LLM_BASE_URL,
        "endpoint": f"{(config.DEEPSEEK_BASE_URL if name == 'deepseek' else config.MAIN_LLM_BASE_URL).rstrip('/')}/chat/completions",
    }


def list_main_models():
    return [
        {
            "id": model,
            "provider": provider,
            "model": model,
            "available": bool(config.MAIN_LLM_API_KEY),
            "capabilities": dict(config.MAIN_PROVIDERS[provider]["capabilities"]),
        }
        for model, provider in config.MODEL_CATALOG.items()
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


def stream_chat(system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True, provider=None, model=None, tools=None, tool_choice=None, tool_result=None):
    try:
        yield from get_main_provider(provider=provider, model=model).stream_chat(
            system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            tool_result=tool_result,
        )
    except Exception as exc:
        print(f"[llm.router] stream routing failed: {exc}")
        yield ("error", str(exc))
