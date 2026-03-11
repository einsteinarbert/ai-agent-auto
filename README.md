# AI Agent - ChatGPT Nội Bộ (Python + Playwright)

Tự động hoá tương tác với ChatGPT nội bộ qua browser automation.  
Đọc source code project → tạo prompt → nhập vào ChatGPT UI → lấy response.

## Cài đặt

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Cài browser cho Playwright
playwright install chromium
```

## Cấu hình

Chỉnh sửa `config.json`:

```jsonc
{
    "chatgpt_url": "https://chatgpt.com",  // ← ĐỔI URL NÀY
    "prompt_selector": "#prompt-textarea",               // CSS selector ô nhập
    "response_selector": ".markdown.prose",              // CSS selector phần response
    "wait_timeout": 60000,                               // Thời gian chờ tối đa (ms)
    "headless": false,                                   // false = thấy browser
    "project_root": "/path/to/your/project"              // ← ĐỔI PATH NÀY
}
```

## Sử dụng

### Interactive mode (hỏi-đáp liên tục)
```bash
python agent.py
```

### Single question
```bash
python agent.py --question "giải thích kiến trúc project"
```

### Chỉ định project path
```bash
python agent.py --project /path/to/source
```

### Không đọc context (hỏi trực tiếp)
```bash
python agent.py --no-context
```

## Cách hoạt động

1. **Đọc project** → Quét source files, ghép thành context
2. **Mở browser** → Navigate tới ChatGPT URL
3. **Chờ login** → Bạn login thủ công trên browser (nếu cần)
4. **Nhập prompt** → Fill vào `#prompt-textarea` + nhấn Enter
5. **Lấy response** → Chờ response ổn định, hiển thị kết quả
6. **Lặp lại** → Tiếp tục hỏi câu khác

## Lưu ý

- Lần đầu chạy, agent sẽ gửi kèm project context. Các câu sau chỉ gửi câu hỏi.
- Nếu `fill()` không hoạt động (do textarea dùng `contenteditable`), agent sẽ tự fallback sang `keyboard.insert_text()`.
- Điều chỉnh `response_stable_delay` nếu response bị cắt sớm hoặc chờ quá lâu.
