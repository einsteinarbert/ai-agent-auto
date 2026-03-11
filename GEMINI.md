# HOW TO USE

# AI Agent – Hướng dẫn cài đặt và sử dụng

AI Agent là một tool giúp **tự động gửi câu hỏi về source code project tới ChatGPT** bằng cách:

1. Đọc source code của project
2. Tạo context cho ChatGPT
3. Tự động mở browser bằng Playwright
4. Gửi prompt và lấy response

Tool hỗ trợ 2 chế độ:

* **Full context mode** – gửi toàn bộ source code
* **RAG mode (Recommended)** – index code và chỉ gửi phần liên quan

---

# 1. Yêu cầu hệ thống

Cần cài đặt:

* Python **3.9+**
* Google Chrome
* Internet để tải model embedding

---

# 2. Cài đặt dependencies

Tạo virtual environment:

```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows
```

Cài đặt packages:

```bash
pip install playwright chromadb sentence-transformers tqdm
```

Cài Playwright browser:

```bash
playwright install
```

Lưu ý:

Agent **không dùng Chromium bundled** mà sử dụng **Chrome system** để tránh bị Cloudflare phát hiện bot.

---

# 3. Tạo file config.json

Ví dụ:

```json
{
  "chatgpt_url": "https://chat.openai.com",
  "prompt_selector": "textarea",
  "response_selector": "[data-message-author-role='assistant']",
  "wait_timeout": 60000,
  "response_stable_delay": 3000,
  "send_key": "Enter",

  "project_root": "./project",
  "file_extensions": [".py"],
  "exclude_dirs": ["node_modules", ".git", "__pycache__"],

  "max_context_chars": 100000,

  "headless": false,

  "rag": {
    "enabled": true,
    "chroma_persist_dir": ".chroma_db",
    "model_name": "all-MiniLM-L6-v2",
    "chunk_max_lines": 500,
    "top_k": 5
  }
}
```

Giải thích:

| Key               | Ý nghĩa                             |
| ----------------- | ----------------------------------- |
| chatgpt_url       | URL ChatGPT                         |
| prompt_selector   | CSS selector cho ô nhập prompt      |
| response_selector | CSS selector cho response           |
| project_root      | thư mục source code                 |
| file_extensions   | loại file cần index                 |
| exclude_dirs      | thư mục bỏ qua                      |
| max_context_chars | giới hạn context khi không dùng RAG |
| rag.enabled       | bật/tắt RAG                         |

---

# 4. Chạy AI Agent

## Interactive mode

```bash
python agent.py
```

Agent sẽ:

1. Index project (nếu bật RAG)
2. Mở Chrome
3. Yêu cầu login ChatGPT
4. Cho phép hỏi đáp liên tục

Ví dụ:

```
🤖 Câu hỏi: explain architecture of this project
```

---

## Single question mode

```bash
python agent.py --question "Explain how indexing works"
```

Agent sẽ:

1. mở browser
2. gửi câu hỏi
3. in response
4. thoát

---

## Chỉ định project root

```bash
python agent.py --project /path/to/source
```

---

## Không dùng project context

```bash
python agent.py --no-context
```

Agent chỉ gửi câu hỏi bình thường.

---

# 5. Cách hoạt động

## 5.1 Không dùng RAG

Agent sẽ:

1. Đọc toàn bộ source code
2. Ghép thành context:

```
### File: main.py
```

code

```

### File: utils.py
```

code

```

3. Gửi context + câu hỏi tới ChatGPT

Nhược điểm:

- context lớn
- có thể vượt limit

---

## 5.2 RAG mode (Recommended)

Pipeline:

```

Project files
│
▼
Chunk source code
│
▼
Generate embeddings
(SentenceTransformer)
│
▼
Store in ChromaDB
│
▼
Search top-k relevant chunks
│
▼
Send to ChatGPT

```

Ưu điểm:

- prompt nhỏ
- tìm đúng code liên quan
- scale project lớn

---

# 6. Index project

Index được chạy tự động khi start agent.

Có thể reindex trong interactive mode:

```

reindex

```

Agent sẽ:

```

scan project
chunk files
generate embeddings
store to ChromaDB

```

---

# 7. Các lệnh trong interactive mode

| Lệnh | Ý nghĩa |
|----|----|
| question | hỏi ChatGPT |
| reindex | rebuild code index |
| context | xem context (khi không dùng RAG) |
| quit | thoát |

---

# 8. ChromaDB storage

Index được lưu tại:

```

.chroma_db/

````

Có thể xoá để rebuild:

```bash
rm -rf .chroma_db
````

---

# 9. Chrome profile

Agent lưu login session tại:

```
~/.ai-agent-chrome-profile
```

Nhờ đó **chỉ cần login ChatGPT 1 lần**.

---

# 10. Troubleshooting

## ChatGPT không nhận prompt

Kiểm tra selector trong config:

```
prompt_selector
response_selector
```

Vì UI ChatGPT có thể thay đổi.

---

## ChromaDB lỗi

Xóa DB:

```bash
rm -rf .chroma_db
```

và chạy lại agent.

---

## Model download chậm

SentenceTransformer sẽ download model lần đầu:

```
all-MiniLM-L6-v2
```

Dung lượng ~90MB.

---

# 11. Kiến trúc code

```
agent.py
 ├── config loader
 ├── project context reader
 ├── browser automation (Playwright)
 └── interactive agent loop

context_indexer.py
 └── scan project → chunk → embedding → ChromaDB

context_retriever.py
 └── search top-k chunks
```

---

# 12. Best practices

Khuyến nghị:

* luôn bật **RAG mode**
* exclude thư mục lớn

Ví dụ:

```
node_modules
dist
build
.venv
.git
```

---

# 13. Ví dụ workflow

Dev hỏi:

```
🤖 Câu hỏi:
Explain how indexing works
```

Agent:

```
search top 5 code chunks
build prompt
send to ChatGPT
print response
```

---

Nếu bạn muốn, tôi có thể **viết thêm phiên bản GUIDE.md "chuẩn open-source project"** gồm:

* Quick Start
* Architecture diagram
* Example prompts
* Dev guide
* Performance tips

(guide này sẽ **xịn hơn README của nhiều repo AI agent trên GitHub**).
