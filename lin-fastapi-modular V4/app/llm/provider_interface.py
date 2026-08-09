"""主聊天模型的 provider capabilities。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    chat: bool = True
    streaming: bool = True
    reasoning: bool = False
    structured_output: bool = False
    tool_calling: bool = False


class LLMProvider:
    """主聊天 provider 的最小统一接口。"""

    name = "unknown"
    capabilities = ProviderCapabilities()

    def chat(self, system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
        raise NotImplementedError

    def stream_chat(self, system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
        raise NotImplementedError
