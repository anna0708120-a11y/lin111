"""
LLM Provider 统一接口基类。
所有模型(DeepSeek/Claude/GPT/Gemini/Codex)都继承这个类，实现统一的 streaming 接口。
"""
from abc import ABC, abstractmethod
from typing import Iterator, Tuple, Optional


class LLMProvider(ABC):
    """
    所有LLM提供商的基类。
    """
    
    @abstractmethod
    def name(self) -> str:
        """返回Provider名称，如 'DeepSeek', 'Claude'"""
        pass
    
    @abstractmethod
    def stream_chat(
        self,
        system_prompt: str,
        temperature: float = 0.95,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        thinking: bool = True
    ) -> Iterator[dict]:
        """
        流式生成回复。
        
        Yields:
            dict: 包含以下字段之一或多个
                - 'token': str - 文本token
                - 'thinking_token': str - 思考过程token (如果支持)
                - 'done': bool - 是否结束
                - 'error': str - 错误信息
        
        Example:
            for chunk in provider.stream_chat(prompt):
                if 'token' in chunk:
                    print(chunk['token'], end='')
                elif 'done' in chunk:
                    break
        """
        pass
    
    def chat(
        self,
        system_prompt: str,
        temperature: float = 0.95,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        thinking: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        非流式调用(向后兼容)。
        内部调用 stream_chat 并收集完整响应。
        
        Returns:
            (content, reasoning): 回复内容和思考过程
        """
        content_tokens = []
        thinking_tokens = []
        
        try:
            for chunk in self.stream_chat(system_prompt, temperature, max_tokens, top_p, thinking):
                if 'token' in chunk:
                    content_tokens.append(chunk['token'])
                elif 'thinking_token' in chunk:
                    thinking_tokens.append(chunk['thinking_token'])
                elif 'error' in chunk:
                    print(f"[{self.name()}] 调用失败: {chunk['error']}")
                    return None, None
        except Exception as e:
            print(f"[{self.name()}] 调用失败: {e}")
            return None, None
        
        content = ''.join(content_tokens).strip() if content_tokens else None
        reasoning = ''.join(thinking_tokens).strip() if thinking_tokens else None
        return content, reasoning
