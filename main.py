#!/usr/bin/env python3
"""
AI Agent - Tự động hoá ChatGPT nội bộ qua Playwright browser automation.

Đọc project context → tạo prompt → nhập vào ChatGPT UI → lấy response.

Usage:
    python agent.py                          # Interactive mode
    python agent.py --question "explain X"   # Single question mode
    python agent.py --project /path/to/src   # Specify project root
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

def load_config(config_path: str = "config.json") -> dict:
    """Load config từ file JSON."""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# Project Context Reader
# ─────────────────────────────────────────────

def read_project_context(
    root_dir: str,
    extensions: list[str],
    exclude_dirs: list[str],
    max_chars: int
) -> str:
    """
    Đọc toàn bộ source files trong project, trả về string context.
    Giới hạn max_chars để không vượt context window.
    """
    context_parts = []
    total_chars = 0
    root = Path(root_dir).resolve()

    if not root.exists():
        print(f"[WARN] Project root not found: {root_dir}")
        return ""

    for file_path in sorted(root.rglob("*")):
        # Skip excluded directories
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue

        # Only include matching extensions
        if file_path.suffix not in extensions:
            continue

        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            relative = file_path.relative_to(root)
            file_block = f"\n### File: {relative}\n```\n{content}\n```\n"

            if total_chars + len(file_block) > max_chars:
                context_parts.append(
                    f"\n... [TRUNCATED - đã đạt giới hạn {max_chars} ký tự] ..."
                )
                break

            context_parts.append(file_block)
            total_chars += len(file_block)
        except Exception as e:
            context_parts.append(f"\n### File: {file_path} [ERROR: {e}]\n")

    if not context_parts:
        return "(Không tìm thấy source file nào trong project)"

    return "".join(context_parts)


def build_prompt(context: str, question: str) -> str:
    """Ghép project context + câu hỏi thành prompt hoàn chỉnh."""
    if context and context.strip() != "(Không tìm thấy source file nào trong project)":
        return (
            f"Đây là source code của project:\n"
            f"{context}\n\n"
            f"---\n\n"
            f"Câu hỏi: {question}"
        )
    return question


# ─────────────────────────────────────────────
# Browser Automation
# ─────────────────────────────────────────────

def open_browser(config: dict) -> tuple:
    """
    Mở browser và navigate tới ChatGPT.
    Dùng persistent context + system Chrome để tránh Cloudflare bot detection.
    Trả về (playwright, context, page).
    """
    pw = sync_playwright().start()

    headless = config.get("headless", False)

    # Dùng persistent context để lưu login session
    user_data_dir = config.get(
        "user_data_dir",
        os.path.join(Path.home(), ".ai-agent-chrome-profile")
    )
    os.makedirs(user_data_dir, exist_ok=True)

    print(f"[INFO] Chrome profile: {user_data_dir}")

    # Dùng system Chrome (channel="chrome") thay vì Chromium bundled
    # → Cloudflare sẽ không detect là bot
    context = pw.chromium.launch_persistent_context(
        user_data_dir,
        channel="chrome",       # Dùng Chrome thật trên máy
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",  # Ẩn automation flag
        ],
        ignore_default_args=["--enable-automation"],  # Bỏ cờ automation
    )

    page = context.pages[0] if context.pages else context.new_page()

    url = config["chatgpt_url"]
    print(f"[INFO] Đang mở browser → {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=config.get("wait_timeout", 60000))

    return pw, context, page


def wait_for_ready(page: Page, selector: str, timeout: int):
    """Chờ textarea sẵn sàng."""
    print(f"[INFO] Chờ textarea ({selector}) sẵn sàng...")
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    print("[INFO] ✓ Textarea sẵn sàng")


def send_prompt(page: Page, config: dict, prompt: str):
    """Nhập prompt vào textarea và nhấn Enter."""
    selector = config["prompt_selector"]
    wait_for_ready(page, selector, config["wait_timeout"])

    print(f"[INFO] Đang nhập prompt ({len(prompt)} ký tự)...")

    # Focus vào textarea
    page.click(selector)
    time.sleep(0.3)

    # Nhập text - dùng fill() cho nhanh
    # Nếu fill() không hoạt động (vì textarea dùng contenteditable),
    # thử type() thay thế
    try:
        page.fill(selector, prompt)
    except Exception:
        # Fallback: dùng keyboard type cho contenteditable elements
        page.click(selector)
        page.keyboard.insert_text(prompt)

    time.sleep(0.5)

    # Nhấn Enter để gửi
    print("[INFO] Nhấn Enter để gửi...")
    page.keyboard.press(config.get("send_key", "Enter"))


def wait_and_get_response(page: Page, config: dict) -> str:
    """
    Chờ response từ ChatGPT và lấy text.
    Logic: chờ element xuất hiện, sau đó chờ thêm cho đến khi
    text không thay đổi (= response đã hoàn tất).
    """
    selector = config["response_selector"]
    timeout = config["wait_timeout"]
    stable_delay = config.get("response_stable_delay", 3000) / 1000.0

    print(f"[INFO] Đang chờ response...")

    # Chờ response element xuất hiện
    page.wait_for_selector(selector, state="visible", timeout=timeout)

    # Chờ response ổn định (text không thay đổi)
    previous_text = ""
    stable_count = 0
    required_stable = 2  # cần 2 lần liên tiếp text giống nhau

    while stable_count < required_stable:
        time.sleep(stable_delay)

        # Lấy text từ element response MỚI NHẤT (element cuối cùng)
        elements = page.query_selector_all(selector)
        if not elements:
            continue

        current_text = elements[-1].inner_text()

        if current_text == previous_text and current_text.strip():
            stable_count += 1
        else:
            stable_count = 0
            previous_text = current_text

    print("[INFO] ✓ Response hoàn tất")
    return previous_text


# ─────────────────────────────────────────────
# Agent Loop
# ─────────────────────────────────────────────

def interactive_loop(page: Page, config: dict, context: str, retriever=None):
    """Vòng lặp hỏi-đáp tương tác."""
    print("\n" + "=" * 60)
    print("  AI Agent - ChatGPT Nội Bộ")
    print("  Gõ 'quit' hoặc 'exit' để thoát")
    if retriever:
        print("  Gõ 'reindex' để cập nhật index code (RAG)")
    else:
        print("  Gõ 'context' để xem project context đã load")
    print("=" * 60 + "\n")

    conversation_count = 0

    while True:
        try:
            question = input("\n🤖 Câu hỏi: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[INFO] Thoát agent.")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit", "q"):
            print("[INFO] Thoát agent.")
            break

        if question.lower() == "context" and not retriever:
            print(f"\n📄 Project context ({len(context)} ký tự):")
            print(context[:2000] + "..." if len(context) > 2000 else context)
            continue

        if question.lower() == "reindex" and retriever:
            print("[INFO] Đang chạy lại indexer...")
            from context_indexer import ProjectIndexer
            rag_config = config.get("rag", {})
            indexer = ProjectIndexer(rag_config.get("chroma_persist_dir", ".chroma_db"), rag_config.get("model_name", "all-MiniLM-L6-v2"))
            indexer.index_project(
                root_dir=config.get("project_root", "."),
                extensions=config.get("file_extensions", [".py"]),
                exclude_dirs=config.get("exclude_dirs", []),
                chunk_max_lines=rag_config.get("chunk_max_lines", 500)
            )
            print("[INFO] ✓ Re-index hoàn tất.")
            continue

        # Với RAG, ta gửi câu nào cũng kèm context liên quan. Không RAG thì chỉ gửi câu đầu.
        if retriever:
            rag_context = retriever.search(question, top_k=config.get("rag", {}).get("top_k", 5))
            prompt = build_prompt(rag_context, question)
            print(f"[INFO] Dùng RAG: Đã gửi các chunks liên quan từ ChromaDB.")
        elif conversation_count == 0 and context:
            prompt = build_prompt(context, question)
            print(f"[INFO] Gửi kèm project context ({len(context)} ký tự)")
        else:
            prompt = question

        try:
            send_prompt(page, config, prompt)
            response = wait_and_get_response(page, config)

            print("\n" + "─" * 60)
            print("📝 Response:")
            print("─" * 60)
            print(response)
            print("─" * 60)

            conversation_count += 1
        except Exception as e:
            print(f"\n[ERROR] Lỗi khi gửi/nhận: {e}")
            print("[INFO] Thử lại hoặc gõ 'quit' để thoát.")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Agent - ChatGPT Nội Bộ")
    parser.add_argument(
        "--config", default="config.json",
        help="Đường dẫn config file (mặc định: config.json)"
    )
    parser.add_argument(
        "--project", default=None,
        help="Đường dẫn project root để đọc context"
    )
    parser.add_argument(
        "--question", default=None,
        help="Câu hỏi (single-shot mode, không interactive)"
    )
    parser.add_argument(
        "--no-context", action="store_true",
        help="Không đọc project context"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Đọc project context hoặc khởi tạo RAG
    context = ""
    retriever = None
    if not args.no_context:
        project_root = args.project or config.get("project_root", ".")
        rag_config = config.get("rag", {})
        
        if rag_config.get("enabled", False):
            print(f"[INFO] RAG đang bật. Chạy indexer trên {project_root}...")
            from context_indexer import ProjectIndexer
            from context_retriever import ContextRetriever
            
            persist_dir = rag_config.get("chroma_persist_dir", ".chroma_db")
            model_name = rag_config.get("model_name", "all-MiniLM-L6-v2")
            
            # Step 1: Index
            indexer = ProjectIndexer(persist_dir, model_name)
            indexer.index_project(
                root_dir=project_root,
                extensions=config.get("file_extensions", [".py"]),
                exclude_dirs=config.get("exclude_dirs", []),
                chunk_max_lines=rag_config.get("chunk_max_lines", 500)
            )
            
            # Step 2: Retriever
            retriever = ContextRetriever(persist_dir, model_name)
            print("[INFO] ✓ RAG đã sẵn sàng.")
        else:
            print(f"[INFO] RAG đang tắt. Đọc toàn bộ project context từ: {project_root}")
            context = read_project_context(
                root_dir=project_root,
                extensions=config.get("file_extensions", [".py"]),
                exclude_dirs=config.get("exclude_dirs", []),
                max_chars=config.get("max_context_chars", 100000),
            )
            file_count = context.count("### File:")
            print(f"[INFO] ✓ Đã đọc {file_count} files ({len(context)} ký tự)")

    # Mở browser
    pw, browser_ctx, page = open_browser(config)

    try:
        # Cho user thời gian login nếu cần
        print("\n" + "=" * 60)
        print("  ⏳ Nếu cần LOGIN, hãy login trên browser ngay bây giờ.")
        print("  (Login session sẽ được lưu cho lần sau)")
        print("  Nhấn Enter khi đã sẵn sàng...")
        print("=" * 60)
        input()

        if args.question:
            # Single-shot mode
            if retriever:
                rag_context = retriever.search(args.question, top_k=config.get("rag", {}).get("top_k", 5))
                prompt = build_prompt(rag_context, args.question)
            else:
                prompt = build_prompt(context, args.question)
            send_prompt(page, config, prompt)
            response = wait_and_get_response(page, config)
            print("\n📝 Response:")
            print(response)
        else:
            # Interactive mode
            interactive_loop(page, config, context, retriever)
    except KeyboardInterrupt:
        print("\n[INFO] Thoát agent.")
    finally:
        browser_ctx.close()
        pw.stop()
        print("[INFO] Browser đã đóng.")


if __name__ == "__main__":
    main()
