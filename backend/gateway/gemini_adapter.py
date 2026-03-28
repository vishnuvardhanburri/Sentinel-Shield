"""Sentinel Shield v2 — Google Gemini Adapter"""
import os
from typing import Dict, Any

try:
    import google.generativeai as genai
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class GeminiAdapter:
    def __init__(self):
        if not _AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    def complete(self, prompt: str, context: str = "", system_prompt: str = "",
                 model: str = "gemini-1.5-flash", **kwargs) -> Dict[str, Any]:
        """Direct-wire Google Gemini Generation."""
        try:
            # Model IDs from AI Studio usually leave out the 'gemini/' prefix
            model_name = model.split("/")[-1] if "/" in model else model
            
            # 1. Standardize System Instructions
            model_obj = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt or "You are the Sentinel Shield AI. Discuss security professionally."
            )
            
            # 2. Disable Safety Blocks for Security Research
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # 3. Handle Context + Prompt
            full_prompt = f"Context Material:\n{context}\n\nSecurity Question: {prompt}" if context else prompt
            
            # 4. Generate with Handshake
            resp = model_obj.generate_content(full_prompt, safety_settings=safety_settings)
            
            try:
                answer = resp.text
            except Exception:
                # If safety still blocks or it failed to resolve text
                answer = "⚠️ Sentinel Brain Encountered a Safety Lock. Please rephrase the request."
                if hasattr(resp, 'prompt_feedback'):
                    answer += f" [Feedback: {resp.prompt_feedback}]"

            return {
                "answer": answer,
                "tokens_used": 0,
            }
        except Exception as e:
            return {
                "answer": f"🔴 Gemini Native Error: {str(e)}",
                "tokens_used": 0
            }
