# RAG Service - Xử lý Retrieval-Augmented Generation
# Author: SimpleBIM Team

import os
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Load settings
def get_number_few_shot() -> int:
    """Lấy số lượng few-shot examples từ config"""
    return int(os.getenv("NUMBER_FEW_SHOT", "5"))

@dataclass
class RetrievedChunk:
    id: str
    title: str
    content: str
    score: float
    category: str

# ==================== Load Data từ JSON Files ====================

def get_data_dir() -> Path:
    """Lấy đường dẫn thư mục data"""
    return Path(__file__).parent / "data"

def load_rag_chunks() -> List[Dict]:
    """Load RAG chunks từ file JSON"""
    try:
        data_file = get_data_dir() / "rag_chunks.json"
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading rag_chunks.json: {e}")
    return []

def load_few_shot_examples() -> List[Dict]:
    """Load few-shot examples từ file JSON"""
    try:
        data_file = get_data_dir() / "few_shot_examples.json"
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading few_shot_examples.json: {e}")
    return []

# Load data khi module được import
RAG_CHUNKS = load_rag_chunks()
FEW_SHOT_EXAMPLES = load_few_shot_examples()


def normalize_query(query: str) -> str:
    """Chuẩn hóa query"""
    normalized = query.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[?.!]+$', '', normalized)
    return normalized


def is_greeting_or_general_question(query: str) -> bool:
    """Kiểm tra xem query có phải là lời chào hoặc câu hỏi chung chung không"""
    normalized = normalize_query(query)
    
    # Các pattern liên quan đến LỊCH SỬ CHAT - KHÔNG được coi là greeting/general
    # Các câu hỏi này CẦN chat_history nên phải dùng prompt đầy đủ
    history_patterns = [
        'vừa hỏi', 'trước đó', 'câu hỏi trước', 'lúc nãy',
        'hỏi gì', 'nói gì', 'tôi đã hỏi', 'tôi đã nói',
        'câu trả lời trước', 'nhắc lại', 'lần trước'
    ]
    for pattern in history_patterns:
        if pattern in normalized:
            return False  # Cần prompt đầy đủ với chat_history
    
    # Các pattern lời chào
    greeting_patterns = [
        'xin chào', 'chào bạn', 'chào', 'hello', 'hi', 'hey',
        'chào buổi sáng', 'chào buổi chiều', 'chào buổi tối'
    ]
    
    # Các pattern câu hỏi chung chung
    general_patterns = [
        'hướng dẫn tôi', 'giúp tôi', 'bạn có thể hướng dẫn',
        'bạn có thể giúp', 'hỗ trợ tôi', 'bạn làm được gì',
        'bạn biết gì', 'bạn có thể làm gì', 'vài vấn đề',
        '1 vài vấn đề', 'một vài vấn đề', 'một số vấn đề',
        'được không', 'có thể không', 'giúp được không'
    ]
    
    # Kiểm tra lời chào
    for pattern in greeting_patterns:
        if pattern in normalized or normalized == pattern:
            return True
    
    # Kiểm tra câu hỏi chung chung (không có chủ đề cụ thể)
    for pattern in general_patterns:
        if pattern in normalized:
            # Kiểm tra xem có từ khóa cụ thể không
            specific_keywords = [
                'command', 'build', 'version', 'ribbon', 'icon', 'obfuscate',
                'sha256', 'hash', 'zip', 'github', 'release', 'update',
                'button', 'panel', 'tab', 'dll', 'confuserex', 'visual studio',
                'code', 'lỗi', 'error', 'tạo', 'thêm', 'xóa', 'sửa',
                'qs', 'as', 'mepf', 'chức năng'
            ]
            has_specific = any(kw in normalized for kw in specific_keywords)
            if not has_specific:
                return True
    
    return False


