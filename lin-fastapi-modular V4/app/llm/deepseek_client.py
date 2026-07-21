"""
封装对 DeepSeek API 的调用。

支持 thinking mode：开启后回应会带独立的 reasoning_content（模型真的推理过程），
不用再靠 prompt 硬性要求输出固定格式、自己切字符串解析。

以后想换别的模型，只需要在这个文件里加新函数，改 agent/brain.py 里调用的那一行。
"""
import requests

from app import config


def call_deepseek(system_prompt, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
    """
    调 DeepSeek 的 chat completions 接口。
    不带对话历史，每次都把人设+情境拼成一条完整的 system message 发过去。

    返回 (content, reasoning_content)：
      content            正式回复，失败时是 None
      reasoning_content   真思考过程，没开thinking或模型没给的话是 None
    """
    if not config.DEEPSEEK_API_KEY:
        print("[deepseek_client] 没有设置 DEEPSEEK_API_KEY，跳过调用")
        return None, None

    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": system_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens or config.DEEPSEEK_MAX_TOKENS,
        "top_p": top_p,
    }
    if thinking:
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = config.DEEPSEEK_REASONING_EFFORT

    try:
        response = requests.post(
            config.DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        result = response.json()
        if "choices" not in result:
            print(f"[deepseek_client] 回应里没有 choices: {result}")
            return None, None

        message = result["choices"][0]["message"]
        content = (message.get("content") or "").strip() or None
        reasoning = message.get("reasoning_content")
        reasoning = reasoning.strip() if reasoning else None
        return content, reasoning
    except Exception as e:
        print(f"[deepseek_client] 呼叫失败: {e}")
        return None, None
