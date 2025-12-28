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

def get_number_question_answer() -> int:
    """Lấy số lượng cặp Q&A từ chat history"""
    return int(os.getenv("NUMBER_QUESTION_ANSWER", "3"))

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
    
    # Các pattern FOLLOW-UP (yêu cầu giải thích thêm) - KHÔNG được coi là greeting/general
    # Các câu hỏi này CẦN chat_history để biết đang hỏi về chủ đề gì
    follow_up_patterns = [
        'vẫn chưa hiểu', 'chưa hiểu rõ', 'chưa rõ', 'chưa hiểu',
        'giải thích rõ hơn', 'giải thích thêm', 'giải thích lại',
        'chi tiết hơn', 'cụ thể hơn', 'rõ ràng hơn', 'dễ hiểu hơn',
        'ví dụ thêm', 'ví dụ cụ thể', 'cho ví dụ',
        'hướng dẫn lại', 'nhắc lại', 'làm rõ'
    ]
    for pattern in follow_up_patterns:
        if pattern in normalized:
            return False  # Cần prompt đầy đủ với chat_history
    
    # Các pattern về WORKFLOW - KHÔNG được coi là greeting/general
    # Các câu hỏi này cần RAG để trả lời chính xác
    workflow_patterns = [
        'làm gì tiếp', 'bước tiếp theo', 'tiếp theo', 'sau đó', 
        'xong rồi', 'hoàn thành', 'đã xong', 'tiếp tục',
        'bây giờ', 'giờ', 'sau khi', 'kế tiếp', 'lại'
    ]
    for pattern in workflow_patterns:
        if pattern in normalized:
            return False  # Cần prompt đầy đủ với RAG
    
    # Các pattern lời chào
    greeting_patterns = [
        'xin chào', 'chào bạn', 'chào', 'hello', 'hi', 'hey',
        'chào buổi sáng', 'chào buổi chiều', 'chào buổi tối'
    ]
    
    # Các pattern câu hỏi chung chung
    general_patterns = [
        'hướng dẫn tôi', 'hướng dẫn', 'giúp tôi', 'bạn có thể hướng dẫn',
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


def retrieve_chunks(query: str, top_k: int = 8) -> List[RetrievedChunk]:
    """
    Retrieve relevant chunks cho query.
    Sử dụng keyword matching với fuzzy support.
    Tăng top_k lên 8 để cung cấp nhiều context hơn cho LLM tổng hợp.
    """
    query_normalized = normalize_query(query)
    query_words = set(query_normalized.split())
    
    scored_chunks = []
    
    # Mapping từ đồng nghĩa để cải thiện retrieval
    synonym_mapping = {
        'chuyển': ['di chuyển', 'move', 'dời'],
        'tạo': ['thêm', 'add', 'new', 'create'],
        'xóa': ['delete', 'remove', 'bỏ'],
        'sửa': ['chỉnh sửa', 'edit', 'modify', 'đổi'],
        'chức năng': ['function', 'feature', 'command', 'button'],
        'tab': ['ribbon', 'panel', 'giao diện'],
    }
    
    # Mở rộng query với từ đồng nghĩa
    expanded_query_words = set(query_words)
    for word in query_words:
        if word in synonym_mapping:
            expanded_query_words.update(synonym_mapping[word])
    
    for chunk in RAG_CHUNKS:
        # Tính score dựa trên keyword overlap
        chunk_text = f"{chunk['title']} {chunk['content']}".lower()
        keywords = set(chunk.get('keywords', []))
        
        # Score từ keywords - tăng trọng số cho exact match
        keyword_matches = expanded_query_words & keywords
        keyword_score = len(keyword_matches) / max(len(keywords), 1)
        
        # Bonus score nếu match nhiều keywords quan trọng
        important_keywords = {'qs', 'as', 'mepf', 'chức năng', 'tab', 'ribbon', 'command', 'tạo', 'chuyển'}
        important_matches = expanded_query_words & important_keywords & keywords
        bonus_score = len(important_matches) * 0.25
        
        # Score từ content overlap (bao gồm cả expanded words)
        content_words = set(chunk_text.split())
        content_score = len(expanded_query_words & content_words) / max(len(expanded_query_words), 1)
        
        # Bonus cho category liên quan
        category_bonus = 0.0
        if any(cat in query_normalized for cat in ['workflow', 'quy trình', 'hoàn chỉnh', 'đầy đủ']):
            if chunk['category'] in ['workflow', 'overview']:
                category_bonus = 0.3
        
        # Combined score
        total_score = keyword_score * 0.5 + content_score * 0.3 + bonus_score + category_bonus
        
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
    """Build context string từ chunks với metadata để LLM dễ tổng hợp"""
    if not chunks:
        return "Không tìm thấy thông tin trực tiếp liên quan trong tài liệu."
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        # Thêm category để LLM biết chunk thuộc nhóm nào
        context_parts.append(
            f"[{i}] **{chunk.title}** (Category: {chunk.category}, Relevance: {int(chunk.score * 100)}%)\n"
            f"{chunk.content}"
        )
    
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
    
    # Lấy số lượng cặp Q&A từ config
    count = get_number_question_answer()
    
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
    """Build prompt tối ưu cho LLM - cho phép tổng hợp thông tin từ nhiều chunks"""
    
    # Build phần lịch sử chat
    history_section = ""
    if chat_history:
        history_text = build_chat_history_prompt(chat_history)
        if history_text:
            history_section = f"""
=== LỊCH SỬ TRÒ CHUYỆN GẦN NHẤT ===
{history_text}
"""
    
    return f"""Bạn là trợ lý AI chuyên hướng dẫn phát triển SimpleBIM - Revit Add-in (C#) trong Visual Studio 2022.

=== CẤU TRÚC DỰ ÁN SIMPLEBIM ===
SimpleBIM/
├── Commands/           # Mã nguồn chức năng
│   ├── As/            # Ribbon SIMPLEBIM.AS (Kiến trúc)
│   ├── MEPF/          # Ribbon SIMPLEBIM.MEPF (Cơ điện)
│   └── Qs/            # Ribbon SIMPLEBIM.QS (Định lượng)
├── Ribbon/Panels/     # Cấu hình giao diện ribbon
│   ├── AsPanel.cs
│   ├── MEPFPanel.cs
│   └── QsPanel.cs
├── Icons/16/ và 32/   # Icon cho buttons
└── Update/ForceVersion.cs  # Quản lý version

=== WORKFLOW PHÁT HÀNH (6 BƯỚC) ===
1. Tạo/sửa code → 2. Cập nhật version → 3. Build Release → 4. Obfuscate → 5. Tạo ZIP → 6. GitHub Release → 7. Website
{history_section}
=== TÀI LIỆU HƯỚNG DẪN ===
Dưới đây là các phần liên quan từ tài liệu. Bạn CÓ THỂ KẾT HỢP NHIỀU PHẦN để trả lời câu hỏi.

{context}

=== VÍ DỤ PHONG CÁCH TRẢ LỜI ===
{few_shot}

=== HƯỚNG DẪN TRẢ LỜI ===

**KHI CÓ THÔNG TIN TRỰC TIẾP:**
- Sử dụng thông tin từ tài liệu ở trên
- Trả lời chi tiết, từng bước nhỏ cho người mới

**KHI CẦN TỔNG HỢP (câu hỏi phức tạp hoặc không match trực tiếp):**
- KẾT HỢP nhiều phần tài liệu liên quan để tạo hướng dẫn hoàn chỉnh
- SỬ DỤNG CẤU TRÚC DỰ ÁN để suy luận các bước tương tự
- Ví dụ: "chuyển chức năng từ As sang Qs" = copy file từ Commands/As sang Commands/Qs + sửa namespace + cập nhật QsPanel.cs

**⚠️ QUY TẮC TUÂN THỦ NGHIÊM NGẶT - BẮT BUỘC:**

1. **GIỮ NGUYÊN TÊN FILE/CLASS:**
   - User nói "facefloor" → Giữ nguyên "facefloor" (KHÔNG tự động thêm "Command")
   - User nói "FaceFloorCommand" → Giữ nguyên "FaceFloorCommand"
   - CHỈ thêm "Command" khi tài liệu hoặc user yêu cầu rõ ràng

2. **COPY CHÍNH XÁC CODE TỪ TÀI LIỆU:**
   - Tài liệu viết `[assembly: AssemblyVersion("1.0.0.0")]` → Copy CHÍNH XÁC
   - KHÔNG được tự sáng tạo thành `new Version("1.0.0.0")`
   - KHÔNG được thay đổi format, cú pháp, tên biến

3. **TUÂN THỦ SỐ LIỆU:**
   - Tài liệu viết version "1.0.0.0" → Giữ nguyên "1.0.0.0"
   - Chỉ thay đổi khi user yêu cầu version cụ thể

4. **QUY TẮC CHUNG:**
   - Trả lời TIẾNG VIỆT, chi tiết, dễ hiểu
   - Chỉ rõ: CÁI GÌ, Ở ĐÂU, COPY/PASTE gì, ĐỔI từ gì THÀNH gì
   - Dùng số thứ tự và bullet points
   - KHÔNG copy nguyên văn từ ví dụ few-shot
   - Với câu hỏi "làm gì tiếp" → ĐỌC lịch sử để biết user đang ở bước nào, gợi ý bước kế

=== CÂU HỎI ===
{query}

=== TRẢ LỜI ===\n"""


def build_greeting_prompt(query: str) -> str:
    """Build prompt CỰC KỲ NGẮN GỌN cho lời chào - CHỈ 1 CÂU"""
    return f"""Bạn là trợ lý SimpleBIM. User vừa chào hoặc hỏi chung chung.

⚠️ QUY TẮC BẮT BUỘC:
- CHỈ trả lời 1 CÂU duy nhất (10-15 từ)
- KHÔNG liệt kê bước 1, 2, 3
- KHÔNG hướng dẫn chi tiết
- KHÔNG đề cập Visual Studio, Commands, code

✅ MẪU ĐÚNG:
"Xin chào! Bạn cần hỗ trợ gì về SimpleBIM?"
"Bạn cần hỗ trợ vấn đề cụ thể nào về SimpleBIM?"

User: {query}

TRẢ LỜI (1 CÂU):"""


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
