import os
import re
import hashlib
from pathlib import Path
from tqdm import tqdm
import chromadb
from sentence_transformers import SentenceTransformer

# Keywords dùng chung cho mọi ngôn ngữ lập trình
# Mỗi keyword là 1 prefix của dòng code (sau khi strip)
IMPORT_KEYWORDS = [
    "import ",       # Python, Java, Go, Dart, JS/TS
    "from ",         # Python (from x import y)
    "#include",      # C, C++
    "require(",      # Node.js: require('x')
    "require '",     # Ruby: require 'x'
    "use ",          # Rust, PHP, Perl
    "using ",        # C#
    "extern crate",  # Rust (old)
]

class ProjectIndexer:
    def __init__(self, persist_dir: str, model_name: str = "all-MiniLM-L6-v2"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        # Dùng persistent client để lưu dữ liệu xuống đĩa
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(name="project_context")
        
        print(f"[RAG] Loading model {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"[RAG] Model loaded.")

    def chunk_file_content(self, file_path: str, content: str, max_lines: int = 500) -> list[str]:
        """Chia file thành các chunks theo số dòng."""
        lines = content.split('\n')
        chunks = []
        for i in range(0, len(lines), max_lines):
            chunk_lines = lines[i:i + max_lines]
            chunk_content = '\n'.join(chunk_lines)
            chunk = f"### File: {file_path} (lines {i+1}-{min(i+max_lines, len(lines))})\n```\n{chunk_content}\n```\n"
            chunks.append(chunk)
        return chunks

    def _extract_import_chunk(self, file_path: str, content: str) -> str | None:
        """
        Trích xuất các dòng import/include/require/use từ source code.
        Dùng chung bộ keywords cho mọi ngôn ngữ, không cần if/else.
        Trả về chunk text hoặc None nếu không có import nào.
        """
        import_lines = []
        in_import_block = False  # Cho Go: import ( ... )
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#!"):
                continue
            
            # Handle Go multi-line import block: import ( ... )
            if in_import_block:
                import_lines.append(stripped)
                if stripped == ")":
                    in_import_block = False
                continue
            
            for keyword in IMPORT_KEYWORDS:
                if stripped.startswith(keyword) or stripped.startswith("const ") and "require(" in stripped:
                    import_lines.append(stripped)
                    # Bắt đầu Go import block
                    if stripped == "import (":
                        in_import_block = True
                    break
        
        if not import_lines:
            return None
        
        import_text = '\n'.join(import_lines)
        return f"### File: {file_path} (imports/dependencies)\n```\n{import_text}\n```\n"

    def _get_file_hash(self, file_path: Path) -> str:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def index_project(self, root_dir: str, extensions: list[str], exclude_dirs: list[str], chunk_max_lines: int = 500):
        root = Path(root_dir).resolve()
        
        if not root.exists():
            print(f"[ERROR] Project root not found: {root_dir}")
            return
            
        print(f"[RAG] Scanning project: {root_dir}")
        all_files = []
        for file_path in root.rglob("*"):
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            if file_path.suffix not in extensions:
                continue
            if not file_path.is_file():
                continue
            all_files.append(file_path)

        existing_docs = self.collection.get(include=["metadatas"])
        existing_hashes = {m["file_path"]: m["hash"] for m in existing_docs["metadatas"]} if existing_docs and existing_docs["metadatas"] else {}
        
        files_to_index = []
        for file_path in all_files:
            rel_path = str(file_path.relative_to(root)).replace("\\", "/")
            file_hash = self._get_file_hash(file_path)
            if existing_hashes.get(rel_path) != file_hash:
                files_to_index.append((file_path, rel_path, file_hash))
                
        # Xóa các document cũ của những file bị sửa hoặc đã bị xóa
        current_rel_paths = set(str(f.relative_to(root)).replace("\\", "/") for f in all_files)
        paths_to_remove = []
        
        if existing_docs and existing_docs["metadatas"]:
            for m in existing_docs["metadatas"]:
                if m["file_path"] not in current_rel_paths or m["file_path"] in [item[1] for item in files_to_index]:
                    paths_to_remove.append(m["file_path"])
        
        if paths_to_remove:
            self.collection.delete(where={"file_path": {"$in": paths_to_remove}})
            
        if not files_to_index:
            print("[RAG] No new or modified files to index.")
            return

        print(f"[RAG] Indexing {len(files_to_index)} modified/new files...")
        
        ids_to_add = []
        texts_to_add = []
        metadatas_to_add = []
        embeddings_to_add = []
        
        for file_path, rel_path, file_hash in tqdm(files_to_index, desc="Reading and Chunking"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Chunk 1: Tách riêng phần imports/dependencies (nếu có)
                import_chunk = self._extract_import_chunk(rel_path, content)
                if import_chunk:
                    sanitized = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', rel_path)
                    idx = f"{sanitized}_imports"
                    ids_to_add.append(idx)
                    texts_to_add.append(import_chunk)
                    metadatas_to_add.append({"file_path": rel_path, "hash": file_hash, "chunk_index": -1, "chunk_type": "imports"})
                
                # Chunk 2+: Các chunks code bình thường (theo số dòng)
                chunks = self.chunk_file_content(rel_path, content, max_lines=chunk_max_lines)
                for i, chunk in enumerate(chunks):
                    sanitized = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', rel_path)
                    idx = f"{sanitized}_{i}"
                    ids_to_add.append(idx)
                    texts_to_add.append(chunk)
                    metadatas_to_add.append({"file_path": rel_path, "hash": file_hash, "chunk_index": i, "chunk_type": "code"})
            except Exception as e:
                print(f"[RAG] Error reading {rel_path}: {e}")

        if texts_to_add:
            print(f"[RAG] Generating embeddings for {len(texts_to_add)} chunks...")
            embeddings_to_add = self.model.encode(texts_to_add, show_progress_bar=True).tolist()
            
            print(f"[RAG] Storing to ChromaDB ({len(ids_to_add)} chunks)...")
            batch_size = 100
            for i in tqdm(range(0, len(ids_to_add), batch_size), desc="Saving batches"):
                self.collection.add(
                    ids=ids_to_add[i:i+batch_size],
                    documents=texts_to_add[i:i+batch_size],
                    embeddings=embeddings_to_add[i:i+batch_size],
                    metadatas=metadatas_to_add[i:i+batch_size]
                )
            print("[RAG] Indexing complete.")
