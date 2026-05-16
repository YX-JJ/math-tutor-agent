import requests
import json
from config import get_deepseek_api_key, get_deepseek_api_base, get_model


class DeepSeekClient:
    def __init__(self):
        self.api_key = get_deepseek_api_key()
        self.base_url = get_deepseek_api_base().rstrip('/')
        self.model = get_model()

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages, temperature=0.7, max_tokens=2048):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(url, json=payload, headers=self._headers(), timeout=90)
        response.raise_for_status()
        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
        }

    def chat_with_retry(self, messages, temperature=0.7, max_tokens=2048, retries=2):
        last_error = None
        for attempt in range(retries + 1):
            try:
                return self.chat(messages, temperature, max_tokens)
            except requests.exceptions.Timeout:
                last_error = "请求超时，请稍后重试"
                if attempt < retries:
                    continue
            except requests.exceptions.HTTPError as e:
                last_error = f"API 请求失败: {e}"
                if attempt < retries:
                    continue
            except Exception as e:
                last_error = f"发生错误: {e}"
                if attempt < retries:
                    continue
        return {"content": f"抱歉，{last_error}", "tokens_used": 0}

    def parse_json_response(self, content):
        """Try to extract and parse JSON from the AI response content."""
        text = content.strip()
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try to extract from code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        # Try to extract JSON object with braces
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
        return None


_client = None

def get_client():
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client
