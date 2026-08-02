import json
import uuid
import inspect
from datetime import datetime
import re
import requests
"""
封装对 DeepSeek API 的调用。

支持 thinking mode：开启后回应会带独立的 reasoning_content（模型真的推理过程），
不用再靠 prompt 硬性要求输出固定格式、自己切字符串解析。

以后想换别的模型，只需要在这个文件里加新函数，改 agent/brain.py 里调用的那一行。
"""
import json
import re
import requests

from app import config


def call_deepseek(system_prompt, temperature=0.95, max_tokens=None, top_p=0.95):
    """
    调 DeepSeek 的 chat completions 接口。
    不带对话历史，每次都把人设+情境拼成一条完整的 system message 发过去。

    返回 (content, reasoning_content)：
      content            正式回复，失败时是 None
      reasoning_content   真思考过程，deepseek-reasoner 自动提供，其他模型可能为空
    """
    if not config.DEEPSEEK_API_KEY:
        print("[deepseek_client] 没有设置 CLAUDE_API_KEY，跳过调用")
        return None, None

    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据以上人设与情境，给出你的回应。"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens or config.DEEPSEEK_MAX_TOKENS,
        "top_p": top_p,
    }

    try:
        url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
        print(f"[DEBUG] DEEPSEEK_BASE_URL={config.DEEPSEEK_BASE_URL}")
        print(f"[DEBUG] FINAL_URL={url}")
        url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
        print(f"[DEBUG] DEEPSEEK_BASE_URL={config.DEEPSEEK_BASE_URL}")
        print(f"[DEBUG] FINAL_URL={url}")
        response = requests.post(
            url,
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


def call_deepseek_stream(system_prompt, temperature=0.95, max_tokens=None, top_p=0.95, session_id=None, source="unknown"):
    """
    流式調用 DeepSeek API，逐 token yield SSE 事件。
    Yields: (event_type, data)
        - ("reasoning", chunk) - 思考內容
        - ("content", chunk) - 回答內容
        - ("done", usage_info) - 結束標記
    """
    
     # ========== 添加这两行 ==========
    from app.web.routes import increment_deepseek
    increment_deepseek()
     # ========== END ==========
    
    # ========== DEEPSEEK TRACE ==========
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"
    request_id = str(uuid.uuid4())[:8]
    print(
        f"[DEEPSEEK TRACE] "
        f"request={request_id} "
        f"caller={caller} "
        f"session={session_id[:8] if session_id else 'none'} "
        f"source={source} "
        f"time={datetime.now().isoformat()}"
    )
    # ========== END TRACE ==========
    
    print("[🔥 ENTRY] call_deepseek_stream called, system_prompt length:", len(system_prompt))
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据以上人设与情境，给出你的回应。"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens or config.DEEPSEEK_MAX_TOKENS,
        "top_p": top_p,
        "stream": True  # 🔥 關鍵
    }
    
    try:
        # 🔍 DEBUG: 完整记录发送给 DeepSeek 的 payload
        import json
        from datetime import datetime
        try:
            log_file = f"/tmp/deepseek_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_file, "w", encoding="utf-8") as log_f:
                log_f.write("=" * 80 + "\n")
                log_f.write("DEEPSEEK API PAYLOAD\n")
                log_f.write("=" * 80 + "\n\n")
                log_f.write(json.dumps(payload, ensure_ascii=False, indent=2))
                log_f.write("\n\n" + "=" * 80 + "\n")
                log_f.write(f"SYSTEM_PROMPT LENGTH: {len(system_prompt)}\n")
                log_f.write("=" * 80 + "\n")
            print(f"[PAYLOAD_LOG] Saved to {log_file}")
        except Exception as log_e:
            print(f"[PAYLOAD_LOG] Failed: {log_e}")
        
        # 🔍 DEBUG: 完整记录发送给 DeepSeek 的 payload
        try:
            import json
            from datetime import datetime
            log_file = f"/tmp/deepseek_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("DEEPSEEK API PAYLOAD\n")
                f.write("=" * 80 + "\n\n")
                f.write(json.dumps(payload, ensure_ascii=False, indent=2))
                f.write("\n\n" + "=" * 80 + "\n")
                f.write(f"SYSTEM_PROMPT LENGTH: {len(system_prompt)}\n")
                f.write("=" * 80 + "\n")
            print(f"[PAYLOAD_LOG] Saved to {log_file}")
        except Exception as e:
            print(f"[PAYLOAD_LOG] Failed: {e}")
        
        url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
        print(f"[DEBUG-STREAM] DEEPSEEK_BASE_URL={config.DEEPSEEK_BASE_URL}")
        print(f"[DEBUG-STREAM] FINAL_URL={url}")
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
            stream=True  # 🔥 關鍵
        )
        
        # 檢查 HTTP 狀態碼
        if response.status_code != 200:
            error_body = response.text
            print(f"[deepseek_client] API 錯誤 {response.status_code}: {error_body}")
            yield ("error", f"API返回錯誤: {response.status_code}")
            return
        
        reasoning_buffer = []  # 用於過濾 [MEMORY_DECISION] 等隱藏標籤
        
        for line in response.iter_lines():
            if not line or line.decode().startswith(": ping"):
                continue
            
            if line.startswith(b"data: "):
                payload_str = line[6:].strip()
                if payload_str == b"[DONE]":
                    break
                data = json.loads(payload_str)
                delta = data["choices"][0]["delta"]
                
                # 用值是否為 None 判斷，而不是 key 是否存在：
                # DeepSeek 吐正式 content 的 chunk 裡，"reasoning_content" 這個 key
                # 通常還在，只是值是 null，用 "in delta" 判斷會誤判成 reasoning，
                # 導致 content 永遠被吃掉、送不到前端。
                reasoning_chunk = delta.get("reasoning_content")
                content_chunk = delta.get("content")
                
                # 處理 reasoning_content
                if reasoning_chunk is not None:
                    reasoning_buffer.append(reasoning_chunk)
                    
                    # 檢查是否包含隱藏標籤
                    full_reasoning = "".join(reasoning_buffer)
                    if "[MEMORY_DECISION]" in full_reasoning or "[MOOD_REPORT]" in full_reasoning or "[MOOD_EVENT]" in full_reasoning:
                        # 暫時不發送，等完整 reasoning 結束後過濾
                        pass
                    else:
                        yield ("reasoning", reasoning_chunk)
                
                # 處理 content（獨立判斷，不用 elif，避免同一個 chunk 裡兩者都有時漏掉）
                if content_chunk is not None:
                    yield ("content", content_chunk)
                
                # 結束標記
                if data["choices"][0].get("finish_reason"):
                    # 過濾並發送完整 reasoning（如果有隱藏標籤）
                    full_reasoning = "".join(reasoning_buffer)
                    cleaned = re.sub(r'\[MEMORY_DECISION\].*?\[/MEMORY_DECISION\]', '', full_reasoning, flags=re.DOTALL)
                    cleaned = re.sub(r'\[MOOD_REPORT\].*?\[/MOOD_REPORT\]', '', cleaned, flags=re.DOTALL)
                    cleaned = re.sub(r'\[MOOD_EVENT\].*?\[/MOOD_EVENT\]', '', cleaned, flags=re.DOTALL)
                    
                    # 如果 reasoning 被過濾了，補發乾淨版本給前端顯示
                    if cleaned != full_reasoning:
                        yield ("reasoning", cleaned)
                    
                    # 把未經過濾的原始 reasoning 單獨傳出，供上層解析 [MOOD_REPORT]/[MEMORY_DECISION]
                    # 標籤用；不能拿上面那份 cleaned 版本解析，因為標籤已經被拔掉了
                    yield ("raw_reasoning", full_reasoning)
                    
                    yield ("done", data.get("usage", {}))
                    
    except Exception as e:
        print(f"[deepseek_client] Stream 失敗: {e}")
        yield ("error", str(e))
