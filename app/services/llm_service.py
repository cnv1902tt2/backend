# LLM Service - Hỗ trợ Gemini, Groq và HuggingFace
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
    provider: str  # "gemini", "groq", or "huggingface"
    api_key: str
    model: str


class LLMService:
    """Service xử lý gọi LLM APIs"""
    
    def __init__(self):
        self.config = self._detect_config()
        self._gemini_model = None
        self._groq_client = None
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
                model="gemini-2.5-flash"
            )
        
        # Try Groq
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            logger.info("Detected Groq API key")
            return LLMConfig(
                provider="groq",
                api_key=groq_key,
                model="llama-3.3-70b-versatile"  # Llama 3.3 70B
            )
        
        # Try HuggingFace
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            logger.info("Detected HuggingFace token")
            return LLMConfig(
                provider="huggingface",
                api_key=hf_token,
                model="Qwen/Qwen2.5-72B-Instruct"  # Model miễn phí trên HF
            )
        
        logger.warning("No LLM API key found in environment")
        return None
    
    def is_configured(self) -> bool:
        """Kiểm tra đã cấu hình LLM chưa"""
        return self.config is not None
    
    def get_provider(self) -> Optional[str]:
        """Lấy tên provider đang dùng"""
        return self.config.provider if self.config else None
    
    async def generate_response(self, prompt: str, chat_history: list = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """
        Generate response từ LLM.
        Hỗ trợ cả Gemini, Groq và HuggingFace.
        
        Args:
            prompt: Prompt text
            chat_history: Chat history (optional)
            max_tokens: Max tokens to generate (default 2048, set lower for greetings)
            temperature: Creativity level (default 0.7, set lower for greetings)
        """
        if not self.config:
            return "⚠️ LLM chưa được cấu hình. Vui lòng thiết lập GEMINI_API_KEY, GROQ_API_KEY hoặc HF_TOKEN."
        
        if self.config.provider == "gemini":
            return await self._call_gemini(prompt, chat_history, max_tokens, temperature)
        elif self.config.provider == "groq":
            return await self._call_groq(prompt, chat_history, max_tokens, temperature)
        elif self.config.provider == "huggingface":
            return await self._call_huggingface(prompt, chat_history, max_tokens, temperature)
        else:
            return f"⚠️ Provider không được hỗ trợ: {self.config.provider}"
    
    async def _call_gemini(self, prompt: str, chat_history: list = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
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
    
    async def _call_groq(self, prompt: str, chat_history: list = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Call Groq API"""
        try:
            from groq import Groq
            
            if self._groq_client is None:
                self._groq_client = Groq(
                    api_key=self.config.api_key
                )
            
            # Build messages
            messages = []
            system_msg = """Bạn là trợ lý AI hỗ trợ phát triển SimpleBIM - Revit Add-in (C#).

    QUY TẮC BẮT BUỘC:
    1. LUÔN trả lời bằng TIẾNG VIỆT - KHÔNG BAO GIỜ dùng tiếng Trung, tiếng Anh hoặc ngôn ngữ khác
    2. CHỈ trả lời ĐÚNG câu hỏi được hỏi - KHÔNG tự bịa thêm câu hỏi khác
    3. KHÔNG liệt kê "Câu hỏi 1", "Câu hỏi 2" nếu user KHÔNG hỏi nhiều câu
    4. Nếu người dùng hỏi về lịch sử chat ("tôi vừa hỏi gì", "câu hỏi trước"), trả lời: "Tôi không có khả năng nhớ lịch sử trò chuyện. Vui lòng hỏi lại câu hỏi của bạn."
    5. KHÔNG BAO GIỜ bịa đặt hoặc tự tạo ra lịch sử chat không có thật
    6. Trả lời ngắn gọn, hữu ích, đúng trọng tâm"""
            messages.append({"role": "system", "content": system_msg})
            
            if chat_history:
                for msg in chat_history[-6:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            messages.append({"role": "user", "content": prompt})
            
            # Call Groq API
            response = self._groq_client.chat.completions.create(
                model=self.config.model,  # "llama-3.3-70b-versatile"
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"⚠️ Lỗi Groq API: {str(e)}"
    
    async def _call_huggingface(self, prompt: str, chat_history: list = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Call HuggingFace Inference API"""
        try:
            from huggingface_hub import InferenceClient
            
            if self._hf_client is None:
                self._hf_client = InferenceClient(
                    provider="together",
                    token=self.config.api_key
                )
            
            # Build messages
            messages = []
            system_msg = """Bạn là trợ lý AI hỗ trợ phát triển SimpleBIM - Revit Add-in (C#).

    QUY TẮC BẮT BUỘC:
    1. LUÔN trả lời bằng TIẾNG VIỆT - KHÔNG BAO GIỜ dùng tiếng Trung, tiếng Anh hoặc ngôn ngữ khác
    2. CHỈ trả lời ĐÚNG câu hỏi được hỏi - KHÔNG tự bịa thêm câu hỏi khác
    3. KHÔNG liệt kê "Câu hỏi 1", "Câu hỏi 2" nếu user KHÔNG hỏi nhiều câu
    4. Nếu người dùng hỏi về lịch sử chat ("tôi vừa hỏi gì", "câu hỏi trước"), trả lời: "Tôi không có khả năng nhớ lịch sử trò chuyện. Vui lòng hỏi lại câu hỏi của bạn."
    5. KHÔNG BAO GIỜ bịa đặt hoặc tự tạo ra lịch sử chat không có thật
    6. Trả lời ngắn gọn, hữu ích, đúng trọng tâm"""
            messages.append({"role": "system", "content": system_msg})
            
            if chat_history:
                for msg in chat_history[-6:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            messages.append({"role": "user", "content": prompt})
            
            # Call HuggingFace API
            response = self._hf_client.chat_completion(
                model=self.config.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
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
