"""
Danh sách các AI models hỗ trợ cho AI Agent.

Có 2 loại model:
1. EMBEDDING_MODELS: Dùng cho RAG pipeline (tìm code liên quan)
   - Input: text → Output: vector (embedding)
   - Dùng với: sentence-transformers

2. LLM_MODELS: Dùng cho suy luận / tóm tắt (tương lai)
   - Input: prompt → Output: generated text
   - Dùng với: transformers, llama-cpp-python

Cách dùng:
   Đổi field "model_name" trong config.json → giá trị "name" của model tương ứng.
"""


# ──────────────────────────────────────────────
# Embedding Models (cho RAG - tìm kiếm tương đồng)
# ──────────────────────────────────────────────
EMBEDDING_MODELS = [
    {
        "name": "all-MiniLM-L6-v2",
        "full_name": "sentence-transformers/all-MiniLM-L6-v2",
        "size_mb": 80,
        "description": "Nhẹ, nhanh, phù hợp CPU yếu. Chất lượng khá.",
        "language": "English (đa ngôn ngữ hạn chế)",
        "recommended": True,
    },
    {
        "name": "all-MiniLM-L12-v2",
        "full_name": "sentence-transformers/all-MiniLM-L12-v2",
        "size_mb": 120,
        "description": "Tốt hơn L6, chậm hơn ~30%. Vẫn chạy tốt trên CPU.",
        "language": "English",
        "recommended": False,
    },
    {
        "name": "BAAI/bge-small-en-v1.5",
        "full_name": "BAAI/bge-small-en-v1.5",
        "size_mb": 130,
        "description": "Chất lượng cao hơn MiniLM. Ranking tốt. Khuyên dùng nếu CPU đủ mạnh.",
        "language": "English",
        "recommended": False,
    },
    {
        "name": "BAAI/bge-base-en-v1.5",
        "full_name": "BAAI/bge-base-en-v1.5",
        "size_mb": 420,
        "description": "Chất lượng tốt nhất trong nhóm CPU-friendly. Chậm hơn ~3x so với MiniLM.",
        "language": "English",
        "recommended": False,
    },
    {
        "name": "paraphrase-multilingual-MiniLM-L12-v2",
        "full_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "size_mb": 470,
        "description": "Hỗ trợ 50+ ngôn ngữ (kể cả tiếng Việt). Tốt cho project đa ngôn ngữ.",
        "language": "Multilingual (50+ languages, bao gồm tiếng Việt)",
        "recommended": False,
    },
]


# ──────────────────────────────────────────────
# Ollama Embedding Models (cần cài Ollama)
# ──────────────────────────────────────────────
OLLAMA_EMBEDDING_MODELS = [
    {
        "name": "nomic-embed-text",
        "size_mb": 274,
        "description": "Embedding mạnh, nhanh. Không cần GPU.",
        "gpu_required": False,
        "min_vram_gb": 0,
    },
    {
        "name": "mxbai-embed-large",
        "size_mb": 670,
        "description": "Chất lượng cao nhất. Khuyên dùng GPU (VRAM ≥4GB).",
        "gpu_required": False,
        "min_vram_gb": 4,
    },
    {
        "name": "snowflake-arctic-embed",
        "size_mb": 670,
        "description": "Tốt cho tìm kiếm code. Khuyên dùng GPU (VRAM ≥4GB).",
        "gpu_required": False,
        "min_vram_gb": 4,
    },
]


# ──────────────────────────────────────────────
# Ollama LLM Models (dùng cho Offline Mode - cần cài Ollama)
# ──────────────────────────────────────────────
OLLAMA_LLM_MODELS = [
    {
        "name": "llama3.2:1b",
        "size_gb": 1.3,
        "description": "Nhẹ nhất, chạy được CPU.",
        "min_vram_gb": 2,
        "gpu_required": False,
    },
    {
        "name": "phi3:mini",
        "size_gb": 2.3,
        "description": "Tốt cho code. Khuyên dùng GPU.",
        "min_vram_gb": 4,
        "gpu_required": False,
    },
    {
        "name": "llama3.2:3b",
        "size_gb": 2.0,
        "description": "Cân bằng chất lượng/tốc độ. Khuyên dùng GPU.",
        "min_vram_gb": 4,
        "gpu_required": False,
    },
    {
        "name": "mistral:7b",
        "size_gb": 4.1,
        "description": "Rất mạnh, hiểu context tốt. BẮT BUỘC có GPU.",
        "min_vram_gb": 8,
        "gpu_required": True,
    },
    {
        "name": "codellama:7b",
        "size_gb": 3.8,
        "description": "Chuyên cho code. BẮT BUỘC có GPU.",
        "min_vram_gb": 8,
        "gpu_required": True,
    },
    {
        "name": "deepseek-coder:6.7b",
        "size_gb": 3.8,
        "description": "Code-first, mạnh nhất. BẮT BUỘC có GPU.",
        "min_vram_gb": 8,
        "gpu_required": True,
    },
]


def list_embedding_models():
    """In danh sách embedding models."""
    print("\n📊 Embedding Models - sentence-transformers (cho RAG):")
    print("-" * 70)
    for m in EMBEDDING_MODELS:
        star = " ⭐" if m.get("recommended") else ""
        print(f"  {m['name']}{star}")
        print(f"    Size: {m['size_mb']}MB | {m['description']}")
        print()

    print("\n📊 Embedding Models - Ollama (cần cài ollama.com):")
    print("-" * 70)
    for m in OLLAMA_EMBEDDING_MODELS:
        gpu = "⚙️ GPU khuyên dùng" if m["min_vram_gb"] > 0 else "❌ Không cần GPU"
        print(f"  {m['name']}")
        print(f"    Size: {m['size_mb']}MB | {gpu} | {m['description']}")
        print()


def list_llm_models():
    """In danh sách LLM models (Ollama - cho Offline Mode)."""
    print("\n🧠 LLM Models - Ollama (cho Offline Mode, cần cài ollama.com):")
    print("-" * 70)
    for m in OLLAMA_LLM_MODELS:
        if m["gpu_required"]:
            gpu = f"⚠️ BẮT BUỘC GPU (VRAM ≥{m['min_vram_gb']}GB)"
        elif m["min_vram_gb"] > 0:
            gpu = f"⚙️ Khuyên dùng GPU (VRAM ≥{m['min_vram_gb']}GB)"
        else:
            gpu = "❌ Không cần GPU"
        print(f"  {m['name']}")
        print(f"    Size: {m['size_gb']}GB | {gpu} | {m['description']}")
        print()


def get_embedding_model_info(name: str) -> dict | None:
    """Tìm thông tin model theo tên."""
    for m in EMBEDDING_MODELS:
        if m["name"] == name or m["full_name"] == name:
            return m
    for m in OLLAMA_EMBEDDING_MODELS:
        if m["name"] == name:
            return m
    return None


if __name__ == "__main__":
    list_embedding_models()
    list_llm_models()
