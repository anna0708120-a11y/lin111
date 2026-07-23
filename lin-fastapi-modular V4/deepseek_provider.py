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
        
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': system_prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens or 1500,
            'top_p': top_p,
            'stream': True
        }
        
        if thinking:
            payload['thinking'] = {'type': 'enabled'}
            payload['reasoning_effort'] = self.reasoning_effort
        
        try:
            response = requests.post(
                self.base_url,
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                yield {'error': f'HTTP {response.status_code}'}
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
                        if 'content' in delta:
                            yield {'token': delta['content']}
                        if 'reasoning_content' in delta:
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