def calculate_similarity(query1: str, query2: str) -> float:
    """Tính Jaccard similarity"""
    words1 = set(normalize_query(query1).split())
    words2 = set(normalize_query(query2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


def retrieve_chunks(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    """
    Retrieve relevant chunks cho query.
    Sử dụng keyword matching đơn giản.
    """
    query_normalized = normalize_query(query)
    query_words = set(query_normalized.split())
    
    scored_chunks = []
    
    for chunk in RAG_CHUNKS:
        # Tính score dựa trên keyword overlap
        chunk_text = f"{chunk['title']} {chunk['content']}".lower()
        keywords = set(chunk.get('keywords', []))
        
        # Score từ keywords - tăng trọng số cho exact match
        keyword_matches = query_words & keywords
        keyword_score = len(keyword_matches) / max(len(keywords), 1)
        
        # Bonus score nếu match nhiều keywords quan trọng
        important_keywords = {'qs', 'as', 'mepf', 'chức năng', 'tab', 'ribbon', 'command'}
        important_matches = query_words & important_keywords & keywords
        bonus_score = len(important_matches) * 0.2
        
        # Score từ content overlap
        content_words = set(chunk_text.split())
        content_score = len(query_words & content_words) / max(len(query_words), 1)
        
        # Combined score
        total_score = keyword_score * 0.5 + content_score * 0.3 + bonus_score
        
        if total_score > 0.1:
            scored_chunks.append(RetrievedChunk(
                id=chunk['id'],
                title=chunk['title'],
                content=chunk['content'],
                score=total_score,
                category=chunk['category']
            ))
    
    # Sort by score và lấy top_k
    scored_chunks.sort(key=lambda x: x.score, reverse=True)
    return scored_chunks[:top_k]


def build_context(chunks: List[RetrievedChunk]) -> str:
    """Build context string từ chunks"""
    if not chunks:
        return "Không tìm thấy thông tin trực tiếp liên quan trong tài liệu."
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[{i}] **{chunk.title}** (relevance: {int(chunk.score * 100)}%)\n{chunk.content}")
    
    return "\n\n---\n\n".join(context_parts)


def build_few_shot_prompt(count: int = None) -> str:
    """Build few-shot examples"""
    if count is None:
        count = get_number_few_shot()
    examples = FEW_SHOT_EXAMPLES[:count]
    return "\n\n".join([
        f"Ví dụ {i+1}:\nCâu hỏi: {ex['question']}\nTrả lời: {ex['answer']}"
        for i, ex in enumerate(examples)
    ])


def build_chat_history_prompt(chat_history: list = None) -> str:
    """Build phần lịch sử chat gần nhất để gửi cho LLM"""
    if not chat_history:
        return ""
    
    # Lấy số lượng từ config
    count = get_number_few_shot()
    
    # Lấy các cặp Q&A gần nhất (mỗi cặp = 2 messages: user + assistant)
    recent_pairs = []
    messages = chat_history[-(count * 2):]  # Lấy count*2 messages cuối
    
    i = 0
    while i < len(messages) - 1:
        if messages[i].get("role") == "user" and messages[i+1].get("role") == "assistant":
            recent_pairs.append({
                "question": messages[i].get("content", ""),
                "answer": messages[i+1].get("content", "")
            })
            i += 2
        else:
            i += 1
    
    if not recent_pairs:
        return ""
    
    history_parts = []
    for i, pair in enumerate(recent_pairs, 1):
        history_parts.append(f"[{i}] Người dùng: {pair['question']}\n    Trợ lý: {pair['answer'][:200]}...")
    
    return "\n".join(history_parts)


def build_llm_prompt(query: str, context: str, few_shot: str, chat_history: list = None) -> str:
    """Build full prompt cho LLM"""
    
    # Build phần lịch sử chat
    history_section = ""
    if chat_history:
        history_text = build_chat_history_prompt(chat_history)
        if history_text:
            history_section = f"""
=== LỊCH SỬ TRÒ CHUYỆN GẦN NHẤT (THAM KHẢO ĐỂ TRẢ LỜI PHÙ HỢP NGỮ CẢNH) ===
{history_text}
"""
    
    return f"""Bạn là trợ lý AI chuyên hướng dẫn phát triển SimpleBIM - một Revit Add-in (C#).

=== VAI TRÒ CỦA BẠN ===
Hướng dẫn người dùng thực hiện quy trình phát triển và phát hành SimpleBIM:
1. Tạo và chỉnh sửa mã nguồn C# trong Visual Studio 2022 (KHÔNG phải VS Code)
2. Build project ở chế độ Release
3. Làm rối code (obfuscate) bằng ConfuserEx
4. Đóng gói ZIP và tính SHA256 hash
5. Upload file lên GitHub Release
6. Cập nhật version trên website admin để user tự động update
{history_section}
=== THÔNG TIN TỪ TÀI LIỆU (DÙNG ĐỂ TRẢ LỜI, KHÔNG LIỆT KÊ NGUYÊN VĂN) ===
{context}

=== VÍ DỤ VỀ CÁCH TRẢ LỜI (CHỈ THAM KHẢO PHONG CÁCH, KHÔNG COPY) ===
{few_shot}

=== ĐỐI TƯỢNG NGƯỜI DÙNG ===
Người dùng là người MỚI, CHƯA THÀNH THẠO Visual Studio và KHÔNG BIẾT CODE.
Vì vậy cần hướng dẫn CHI TIẾT TỪNG BƯỚC NHỎ.

=== QUY TẮC PHÂN BIỆT QUAN TRỌNG ===
1. "Tạo chức năng mới trong giao diện Qs/As/MEPF" = Thêm Command + Button vào tab HIỆN CÓ
   → Hướng dẫn: Tạo file trong Commands/Qs (hoặc As, MEPF) + Thêm AddButton vào QsPanel.cs
   
2. "Tạo tab ribbon mới" hoặc "tạo giao diện mới hoàn toàn" = Tạo TAB MỚI (như BS)
   → Hướng dẫn: Copy QsPanel → BsPanel, đăng ký trong RibbonManager

=== QUY TẮC TRẢ LỜI ===
1. QUAN TRỌNG: Khi hỏi về C#, Visual Studio → LUÔN trả lời dựa trên Visual Studio 2022
2. ƯU TIÊN trả lời dựa trên thông tin trong tài liệu ở trên
3. Trả lời bằng tiếng Việt, CHI TIẾT, dễ hiểu cho người mới
4. Dùng bullet points và đánh số thứ tự rõ ràng
5. Chỉ rõ: CÁI GÌ cần làm, Ở ĐÂU, COPY/PASTE cái gì, ĐỔI từ gì THÀNH gì

=== QUY TẮC BẮT BUỘC ===
1. LUÔN trả lời bằng TIẾNG VIỆT - KHÔNG BAO GIỜ dùng tiếng Trung, tiếng Anh
2. CHỈ trả lời ĐÚNG câu hỏi được hỏi - KHÔNG thêm thông tin thừa
3. KHÔNG gửi code nếu người dùng không yêu cầu cụ thể
4. TUYỆT ĐỐI KHÔNG liệt kê nhiều "Ví dụ 1", "Ví dụ 2"
5. TUYỆT ĐỐI KHÔNG copy nguyên văn từ phần ví dụ
6. Mỗi câu trả lời chỉ tập trung vào 1 chủ đề
7. CHỈ KHI người dùng hỏi rõ ràng về lịch sử chat (VD: "tôi vừa hỏi gì", "câu hỏi trước của tôi") → Tham khảo LỊCH SỬ TRÒ CHUYỆN để trả lời
8. VỚI CÂU HỎI BÌNH THƯỜNG (không hỏi về lịch sử) → Trả lời trực tiếp, KHÔNG đề cập đến lịch sử chat
9. KHÔNG BAO GIỜ nói "Tôi không tìm thấy câu hỏi trước đó" trừ khi người dùng HỎI VỀ CÂU HỎI TRƯỚC ĐÓ

=== CÂU HỎI CỦA NGƯỜI DÙNG ===
{query}

=== TRẢ LỜI (CHỈ TRẢ LỜI CÂU HỎI TRÊN) ==="""


def build_greeting_prompt(query: str) -> str:
    """Build prompt đơn giản cho lời chào hoặc câu hỏi chung chung"""
    return f"""Bạn là trợ lý AI chuyên hướng dẫn phát triển SimpleBIM - một Revit Add-in (C#).

=== NHIỆM VỤ ===
Trả lời ngắn gọn câu hỏi/lời chào của người dùng.

=== QUY TẮC BẮT BUỘC ===
1. LUÔN trả lời bằng TIẾNG VIỆT - KHÔNG dùng tiếng Trung, tiếng Anh
2. Nếu người dùng chào hỏi → Chào lại ngắn gọn 1-2 câu
3. Nếu người dùng hỏi chung chung → Hỏi lại họ cần hỗ trợ gì CỤ THỂ
4. TUYỆT ĐỐI KHÔNG liệt kê nhiều ví dụ
5. Chỉ trả lời TỐI ĐA 3 câu

=== CÂU HỎI ===
{query}

=== TRẢ LỜI NGẮN GỌN ==="""


def run_rag_pipeline(query: str) -> Tuple[str, str, List[str]]:
    """
    Full RAG pipeline.
    Returns: (context, few_shot_prompt, sources)
    """
    # Kiểm tra nếu là lời chào hoặc câu hỏi chung chung
    if is_greeting_or_general_question(query):
        return "", "", []
    
    # Retrieve chunks
    chunks = retrieve_chunks(query)
    
    # Build context
    context = build_context(chunks)
    
    # Build few-shot
    few_shot = build_few_shot_prompt()
    
    # Extract sources
    sources = [chunk.title for chunk in chunks]
    
    return context, few_shot, sources


def get_prompt_for_query(query: str) -> str:
    """
    Lấy prompt phù hợp cho query.
    Nếu là lời chào/câu hỏi chung → prompt đơn giản
    Nếu là câu hỏi cụ thể → prompt đầy đủ với RAG
    """
    if is_greeting_or_general_question(query):
        return build_greeting_prompt(query)
    
    context, few_shot, sources = run_rag_pipeline(query)
    return build_llm_prompt(query, context, few_shot)
