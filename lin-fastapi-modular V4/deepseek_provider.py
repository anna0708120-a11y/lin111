'''
DeepSeek Provider - 支持 streaming + thinking mode
'''
import json
import requests
from typing import Iterator

class DeepSeekProvider:
    def __init__(self, api_key, base_url, model, reasoning_effort='medium'):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.reasoning_effort = reasoning_effort
    
    def name(self):
        return 'DeepSeek'
    
    def stream_chat(self, system_prompt, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
        if not self.api_key:
            yield {'error': 'DeepSeek API key not configured'}
            return
        
        # 修正：base_url 可能不包含 /v1/chat/completions，需要補全
        url = self.base_url
        if not url.endswith('/chat/completions') and not url.endswith('/anthropic'):
            url = url.rstrip('/') + '/v1/chat/completions'
        
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': system_prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens or 8000,
            'top_p': top_p,
            'stream': True
        }
        
        # 只有 deepseek-reasoner 才支持 thinking mode
        if thinking and 'reasoner' in self.model.lower():
            payload['reasoning_effort'] = self.reasoning_effort
        
        try:
            response = requests.post(
                url,
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                error_text = response.text[:200]
                yield {'error': f'HTTP {response.status_code}: {error_text}'}
                return
            
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        yield {'done': True}
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        if not choices:
                            continue
                        delta = choices[0].get('delta', {})
                        if 'content' in delta and delta['content']:
                            yield {'token': delta['content']}
                        if 'reasoning_content' in delta and delta['reasoning_content']:
                            yield {'thinking_token': delta['reasoning_content']}
                        if choices[0].get('finish_reason'):
                            yield {'done': True}
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.Timeout:
            yield {'error': 'Request timeout'}
        except Exception as e:
            yield {'error': str(e)}
