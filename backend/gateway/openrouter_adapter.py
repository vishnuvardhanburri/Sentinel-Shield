import os
import requests
import json
import logging

logger = logging.getLogger("sentinel.gateway")

class OpenRouterAdapter:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def complete(self, prompt, context="", system_prompt="", model="google/gemini-2.0-flash-lite-preview-02-05:free") -> dict:
        if not self.api_key:
            return {"answer": "⚠️ OpenRouter API Key missing. Please set OPENROUTER_API_KEY in .env", "tokens_used": 0}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://sentinel-shield-beta.vercel.app/", # Production Vercel URL
            "X-Title": "Sentinel Shield VishnuLabs",
            "Content-Type": "application/json"
        }

        # Combine context and prompt
        full_prompt = f"Context: {context}\n\nUser Question: {prompt}" if context else prompt

        data = {
            "model": model, 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ]
        }

        try:
            resp = requests.post(self.api_url, headers=headers, data=json.dumps(data), timeout=30)
            resp.raise_for_status()
            res_json = resp.json()
            
            answer = res_json['choices'][0]['message']['content']
            tokens = res_json.get('usage', {}).get('total_tokens', 0)
            
            return {
                "answer": answer,
                "tokens_used": tokens,
            }
        except Exception as e:
            logger.error(f"OpenRouter Error: {e}")
            return {"answer": f"🔴 Cloud AI Agent is offline: {str(e)}", "tokens_used": 0}
