"""
Input handler - Hỗ trợ multi-line input và @file reference.

Sử dụng prompt_toolkit để:
- Shift+Enter = xuống dòng
- Enter = gửi câu hỏi
- @<file> = autocomplete + đính kèm nội dung file
"""

import os
import re
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class FileCompleter(Completer):
    """Autocomplete file khi gõ @<tên file>."""

    def __init__(self, project_root: str, extensions: list[str], exclude_dirs: list[str]):
        self.project_root = Path(project_root).resolve()
        self.extensions = extensions
        self.exclude_dirs = exclude_dirs
        self._file_cache = None

    def _scan_files(self) -> list[str]:
        """Quét danh sách file trong project (có cache)."""
        if self._file_cache is not None:
            return self._file_cache

        files = []
        for file_path in sorted(self.project_root.rglob("*")):
            if any(excluded in file_path.parts for excluded in self.exclude_dirs):
                continue
            if not file_path.is_file():
                continue
            # Cho phép tất cả file types, không giới hạn extensions
            rel = str(file_path.relative_to(self.project_root)).replace("\\", "/")
            files.append(rel)
        self._file_cache = files
        return files

    def refresh_cache(self):
        """Xóa cache, scan lại files."""
        self._file_cache = None

    def get_completions(self, document: Document, complete_event):
        """Trả về danh sách gợi ý khi gõ @."""
        text = document.text_before_cursor

        # Tìm @ cuối cùng trong text
        at_pos = text.rfind("@")
        if at_pos == -1:
            return

        # Lấy phần text sau @ cuối cùng
        partial = text[at_pos + 1:]

        # Không gợi ý nếu có khoảng trắng sau @ (đã gõ xong)
        if " " in partial and not partial.endswith("/"):
            return

        files = self._scan_files()
        for f in files:
            if partial == "" or f.lower().startswith(partial.lower()) or partial.lower() in f.lower():
                # Tính phần text cần thay thế (từ sau @ đến cursor)
                yield Completion(
                    f,
                    start_position=-len(partial),
                    display_meta="file"
                )


def create_key_bindings():
    """
    Tạo key bindings:
    - Enter = gửi (accept input)
    - Alt+Enter (hoặc Escape rồi Enter) = xuống dòng mới
    Lưu ý: Shift+Enter không hoạt động trên terminal, nên dùng Alt+Enter thay thế.
    """
    kb = KeyBindings()

    @kb.add(Keys.Enter)
    def _(event):
        """Enter = gửi câu hỏi."""
        event.current_buffer.validate_and_handle()

    @kb.add("escape", Keys.Enter)
    def _(event):
        """Alt+Enter (hoặc Escape rồi Enter) = xuống dòng."""
        event.current_buffer.insert_text("\n")

    return kb


def create_prompt_session(project_root: str, extensions: list[str], exclude_dirs: list[str]) -> tuple:
    """
    Tạo PromptSession với multi-line + autocomplete.
    Trả về (session, completer).
    """
    completer = FileCompleter(project_root, extensions, exclude_dirs)
    kb = create_key_bindings()

    session = PromptSession(
        key_bindings=kb,
        completer=completer,
        multiline=True,
        complete_while_typing=False,  # Chỉ complete khi nhấn Tab
        reserve_space_for_menu=4,
    )

    return session, completer


def get_multiline_input(session: PromptSession) -> str:
    """Lấy input từ user với multi-line support."""
    try:
        # Dùng prompt 1 dòng để tránh lỗi render trên Git Bash/MINGW
        print("\n🤖 Câu hỏi:")
        text = session.prompt("> ")
        return text.strip()
    except (KeyboardInterrupt, EOFError):
        return None


def parse_file_references(text: str, project_root: str, extensions: list = None, exclude_dirs: list = None) -> tuple:
    """
    Tìm tất cả @<file_path> trong text.
    Hỗ trợ:
      - @file.py       → đính kèm 1 file
      - @all            → đính kèm tất cả code files (theo extensions config)
      - @*.py           → đính kèm tất cả files .py

    Trả về (câu_hỏi_đã_xóa_ref, nội_dung_files_ghép_lại).
    """
    root = Path(project_root).resolve()
    if extensions is None:
        extensions = [".py"]
    if exclude_dirs is None:
        exclude_dirs = []

    # Tìm tất cả @<path> (path không chứa khoảng trắng)
    pattern = r"@([\w\-\.\/\\*]+)"
    matches = re.findall(pattern, text)

    if not matches:
        return text, ""

    file_contents = []

    for match in matches:
        # @all → gửi tất cả code files theo extensions config
        if match.lower() == "all":
            print(f"[INFO] @all: Đính kèm tất cả code files...")
            _attach_glob_files(root, extensions, exclude_dirs, file_contents)
            continue

        # @*.py → gửi tất cả files theo extension
        if match.startswith("*."):
            ext = "." + match[2:]  # "*.py" → ".py"
            print(f"[INFO] @{match}: Đính kèm tất cả files {ext}...")
            _attach_glob_files(root, [ext], exclude_dirs, file_contents)
            continue

        # @file.py → gửi 1 file cụ thể
        file_path = root / match
        if file_path.exists() and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                file_block = f"### File: {match}\n```\n{content}\n```\n"
                file_contents.append(file_block)
                print(f"[INFO] Đính kèm file: {match} ({len(content)} ký tự)")
            except Exception as e:
                print(f"[WARN] Không đọc được file {match}: {e}")
        else:
            print(f"[WARN] File không tồn tại: {match}")

    # Xóa @prefix nhưng giữ tên file trong câu hỏi
    clean_text = re.sub(r"@([\w\-\.\/\\*]+)", r"\1", text)

    return clean_text, "\n".join(file_contents)


def _attach_glob_files(root: Path, extensions: list, exclude_dirs: list, file_contents: list):
    """Helper: quét và đính kèm tất cả files matching extensions."""
    count = 0
    for file_path in sorted(root.rglob("*")):
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix not in extensions:
            continue
        try:
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_block = f"### File: {rel}\n```\n{content}\n```\n"
            file_contents.append(file_block)
            count += 1
            print(f"  📄 {rel} ({len(content)} ký tự)")
        except Exception:
            pass
    print(f"[INFO] Tổng: {count} files đính kèm")

