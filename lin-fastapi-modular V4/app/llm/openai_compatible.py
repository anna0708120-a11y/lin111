"""OpenAI-compatible main-chat provider adapter."""
import json
import re
import requests

from app.llm.provider_interface import LLMProvider, ProviderCapabilities


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, *, name, api_key, base_url, model, reasoning_effort="high", timeout=45):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.capabilities = ProviderCapabilities(
            chat=True,
            streaming=True,
            reasoning=name in {"gpt", "claude", "deepseek"},
            structured_output=True,
            tool_calling=False,
        )

    def _payload(self, system_prompt, *, temperature, max_tokens, top_p, thinking, stream=False):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据以上人设与情境，给出你的回应。"},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        if stream:
            payload["stream"] = True
        if thinking and self.capabilities.reasoning:
            # A6API is OpenAI-compatible; keep these optional fields isolated here.
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    def _url(self):
        return f"{self.base_url}/chat/completions"

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
        if not self.api_key:
            print(f"[llm.{self.name}] main API key is not configured")
            return None, None
        try:
            response = requests.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(
                    system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens or 1200,
                    top_p=top_p,
                    thinking=thinking,
                ),
                timeout=self.timeout,
            )
            response.raise_for_status()
            message = response.json().get("choices", [{}])[0].get("message", {})
            content = (message.get("content") or "").strip() or None
            reasoning = message.get("reasoning_content") or message.get("reasoning")
            return content, reasoning.strip() if isinstance(reasoning, str) and reasoning.strip() else None
        except Exception as exc:
            print(f"[llm.{self.name}] chat failed: {exc}")
            return None, None

    def stream_chat(self, system_prompt, *, temperature=0.95, max_tokens=None, top_p=0.95, thinking=True):
        if not self.api_key:
            yield ("error", f"{self.name} main API key is not configured")
            return
        reasoning_buffer = []
        try:
            response = requests.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(
                    system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens or 1200,
                    top_p=top_p,
                    thinking=thinking,
                    stream=True,
                ),
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else str(raw_line)
                if not line.startswith("data: "):
                    continue
                data_text = line[6:].strip()
                if data_text == "[DONE]":
                    break
                try:
                    data = json.loads(data_text)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                reasoning_chunk = delta.get("reasoning_content") or delta.get("reasoning")
                content_chunk = delta.get("content")
                if reasoning_chunk is not None:
                    reasoning_buffer.append(reasoning_chunk)
                    yield ("reasoning", reasoning_chunk)
                if content_chunk is not None:
                    yield ("content", content_chunk)
                if choices[0].get("finish_reason"):
                    break
            yield ("raw_reasoning", "".join(reasoning_buffer))
            yield ("done", {})
        except Exception as exc:
            print(f"[llm.{self.name}] stream failed: {exc}")
            yield ("error", str(exc))
