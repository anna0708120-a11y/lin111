"""
封装对 DeepSeek API 的调用。

以后想换别的模型（比如换回 OpenAI，或者接 Claude API），
只需要在这个文件里加一个新函数，改 agent/brain.py 里调用的那一行，
其他模块完全不用碰——这就是"模块化"要的效果。
"""
import requests

from app import config


def call_deepseek(system_prompt, temperature=0.95, max_tokens=180, top_p=0.95):
    """
    调 DeepSeek 的 chat completions 接口。
    跟原本的写法一样：不带对话历史，每次都把人设+情境拼成一条完整的 system message 发过去。

    返回：成功时是模型输出的纯文字；失败或没填 API key 时是 None。
    """
    if not config.DEEPSEEK_API_KEY:
        print("[deepseek_client] 没有设置 DEEPSEEK_API_KEY，跳过调用")
        return None

    try:
        response = requests.post(
            config.DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.DEEPSEEK_MODEL,
                "messages": [{"role": "system", "content": system_prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            },
            timeout=30,
        )
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip()
        print(f"[deepseek_client] 回应里没有 choices: {result}")
        return None
    except Exception as e:
        print(f"[deepseek_client] 呼叫失败: {e}")
        return None
