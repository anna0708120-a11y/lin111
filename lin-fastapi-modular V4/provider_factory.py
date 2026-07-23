'''
LLM Provider 工厂 - 根据配置选择provider
'''
from app.llm.providers.deepseek_provider import DeepSeekProvider
from app import config

# 当前选择的provider名称(存储在state中,可动态切换)
_current_provider = None

def get_provider():
    '''获取当前配置的provider实例'''
    global _current_provider
    
    # 从state获取用户选择的模型
    from app.state import state
    provider_name = state.current_model or 'deepseek'
    
    if provider_name == 'deepseek':
        return DeepSeekProvider(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            model=config.DEEPSEEK_MODEL,
            reasoning_effort=config.DEEPSEEK_REASONING_EFFORT
        )
    elif provider_name == 'claude':
        # TODO: 实现Claude provider
        raise NotImplementedError('Claude provider not yet implemented')
    elif provider_name == 'gpt':
        # TODO: 实现GPT provider
        raise NotImplementedError('GPT provider not yet implemented')
    elif provider_name == 'gemini':
        # TODO: 实现Gemini provider
        raise NotImplementedError('Gemini provider not yet implemented')
    else:
        raise ValueError(f'Unknown provider: {provider_name}')

def list_available_models():
    '''返回可用模型列表'''
    models = [
        {'id': 'deepseek', 'name': 'DeepSeek Flash', 'available': bool(config.DEEPSEEK_API_KEY)},
        {'id': 'claude', 'name': 'Claude Sonnet 5', 'available': False},
        {'id': 'gpt', 'name': 'GPT-5', 'available': False},
        {'id': 'gemini', 'name': 'Gemini', 'available': False},
    ]
    return models
