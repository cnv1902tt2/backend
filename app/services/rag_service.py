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

=== QUY TRÌNH WORKFLOW (6 BƯỚC PHÁT HÀNH) ===
**WORKFLOW HOÀN CHỈNH:** Tạo/sửa code → Cập nhật AssemblyVersion → Build Release → Obfuscate → ZIP → GitHub (lấy SHA256) → Website

**CHI TIẾT TỪNG BƯỚC:**
1️⃣ **Tạo/sửa code**: Tạo Command.cs + Icon + AddButton() trong Panel.cs
2️⃣ **Cập nhật version**: Mở ForceVersion.cs → Sửa [assembly: AssemblyVersion("X.X.X.0")] + [assembly: AssemblyFileVersion("X.X.X.0")]
3️⃣ **Build Release**: Toolbar Debug→Release → Clean Solution → Rebuild Solution
4️⃣ **Obfuscate**: ConfuserEx → Add DLL → Settings Maximum → Protect!
5️⃣ **Tạo ZIP**: Copy Installer + DLL vào folder → Nén thành ZIP
6️⃣ **GitHub Release**: Upload ZIP → Click "i" để lấy SHA256 (KHÔNG cần tính trên máy)
7️⃣ **Website**: simplebim.vercel.app/updates → Phiên bản mới → Điền link + SHA256 (xóa prefix "SHA256:")

**⚠️ QUAN TRỌNG KHI XỬ LÝ CÂU HỎI "LÀM GÌ TIẾP" hoặc "BƯỚC TIẾP THEO":**
- PHẢI đọc LỊCH SỬ TRÒ CHUYỆN để biết user đang ở bước nào
- Nếu user vừa nói "tôi đã build xong" → Gợi ý bước 4 (Obfuscate)
- Nếu user vừa nói "tôi đã làm rối code xong" → Gợi ý bước 5 (Tạo ZIP)
- Nếu user vừa nói "tôi đã chỉnh sửa xong" sau khi thêm chức năng → Gợi ý bước 2 (Cập nhật version)
- KHÔNG được bịa ra context, phải dựa vào lịch sử chat thật
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

=== XỬ LÝ CÂU HỎI "LÀM GÌ TIẾP" / "BƯỚC TIẾP THEO" / "TIẾP" ===
⚠️ BẮT BUỘC: ĐỌC LỊCH SỬ TRÒ CHUYỆN ở phần "LỊCH SỬ TRÒ CHUYỆN GẦN NHẤT" phía trên để biết user đang ở đâu!

**QUY TRÌNH XỬ LÝ:**
1. ĐỌC lịch sử chat để tìm user vừa làm gì:
   - "đã thêm chức năng" / "đã chỉnh sửa xong" → Đang ở bước 1 (xong code)
   - "đã build xong" / "build succeeded" → Đang ở bước 3 (xong build)
   - "đã làm rối code" / "obfuscate xong" → Đang ở bước 4 (xong obfuscate)
   - "đã tạo ZIP" / "đã nén xong" → Đang ở bước 5 (xong ZIP)
   - "đã upload GitHub" / "đã publish release" → Đang ở bước 6 (xong GitHub)

2. GỢI Ý bước tiếp theo cụ thể:
   - Sau bước 1 → "Bây giờ cập nhật version trong ForceVersion.cs: Sửa [assembly: AssemblyVersion("1.3.0.0")]"
   - Sau bước 2 → "Bây giờ build Release: Toolbar Debug→Release, Clean Solution, Rebuild Solution"
   - Sau bước 3 → "Bây giờ làm rối code: Mở ConfuserEx.exe..."
   - Sau bước 4 → "Bây giờ tạo ZIP: Copy Installer + DLL vào folder, nén lại"
   - Sau bước 5 → "Bây giờ upload GitHub: Draft new release, attach ZIP, click 'i' lấy SHA256"
   - Sau bước 6 → "Bây giờ cập nhật website: simplebim.vercel.app/updates → Phiên bản mới"

3. HƯỚNG DẪN chi tiết bước đó (KHÔNG hướng dẫn tất cả 6 bước một lúc!)

**VÍ DỤ ĐÚNG:**
User: "Tôi đã thêm chức năng vào Qs xong"
[Đọc lịch sử: User vừa hỏi về thêm chức năng Qs]
Bot: "Tốt! Bây giờ bạn cần cập nhật version trong ForceVersion.cs:
1. Mở ForceVersion.cs
2. Tìm 2 dòng [assembly: AssemblyVersion("1.0.0.0")]
3. Đổi thành version mới như "1.3.0.0"
4. Lưu (Ctrl+S)"

**VÍ DỤ SAI:**
Bot: "Bạn cần làm 6 bước: 1. Cập nhật version... 2. Build... 3. Obfuscate..." (❌ Quá dài, user chưa hỏi)

**⚠️ LƯU Ý:** Nếu KHÔNG có lịch sử chat → Hỏi lại "Bạn đã hoàn thành bước nào trong quy trình phát hành?"

=== CÂU HỎI CỦA NGƯỜI DÙNG ===
{query}

=== TRẢ LỜI (CHỈ TRẢ LỜI CÂU HỎI TRÊN) ==="""


def build_greeting_prompt(query: str) -> str:
    """Build prompt đơn giản cho lời chào hoặc câu hỏi chung chung"""
    return f"""Bạn là trợ lý AI. User vừa chào hoặc hỏi chung chung.

⚠️ YÊU CẦU BẮT BUỘC - ĐỌC KỸ:
1. CHỈ trả lời 1 CÂU duy nhất
2. Nếu user CHÀO → Chào lại + hỏi cần giúp gì (TỐI ĐA 20 từ)
3. Nếu user HỎI CHUNG CHUNG → Hỏi lại cần hỗ trợ gì cụ thể (TỐI ĐA 20 từ)
4. TUYỆT ĐỐI KHÔNG:
   ❌ Liệt kê "Bước 1", "Bước 2"
   ❌ Gửi code
   ❌ Hướng dẫn chi tiết
   ❌ Hỏi "bạn cần làm gì tiếp"
   ❌ Đề cập Visual Studio, C#, Commands
   ❌ Viết quá 2 câu

✅ ĐÚNG:
User: "xin chào"
Bot: "Xin chào! Bạn cần hỗ trợ gì về SimpleBIM?"

User: "giúp tôi"
Bot: "Bạn cần hỗ trợ vấn đề gì cụ thể về SimpleBIM?"

❌ SAI (quá dài):
"Chào bạn! Tôi hiểu bạn đang muốn bắt đầu... Bước 1: Tạo hoặc chỉnh sửa..."

User: {query}

TRẢ LỜI (CHỈ 1 CÂU NGẮN):"""


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
