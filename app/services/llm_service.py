# LLM Service - Hỗ trợ Gemini và HuggingFace
# Author: SimpleBIM Team

import os
import asyncio
import logging
from typing import Optional, AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM Configuration"""
    provider: str  # "gemini" or "huggingface"
    api_key: str
    model: str


class LLMService:
    """Service xử lý gọi LLM APIs"""
    
    def __init__(self):
        self.config = self._detect_config()
        self._gemini_model = None
        self._hf_client = None
    
    def _detect_config(self) -> Optional[LLMConfig]:
        """Auto-detect cấu hình LLM từ environment variables"""
        
        # Try Gemini first
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            logger.info("Detected Gemini API key")
            return LLMConfig(
                provider="gemini",
                api_key=gemini_key,
                model="gemini-2.0-flash"
            )
        
        # Try HuggingFace
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            logger.info("Detected HuggingFace token")
            return LLMConfig(
                provider="huggingface",
                api_key=hf_token,
                model="Qwen/Qwen2.5-7B-Instruct"
            )
        
        logger.warning("No LLM API key found in environment")
        return None
    
    def is_configured(self) -> bool:
        """Kiểm tra đã cấu hình LLM chưa"""
        return self.config is not None
    
    def get_provider(self) -> Optional[str]:
        """Lấy tên provider đang dùng"""
        return self.config.provider if self.config else None
    
    async def generate_response(self, prompt: str, chat_history: list = None) -> str:
        """
        Generate response từ LLM.
        Hỗ trợ cả Gemini và HuggingFace.
        """
        if not self.config:
            return "⚠️ LLM chưa được cấu hình. Vui lòng thiết lập GEMINI_API_KEY hoặc HF_TOKEN."
        
        if self.config.provider == "gemini":
            return await self._call_gemini(prompt, chat_history)
        elif self.config.provider == "huggingface":
            return await self._call_huggingface(prompt, chat_history)
        else:
            return f"⚠️ Provider không được hỗ trợ: {self.config.provider}"
    
    async def _call_gemini(self, prompt: str, chat_history: list = None) -> str:
        """Call Gemini API"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.config.api_key)
            
            if self._gemini_model is None:
                self._gemini_model = genai.GenerativeModel(self.config.model)
            
            # Build messages
            messages = []
            if chat_history:
                for msg in chat_history[-6:]:  # Last 6 messages
                    role = "user" if msg.get("role") == "user" else "model"
                    messages.append({
                        "role": role,
                        "parts": [msg.get("content", "")]
                    })
            
            # Start chat và generate
            if messages:
                chat = self._gemini_model.start_chat(history=messages)
                response = chat.send_message(prompt)
            else:
                response = self._gemini_model.generate_content(prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"⚠️ Lỗi Gemini API: {str(e)}"
    
    async def _call_huggingface(self, prompt: str, chat_history: list = None) -> str:
        """Call HuggingFace Inference API"""
        try:
            from huggingface_hub import InferenceClient
            
            if self._hf_client is None:
                self._hf_client = InferenceClient(
                    model=self.config.model,
                    token=self.config.api_key
                )
            
            # Build messages
            messages = []
            
            # System message - BẮT BUỘC tiếng Việt
            system_msg = """Bạn là trợ lý AI hỗ trợ phát triển SimpleBIM - Revit Add-in (C#).

QUY TẮC BẮT BUỘC:
1. LUÔN trả lời bằng TIẾNG VIỆT - KHÔNG BAO GIỜ dùng tiếng Trung, tiếng Anh hoặc ngôn ngữ khác
2. Nếu người dùng hỏi về lịch sử chat ("tôi vừa hỏi gì", "câu hỏi trước"), trả lời: "Tôi không có khả năng nhớ lịch sử trò chuyện. Vui lòng hỏi lại câu hỏi của bạn."
3. KHÔNG BAO GIỜ bịa đặt hoặc tự tạo ra lịch sử chat không có thật
4. Trả lời ngắn gọn, hữu ích, đúng trọng tâm"""
            messages.append({"role": "system", "content": system_msg})
            
            # Chat history
            if chat_history:
                for msg in chat_history[-6:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Call API
            response = self._hf_client.chat_completion(
                messages=messages,
                max_tokens=2048,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"HuggingFace API error: {e}")
            return f"⚠️ Lỗi HuggingFace API: {str(e)}"


# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get singleton LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
